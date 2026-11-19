#!/usr/bin/env python3
"""MindMetric marketing shorts workflow (1080x1920, 30fps, 30-60s).

Commands (run from the repo root; see video/marketing/README.md):
  python3 video/scripts/marketing-workflow.py due      [--now ISO]
  python3 video/scripts/marketing-workflow.py status
  python3 video/scripts/marketing-workflow.py topics
  python3 video/scripts/marketing-workflow.py run      [--if-due] [--topic ID] [--audio auto|existing|none]
                                                      [--force] [--dry-run] [--now ISO]

Guarantees:
  * Never publishes, schedules posts, or calls any social network. Channels stay awaiting_connection.
  * Never touches git. Writes only under video/marketing/output and video/marketing/state.
  * Missing/failed TTS => output_status draft_blocked_audio (silent draft with an on-screen DRAFT label).
  * One run at a time (lock file); one completed run per schedule slot unless --force.

Exit codes: 0 ok, 2 failed, 3 another run holds the lock, 10 not due, 11 duplicate for this slot.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

VIDEO_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = VIDEO_DIR.parent
MARKETING_DIR = VIDEO_DIR / "marketing"
ENTRY = "marketing/src/index.ts"
COMPOSITION = "MarketingShort"

EXIT_OK, EXIT_FAILED, EXIT_LOCKED, EXIT_NOT_DUE, EXIT_DUPLICATE = 0, 2, 3, 10, 11
MAX_FAILURES_PER_SLOT = 3
BANNED_CLAIMS = re.compile(
    r"\b(official|officially|endorsed|endorsement|certified|accredited|guarantee[ds]?|guaranteed|pass rate|"
    r"real (?:test )?questions|actual (?:test )?questions|past papers?|leaked|100\s?%)\b", re.I)
SCREENSHOT_PROVENANCE = "pre-existing capture in video/public/shots (not recorded by this workflow)"


def _load_tts_module():
    spec = importlib.util.spec_from_file_location("marketing_tts", Path(__file__).with_name("marketing-tts.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tts = _load_tts_module()


class WorkflowError(Exception):
    pass


class StateError(WorkflowError):
    pass


class LockHeld(WorkflowError):
    pass


# --------------------------------------------------------------------------- schedule

def tz_for(name: str) -> dt.tzinfo:
    if ZoneInfo is not None:
        try:
            return ZoneInfo(name)
        except Exception:
            pass
    if name == "Asia/Kolkata":  # fixed UTC+05:30, no DST
        return dt.timezone(dt.timedelta(hours=5, minutes=30), "IST")
    raise WorkflowError(f"Unknown timezone {name}")


def _slot_at(day: dt.date, sched: dict) -> dt.datetime:
    hh, mm = (int(p) for p in sched["time"].split(":"))
    return dt.datetime.combine(day, dt.time(hh, mm), tz_for(sched["timezone"]))


def latest_slot(now: dt.datetime, sched: dict) -> dt.datetime | None:
    """Most recent slot (every N days at HH:MM local, counted from anchor_date) at or before now."""
    tz = tz_for(sched["timezone"])
    local = now.astimezone(tz)
    anchor = dt.date.fromisoformat(sched["anchor_date"])
    every = int(sched["every_days"])
    days = (local.date() - anchor).days
    if days < 0:
        return None
    slot = _slot_at(anchor + dt.timedelta(days=days - days % every), sched)
    if slot > local:
        slot = _slot_at(slot.date() - dt.timedelta(days=every), sched)
        if slot.date() < anchor:
            return None
    return slot


def next_slot(now: dt.datetime, sched: dict) -> dt.datetime:
    last = latest_slot(now, sched)
    if last is None:
        return _slot_at(dt.date.fromisoformat(sched["anchor_date"]), sched)
    return _slot_at(last.date() + dt.timedelta(days=int(sched["every_days"])), sched)


def due_info(now: dt.datetime, sched: dict, state: dict) -> dict:
    slot = latest_slot(now, sched)
    info = {"now": now.astimezone(tz_for(sched["timezone"])).isoformat(),
            "slot": slot.isoformat() if slot else None,
            "next_slot": next_slot(now, sched).isoformat(),
            "last_completed_slot": state.get("last_completed_slot"),
            "due": False, "reason": ""}
    if slot is None:
        info["reason"] = "before first slot"
        return info
    done = state.get("last_completed_slot")
    if done and dt.datetime.fromisoformat(done) >= slot:
        info["reason"] = "slot already completed"
        return info
    fails = state.get("slot_failures", {}).get(slot.isoformat(), 0)
    if fails >= MAX_FAILURES_PER_SLOT:
        info["reason"] = f"blocked_after_failures ({fails} failed attempts for this slot; fix and use --force)"
        return info
    info["due"] = True
    info["reason"] = "slot open"
    return info


# --------------------------------------------------------------------------- state + lock

DEFAULT_STATE = {"version": 1, "next_topic_index": 0, "last_completed_slot": None,
                 "slot_failures": {}, "runs": []}


def load_state(path: Path) -> dict:
    if not path.exists():
        return json.loads(json.dumps(DEFAULT_STATE))
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise StateError(f"State file {path} is corrupt ({e}); fix or move it aside. Not overwriting.") from None
    if not isinstance(data, dict) or "next_topic_index" not in data:
        raise StateError(f"State file {path} has an unexpected shape; not overwriting.")
    for k, v in DEFAULT_STATE.items():
        data.setdefault(k, json.loads(json.dumps(v)))
    return data


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(path)


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class RunLock:
    def __init__(self, path: Path, stale_seconds: int, clock: Callable[[], float] = time.time):
        self.path, self.stale_seconds, self.clock = path, stale_seconds, clock
        self.held = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(2):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                info = self._read()
                stale = (not info or not _pid_alive(int(info.get("pid", -1)))
                         or self.clock() - float(info.get("started", 0)) > self.stale_seconds)
                if stale and attempt == 0:
                    self.path.unlink(missing_ok=True)
                    continue
                raise LockHeld(f"Another marketing run holds {self.path} (pid {info.get('pid') if info else '?'})")
            with os.fdopen(fd, "w") as f:
                json.dump({"pid": os.getpid(), "started": self.clock()}, f)
            self.held = True
            return

    def _read(self) -> dict | None:
        try:
            return json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError):
            return None

    def release(self) -> None:
        if self.held:
            info = self._read()
            if info and info.get("pid") == os.getpid():
                self.path.unlink(missing_ok=True)
            self.held = False


# --------------------------------------------------------------------------- text helpers

def wrap_lines(text: str, font_size: float, width: float, factor: float) -> list[str]:
    max_chars = max(1, int(width / (font_size * factor)))
    lines, cur = [], ""
    for word in text.split():
        cand = f"{cur} {word}".strip()
        if len(cand) <= max_chars or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def _split_balanced(sentence: str, max_chars: int) -> list[str]:
    """Split one sentence into the fewest roughly equal pieces, preferring breaks after , ; :"""
    if len(sentence) <= max_chars:
        return [sentence]
    words = sentence.split()
    target = len(sentence) / math.ceil(len(sentence) / max_chars)
    best = None
    for i in range(1, len(words)):
        left, right = " ".join(words[:i]), " ".join(words[i:])
        if len(left) > max_chars:
            break
        score = abs(len(left) - target) - (12 if left.endswith((",", ";", ":")) else 0)
        if best is None or score < best[0]:
            best = (score, left, right)
    if best is None:
        return [sentence]
    return [best[1]] + _split_balanced(best[2], max_chars)


def chunk_caption(text: str, max_chars: int) -> list[str]:
    """Subtitle cues: one per sentence, long sentences split into balanced pieces (never mid-word)."""
    chunks = []
    for sentence in [p for p in re.split(r"(?<=[.!?])\s+", text.strip()) if p]:
        chunks += _split_balanced(sentence, max_chars)
    return chunks


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


# --------------------------------------------------------------------------- media tools (injectable)

def ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "csv=p=0", str(path)], text=True)
    return float(out.strip())


def ffprobe_video(path: Path) -> dict:
    data = json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], text=True))
    v = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)
    num, den = (int(x) for x in v["r_frame_rate"].split("/"))
    info = {"width": v["width"], "height": v["height"], "fps": num / den,
            "duration": float(data["format"]["duration"]), "has_audio": a is not None,
            "audio_duration": float(a.get("duration", 0)) if a else 0.0,
            "mean_volume": None, "max_volume": None}
    if a:
        err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af", "volumedetect",
                              "-f", "null", "-"], capture_output=True, text=True).stderr
        for key in ("mean_volume", "max_volume"):
            m = re.search(rf"{key}: (-?[\d.]+|-inf) dB", err)
            if m:
                info[key] = -200.0 if m.group(1) == "-inf" else float(m.group(1))
    return info


def ffmpeg_stills(video: Path, times: list[tuple[str, float]], out_dir: Path) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, t in times:
        p = out_dir / f"{name}.png"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", str(p)],
                       check=True)
        paths.append(str(p))
    return paths


def remotion_render(props_path: Path, public_dir: Path, out_path: Path, video_dir: Path) -> None:
    cmd = ["npx", "--no-install", "remotion", "render", ENTRY, COMPOSITION, str(out_path),
           f"--props={props_path}", f"--public-dir={public_dir}", "--log=warn"]
    proc = subprocess.run(cmd, cwd=video_dir, capture_output=True, text=True, timeout=1800)
    if proc.returncode != 0:
        tail = "\n".join((proc.stdout + proc.stderr).splitlines()[-25:])
        raise WorkflowError(f"Remotion render failed (exit {proc.returncode}):\n{tail}")


@dataclass
class Env:
    marketing_dir: Path = MARKETING_DIR
    video_dir: Path = VIDEO_DIR
    repo_root: Path = REPO_ROOT
    now: Callable[[], dt.datetime] = lambda: dt.datetime.now(dt.timezone.utc)
    probe_duration: Callable[[Path], float] = ffprobe_duration
    inspect_video: Callable[[Path], dict] = ffprobe_video
    extract_stills: Callable = ffmpeg_stills
    render: Callable = None
    provider_factory: Callable = None
    clock: Callable[[], float] = time.time

    def __post_init__(self):
        if self.render is None:
            self.render = lambda props, pub, out: remotion_render(props, pub, out, self.video_dir)
        if self.provider_factory is None:
            self.provider_factory = lambda cfg: tts.get_provider(cfg, self.repo_root)

    @property
    def output_dir(self) -> Path:
        return self.marketing_dir / "output"

    @property
    def state_path(self) -> Path:
        return self.marketing_dir / "state" / "state.json"

    @property
    def lock_path(self) -> Path:
        return self.marketing_dir / "state" / "run.lock"

    def load_json(self, name: str) -> dict:
        return json.loads((self.marketing_dir / name).read_text())


# --------------------------------------------------------------------------- audio

@dataclass
class Segment:
    id: str
    spoken: str
    caption: str
    duration: float
    audio: Path | None = None
    source: str = "none"
    meta: dict = field(default_factory=dict)


def resolve_audio(env: Env, topic: dict, cfg: dict, mode: str, today: dt.date, dry_run: bool):
    """Return (audio_info, {scene_id: Segment}). Never raises for missing credentials."""
    scene_ids = [s["id"] for s in topic["scenes"]]
    tcfg = cfg["tts"]
    wpm = cfg["timing"]["words_per_minute_estimate"]

    def estimated(reason: str, extra: dict | None = None):
        segs = {}
        for sid in scene_ids:
            line = topic["script"][sid]
            words = len(line["text"].split())
            segs[sid] = Segment(sid, line["text"], line.get("caption", line["text"]),
                                max(2.0, round(words / wpm * 60, 2)), None, "estimated")
        info = {"status": "blocked_audio", "reason": reason, "provider": tcfg.get("provider"),
                "model": tcfg.get("model"), **(extra or {})}
        return info, segs

    if mode == "none":
        return estimated("audio disabled with --audio none")

    if mode == "existing":
        ex = topic.get("existing_audio")
        if not ex:
            raise WorkflowError(f"Topic {topic['id']} has no existing_audio mapping; use --audio auto")
        segs = {}
        for sid in scene_ids:
            item = ex.get(sid)
            if not item:
                raise WorkflowError(f"existing_audio is missing segment {sid}")
            path = env.video_dir / item["file"]
            if not path.exists():
                raise WorkflowError(f"Existing audio file not found: {item['file']}")
            segs[sid] = Segment(sid, item["text"], item.get("caption", item["text"]), env.probe_duration(path), path,
                                "reused_existing_audio",
                                {"file": item["file"], "sha256": sha256_file(path)})
        return {"status": "reused_existing_audio", "origin": ex.get("_origin", ""),
                "note": "No new TTS was generated for this run."}, segs

    # mode == "auto": OpenAI (or configured) TTS if available, else blocked draft.
    try:
        provider = env.provider_factory(tcfg)
        warnings = provider.check_available(today)
    except tts.TTSUnavailable as e:
        return estimated(str(e))
    base = {"provider": provider.name, "model": provider.model, "voice": provider.voice, "warnings": warnings,
            "model_shutdown": (tts.MODEL_SHUTDOWN.get(provider.model).isoformat()
                               if tts.MODEL_SHUTDOWN.get(provider.model) else None)}
    if dry_run:
        return estimated("dry run: TTS available but not called", base)
    cache_dir = env.output_dir / "tts-cache"
    segs = {}
    try:
        for sid in scene_ids:
            line = topic["script"][sid]
            key = hashlib.sha256(json.dumps([provider.name, provider.model, provider.voice,
                                             tcfg.get("instructions", ""), line["text"]]).encode()).hexdigest()[:20]
            path = cache_dir / f"{key}.mp3"
            source = "generated_tts_cached"
            if not path.exists():
                provider.synthesize(line["text"], path)
                source = "generated_tts"
            segs[sid] = Segment(sid, line["text"], line.get("caption", line["text"]), env.probe_duration(path),
                                path, source, {"cache_key": key})
    except tts.TTSUnavailable as e:
        return estimated(str(e), base)
    return {"status": "generated_tts", **base}, segs


# --------------------------------------------------------------------------- plan + QC

def build_props(topic: dict, topics_doc: dict, segs: dict, cfg: dict, layout: dict, audio_info: dict) -> dict:
    fps = layout["fps"]
    tm = cfg["timing"]
    blocked = audio_info["status"] == "blocked_audio"
    disc = cfg["disclosure"]
    sub = layout["boxes"]["subtitles"]
    max_chars = int((sub["w"] - 2 * sub["paddingX"]) / (sub["fontSize"] * layout["textWidthFactor"])) * sub["maxLines"] - 4
    base = {}
    for sc in topic["scenes"]:
        tail = tm["cta_tail_frames"] if sc["kind"] == "cta" else tm["tail_frames"]
        base[sc["id"]] = tm["lead_frames"] + math.ceil(segs[sc["id"]].duration * fps) + tail
    # If narration runs slightly short of the minimum length, hold demo screens a little longer
    # (bounded; anything beyond the cap is left for QC to reject rather than padded with dead air).
    short = max(0, cfg["duration"]["min_seconds"] * fps - sum(base.values()))
    demos = [sc["id"] for sc in topic["scenes"] if sc["kind"] == "demo"]
    cap = tm.get("max_hold_padding_frames_per_scene", 0)
    hold = {sid: min(cap, math.ceil(short / len(demos))) if demos and short else 0 for sid in demos}

    scenes, cues, frame = [], [], 0
    for sc in topic["scenes"]:
        seg = segs[sc["id"]]
        audio_frames = math.ceil(seg.duration * fps)
        dur = base[sc["id"]] + hold.get(sc["id"], 0)
        start = frame + tm["lead_frames"]
        chunks = chunk_caption(seg.caption, max_chars)
        weights = [len(c) + 6 for c in chunks]
        acc = 0
        for c, w in zip(chunks, weights):
            c_from = start + round(audio_frames * acc / sum(weights))
            acc += w
            c_to = start + round(audio_frames * acc / sum(weights))
            cues.append({"text": c, "from": c_from, "to": c_to, "scene": sc["id"]})
        scenes.append({**{k: v for k, v in sc.items()}, "from": frame, "durationInFrames": dur,
                       "audio": ({"src": f"audio/{sc['id']}.mp3", "startFrame": tm["lead_frames"]}
                                 if seg.audio else None)})
        frame += dur
    return {
        "fps": fps, "width": layout["width"], "height": layout["height"], "durationInFrames": frame,
        "topicId": topic["id"], "scenes": scenes, "cues": cues, "draft": blocked,
        "disclosure": {"text": disc["on_screen_blocked"] if blocked else
                       disc["on_screen_reused"] if audio_info["status"] == "reused_existing_audio"
                       else disc["on_screen_generated"], "tone": "amber" if blocked else "neutral"},
        "cta": topics_doc["cta"],
        "screenshotTag": "Real MindMetric screenshot",
    }


def _check(name: str, ok: bool, detail: str = "") -> dict:
    return {"name": name, "ok": bool(ok), "detail": detail}


def pre_render_qc(props: dict, topic: dict, segs: dict, cfg: dict, layout: dict, shots_dir: Path) -> list[dict]:
    checks = []
    W, H, m = layout["width"], layout["height"], layout["minMargin"]
    f = layout["textWidthFactor"]
    boxes = layout["boxes"]
    fps = props["fps"]
    total_s = props["durationInFrames"] / fps

    # assets
    missing = [s["src"] for sc in props["scenes"] for s in sc.get("shots", []) if not (shots_dir / s["src"]).exists()]
    missing += [str(seg.audio) for seg in segs.values() if seg.audio and not Path(seg.audio).exists()]
    checks.append(_check("assets_exist", not missing, ", ".join(missing) or "all screenshots/audio present"))

    lo, hi = cfg["duration"]["min_seconds"], cfg["duration"]["max_seconds"]
    checks.append(_check("duration_range", lo <= total_s <= hi, f"{total_s:.2f}s (allowed {lo}-{hi}s)"))

    over = [f"{sc['id']}: audio {segs[sc['id']].duration:.2f}s > scene {sc['durationInFrames'] / fps:.2f}s"
            for sc in props["scenes"]
            if sc["audio"] and sc["audio"]["startFrame"] + math.ceil(segs[sc["id"]].duration * fps) > sc["durationInFrames"]]
    checks.append(_check("audio_fits_scenes", not over, "; ".join(over) or "every narration segment fits its scene"))

    bad_boxes = [k for k, b in boxes.items()
                 if b["x"] < m or b["y"] < m or b["x"] + b["w"] > W - m or b["y"] + b["h"] > H - m]
    reserve = H - layout["platformUiReserveBottom"]
    under_ui = [k for k in ("subtitles", "callout", "cta") if boxes[k]["y"] + boxes[k]["h"] > reserve]
    checks.append(_check("safe_margins", not bad_boxes and not under_ui,
                         f"outside {m}px margin: {bad_boxes}; inside bottom platform UI zone: {under_ui}"
                         if bad_boxes or under_ui else f">= {m}px margins; text clear of bottom {layout['platformUiReserveBottom']}px"))

    sizes = [b.get(k) for b in boxes.values()
             for k in ("fontSize", "labelFontSize", "tagFontSize", "urlFontSize", "smallFontSize") if b.get(k)]
    checks.append(_check("min_font_size", min(sizes) >= layout["minFontSize"], f"smallest {min(sizes)}px"))

    fit = []

    def fits(label, text, size, width, max_lines, factor=f):
        n = len(wrap_lines(text, size, width, factor))
        if n > max_lines:
            fit.append(f"{label} needs {n} lines (max {max_lines}): {text!r}")

    hb, cb, sb, db, cta = boxes["header"], boxes["callout"], boxes["subtitles"], boxes["disclosure"], boxes["cta"]
    fits("disclosure", props["disclosure"]["text"], db["fontSize"], db["w"] - 60, 1)
    card_box = boxes["card"]
    tag_w = len(props["screenshotTag"]) * hb["tagFontSize"] * f + 32
    for sc in props["scenes"]:
        label_w = len(sc["label"]) * (hb["labelFontSize"] * 0.6 + 3)
        if sc["kind"] != "cta" and label_w + 20 + tag_w > hb["w"]:
            fit.append(f"{sc['id']}.label+tag row is ~{label_w + 20 + tag_w:.0f}px > {hb['w']}px")
        for url in [sc.get("url")] + [s.get("url") for s in sc.get("shots", [])]:
            if url:
                fits(f"{sc['id']}.url", url, card_box["urlFontSize"], card_box["urlTextWidth"], 1, 0.55)
        if sc["kind"] == "cta":
            fits(f"{sc['id']}.headline", sc["headline"], cta["fontSize"] * 1.3, cta["w"], cta["maxLines"])
        else:
            fits(f"{sc['id']}.headline", sc["headline"], hb["fontSize"], hb["w"], hb["maxLines"])
        for c in sc.get("callouts", []):
            fits(f"{sc['id']}.callout", c["text"], cb["fontSize"], cb["w"] - 2 * cb["paddingX"], cb["maxLines"])
    for cue in props["cues"]:
        fits("subtitle", cue["text"], sb["fontSize"], sb["w"] - 2 * sb["paddingX"], sb["maxLines"])
    fits("cta.url", props["cta"]["url"], cta["urlFontSize"], cta["w"], 1)
    for line in props["cta"]["lines"]:
        fits("cta.line", line, cta["fontSize"], cta["w"], 2)
    fits("cta.disclaimer", props["cta"]["disclaimer"], cta["smallFontSize"], cta["w"], 2)
    checks.append(_check("text_fits_no_cutoff", not fit, "; ".join(fit) or "all text within its box line limits"))

    ss = layout["screenshot"]
    card = boxes["card"]
    img_w, img_h = card["w"], card["h"] - card["urlBarHeight"]
    bad_crop = []
    for sc in props["scenes"]:
        for shot in sc.get("shots", []):
            for c in shot["crops"]:
                h = c["w"] * img_h / img_w
                scale = img_w / c["w"]
                if scale < ss["minScale"]:
                    bad_crop.append(f"{shot['src']} scale {scale:.2f} < {ss['minScale']}")
                if c["x"] < 0 or c["y"] < 0 or c["x"] + c["w"] > ss["sourceWidth"] + 0.5 or c["y"] + h > ss["sourceHeight"] + 0.5:
                    bad_crop.append(f"{shot['src']} crop out of bounds {c}")
    checks.append(_check("screenshot_mobile_readability", not bad_crop,
                         "; ".join(bad_crop) or f"all crops >= {ss['minScale']}x and in bounds"))

    mismatch = []
    for sc in props["scenes"]:
        joined = _norm(" ".join(c["text"] for c in props["cues"] if c["scene"] == sc["id"]))
        if joined != _norm(segs[sc["id"]].caption):
            mismatch.append(sc["id"])
        if segs[sc["id"]].audio and _norm(segs[sc["id"]].caption) != _norm(segs[sc["id"]].spoken) \
                and "caption" not in topic["script"].get(sc["id"], {}):
            mismatch.append(f"{sc['id']} (caption differs from narration)")
    checks.append(_check("subtitles_match_narration", not mismatch, f"mismatch: {mismatch}" if mismatch else
                         "subtitle text equals narration text for every segment"))

    kinds = [sc["kind"] for sc in props["scenes"]]
    first = props["scenes"][0]
    hook_ok = kinds[0] == "hook" and first["durationInFrames"] / fps <= 15
    cta_ok = kinds[-1] == "cta" and props["cta"]["url"] == "mindmetric.store"
    checks.append(_check("structure_hook_demo_cta", hook_ok and "demo" in kinds and cta_ok,
                         f"scenes {kinds}; hook {first['durationInFrames'] / fps:.1f}s; CTA {props['cta']['url']}"))

    texts = [s.spoken for s in segs.values()] + [s.caption for s in segs.values()]
    for sc in props["scenes"]:
        texts += [sc["headline"], sc["label"]] + [c["text"] for c in sc.get("callouts", [])]
    hits = sorted({m.group(0) for t in texts for m in BANNED_CLAIMS.finditer(t)})
    checks.append(_check("no_endorsement_or_guarantee_claims", not hits and bool(topic.get("claims")),
                         f"banned phrases: {hits}" if hits else f"{len(topic.get('claims', []))} claims with codebase evidence"))
    return checks


def post_render_qc(info: dict, props: dict, narrated: bool, cfg: dict) -> list[dict]:
    exp = props["durationInFrames"] / props["fps"]
    lo, hi = cfg["duration"]["min_seconds"], cfg["duration"]["max_seconds"]
    checks = [
        _check("resolution_1080x1920", (info["width"], info["height"]) == (1080, 1920), f"{info['width']}x{info['height']}"),
        _check("fps_30", abs(info["fps"] - 30) < 0.01, f"{info['fps']:.3f}"),
        _check("rendered_duration", abs(info["duration"] - exp) <= 0.25 and lo <= info["duration"] <= hi,
               f"{info['duration']:.2f}s vs planned {exp:.2f}s"),
    ]
    if narrated:
        audible = info["has_audio"] and (info.get("mean_volume") or -200) > -45
        checks.append(_check("narration_audible", audible,
                             f"audio={info['has_audio']} mean={info.get('mean_volume')}dB max={info.get('max_volume')}dB"))
        checks.append(_check("audio_within_video", info["audio_duration"] <= info["duration"] + 0.15,
                             f"audio {info['audio_duration']:.2f}s, video {info['duration']:.2f}s"))
    else:
        silent = not info["has_audio"] or (info.get("max_volume") or -200) < -80
        checks.append(_check("draft_has_no_narration", silent, "silent draft as expected" if silent else "unexpected audio"))
    return checks


# --------------------------------------------------------------------------- captions

def build_captions(topic: dict, cfg: dict, audio_status: str) -> dict:
    disc = cfg["disclosure"]
    ai_line = {"generated_tts": disc["post_generated"], "reused_existing_audio": disc["post_reused"]}.get(
        audio_status, disc["post_blocked"])
    footer = [ai_line, disc["screens"], disc["independence"]]
    draft = audio_status == "blocked_audio"
    yt = topic["captions"]["youtube_shorts"]
    ig = topic["captions"]["instagram_reels"]
    yt_title = yt["title"]
    out = {
        "youtube_shorts": {
            "channel_status": cfg["channels"]["youtube_shorts"]["status"],
            "post_status": "draft_not_published",
            "title": yt_title,
            "description": "\n\n".join([yt["description"], "\n".join(footer), " ".join(yt["hashtags"])]),
        },
        "instagram_reels": {
            "channel_status": cfg["channels"]["instagram_reels"]["status"],
            "post_status": "draft_not_published",
            "caption": "\n\n".join([ig["caption"], "\n".join(footer), " ".join(ig["hashtags"])]),
        },
    }
    problems = []
    if len(yt_title) > 100:
        problems.append("YouTube title > 100 chars")
    if len(out["instagram_reels"]["caption"]) > 2200:
        problems.append("Instagram caption > 2200 chars")
    if "#Shorts" not in out["youtube_shorts"]["description"]:
        problems.append("YouTube description missing #Shorts")
    for k in out:
        text = json.dumps(out[k])
        if "AI-generated" not in text:
            problems.append(f"{k} missing AI narration disclosure")
        hits = {m.group(0) for m in BANNED_CLAIMS.finditer(text)}
        if hits:
            problems.append(f"{k} banned phrases {sorted(hits)}")
    out["_checks"] = {"ok": not problems, "problems": problems, "draft_blocked_audio": draft}
    return out


def captions_markdown(c: dict, run_id: str, video_name: str, draft: bool) -> str:
    head = f"# Draft post copy: {run_id}\n\nVideo: `{video_name}`\n\n"
    if draft:
        head += "> DRAFT (blocked_audio): no narration yet. Do not post until narration is generated and QC passes.\n\n"
    head += ("> Channels are `awaiting_connection`. This workflow never publishes or schedules posts; "
             "posting is a manual step after human review.\n\n")
    yt, ig = c["youtube_shorts"], c["instagram_reels"]
    return (head + f"## YouTube Shorts ({yt['channel_status']})\n\n**Title:** {yt['title']}\n\n**Description:**\n\n"
            f"{yt['description']}\n\n## Instagram Reels ({ig['channel_status']})\n\n**Caption:**\n\n{ig['caption']}\n")


# --------------------------------------------------------------------------- run

def _rel(p: Path, base: Path) -> str:
    try:
        return str(Path(p).relative_to(base))
    except ValueError:
        return str(p)


def run(env: Env, *, if_due=False, topic_id=None, audio_mode="auto", force=False, dry_run=False) -> tuple[int, dict]:
    cfg, layout, topics_doc = env.load_json("config.json"), env.load_json("layout.json"), env.load_json("topics.json")
    topics = topics_doc["topics"]
    lock = RunLock(env.lock_path, int(cfg.get("lock_stale_seconds", 7200)), env.clock)
    try:
        lock.acquire()
    except LockHeld as e:
        return EXIT_LOCKED, {"status": "skipped_locked", "detail": str(e)}
    try:
        state = load_state(env.state_path)
        now = env.now()
        due = due_info(now, cfg["schedule"], state)
        if if_due and not due["due"]:
            return EXIT_NOT_DUE, {"status": "skipped_not_due", **due}
        slot = due["slot"]
        if not force and slot and state.get("last_completed_slot") == slot and not dry_run:
            return EXIT_DUPLICATE, {"status": "skipped_duplicate",
                                    "detail": f"slot {slot} already has a completed run; use --force to re-run", **due}

        rot_index = state["next_topic_index"] % len(topics)
        if topic_id:
            topic = next((t for t in topics if t["id"] == topic_id), None)
            if not topic:
                raise WorkflowError(f"Unknown topic {topic_id}; see `topics`")
        else:
            topic = topics[rot_index]

        local = now.astimezone(tz_for(cfg["schedule"]["timezone"]))
        base_id = (f"{dt.datetime.fromisoformat(slot):%Y%m%d}" if slot else f"manual-{local:%Y%m%dT%H%M}") + f"-{topic['id']}"
        if dry_run:
            base_id += "-dryrun"
        runs_dir = env.output_dir / "runs"
        run_id, n = base_id, 1
        while (runs_dir / run_id).exists():
            n += 1
            run_id = f"{base_id}-{n}"
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)
        record = {"run_id": run_id, "topic_id": topic["id"], "topic_title": topic["title"], "slot": slot,
                  "started_at": local.isoformat(), "status": "running", "output_status": None,
                  "dry_run": dry_run, "audio_mode": audio_mode,
                  "channels": {k: v["status"] for k, v in cfg["channels"].items()},
                  "publishing": "never: no social accounts connected; workflow does not publish or schedule posts",
                  "errors": []}
        (run_dir / "status.json").write_text(json.dumps(record, indent=2))

        try:
            audio_info, segs = resolve_audio(env, topic, cfg, audio_mode, local.date(), dry_run)
            record["audio"] = {**audio_info, "segments": [
                {"id": s.id, "source": s.source, "duration_s": round(s.duration, 2), "spoken_text": s.spoken,
                 "subtitle_text": s.caption, **s.meta} for s in segs.values()]}
            props = build_props(topic, topics_doc, segs, cfg, layout, audio_info)
            shots_dir = env.video_dir / "public" / "shots"
            pre = pre_render_qc(props, topic, segs, cfg, layout, shots_dir)
            record["qc"] = {"pre_render": pre}

            public = run_dir / "public"
            (public / "shots").mkdir(parents=True)
            prov = []
            for src in sorted({s["src"] for sc in props["scenes"] for s in sc.get("shots", [])}):
                p = shots_dir / src
                if p.exists():
                    shutil.copy2(p, public / "shots" / src)
                    prov.append({"src": f"video/public/shots/{src}", "sha256": sha256_file(p),
                                 "file_mtime": dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc).isoformat(),
                                 "provenance": SCREENSHOT_PROVENANCE})
            record["screenshots"] = prov
            if any(s.audio for s in segs.values()):
                (public / "audio").mkdir()
                for s in segs.values():
                    shutil.copy2(s.audio, public / "audio" / f"{s.id}.mp3")
            props_path = run_dir / "props.json"
            props_path.write_text(json.dumps(props, indent=2))

            captions = build_captions(topic, cfg, audio_info["status"])
            record["qc"]["captions"] = captions.pop("_checks")
            (run_dir / "captions.json").write_text(json.dumps(captions, indent=2))
            blocked = audio_info["status"] == "blocked_audio"
            video_name = f"{run_id}{'-DRAFT-no-audio' if blocked else ''}.mp4"
            (run_dir / "captions.md").write_text(captions_markdown(captions, run_id, video_name, blocked))

            failed = [c["name"] for c in pre if not c["ok"]]
            if not record["qc"]["captions"]["ok"]:
                failed.append("captions")
            if failed:
                raise WorkflowError(f"Pre-render QC failed: {failed}")

            if dry_run:
                record.update(status="dry_run", output_status="not_rendered")
            else:
                video = run_dir / video_name
                env.render(props_path, public, video)
                info = env.inspect_video(video)
                post = post_render_qc(info, props, not blocked, cfg)
                record["qc"]["post_render"] = post
                record["qc"]["video_info"] = info
                fps = props["fps"]
                times = [("00-first-frame", 0.0)] + [
                    (f"{i + 1:02d}-{sc['id']}-{tag}", (sc["from"] + sc["durationInFrames"] * pos) / fps)
                    for i, sc in enumerate(props["scenes"]) for tag, pos in (("early", 0.35), ("late", 0.9))]
                record["qc"]["review_stills"] = [_rel(Path(p), env.video_dir)
                                                 for p in env.extract_stills(video, times, run_dir / "stills")]
                record["video"] = _rel(video, env.video_dir)
                bad = [c["name"] for c in post if not c["ok"]]
                if bad:
                    raise WorkflowError(f"Post-render QC failed: {bad}")
                record.update(status="completed",
                              output_status="draft_blocked_audio" if blocked else "narrated_draft_ready_for_review")
        except (WorkflowError, tts.TTSUnavailable, subprocess.SubprocessError, OSError, KeyError, ValueError) as e:
            record.update(status="failed", output_status="failed")
            record["errors"].append(f"{type(e).__name__}: {e}")

        record["finished_at"] = env.now().astimezone(local.tzinfo).isoformat()
        (run_dir / "status.json").write_text(json.dumps(record, indent=2))

        if not dry_run:
            summary = {k: record.get(k) for k in ("run_id", "topic_id", "slot", "status", "output_status", "video",
                                                   "started_at", "finished_at")}
            summary["audio_status"] = record.get("audio", {}).get("status")
            summary["status_file"] = _rel(run_dir / "status.json", env.video_dir)
            state["runs"] = (state["runs"] + [summary])[-50:]
            if record["status"] == "completed" and record["audio"]["status"] != "blocked_audio":
                if slot:
                    state["last_completed_slot"] = slot
                    state["slot_failures"].pop(slot, None)
                if topic["id"] == topics[rot_index]["id"]:
                    state["next_topic_index"] = (rot_index + 1) % len(topics)
            elif record["status"] == "failed" and slot:
                state["slot_failures"][slot] = state["slot_failures"].get(slot, 0) + 1
            save_state(env.state_path, state)
        code = EXIT_OK if record["status"] in ("completed", "dry_run") else EXIT_FAILED
        return code, record
    finally:
        lock.release()


# --------------------------------------------------------------------------- CLI

def _parse_now(s: str | None):
    if not s:
        return lambda: dt.datetime.now(dt.timezone.utc)
    t = dt.datetime.fromisoformat(s)
    if t.tzinfo is None:
        raise SystemExit("--now needs a timezone offset, e.g. 2026-11-17T19:05:00+05:30")
    return lambda: t


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("due", help="exit 0 if a run is due now, 10 otherwise")
    d.add_argument("--now")
    sub.add_parser("status")
    sub.add_parser("topics")
    r = sub.add_parser("run")
    r.add_argument("--if-due", action="store_true", help="only run if the every-2-days 19:00 IST slot is open")
    r.add_argument("--topic", help="override rotation with a topic id")
    r.add_argument("--audio", choices=["auto", "existing", "none"], default="auto",
                   help="auto: configured TTS if credentials exist, else blocked_audio draft; "
                        "existing: reuse the topic's pre-existing narration files (labelled as reused); none: silent draft")
    r.add_argument("--force", action="store_true", help="allow another run for an already-completed slot")
    r.add_argument("--dry-run", action="store_true", help="plan, QC and captions only; no TTS calls, no render, no state change")
    r.add_argument("--now")
    a = ap.parse_args(argv)

    env = Env(now=_parse_now(getattr(a, "now", None)))
    cfg = env.load_json("config.json")
    if a.cmd == "topics":
        state = load_state(env.state_path)
        topics = env.load_json("topics.json")["topics"]
        for i, t in enumerate(topics):
            mark = "->" if i == state["next_topic_index"] % len(topics) else "  "
            print(f"{mark} {t['id']}: {t['title']}{'  [existing audio available]' if t.get('existing_audio') else ''}")
        return 0
    if a.cmd == "due":
        info = due_info(env.now(), cfg["schedule"], load_state(env.state_path))
        print(json.dumps(info, indent=2))
        return EXIT_OK if info["due"] else EXIT_NOT_DUE
    if a.cmd == "status":
        state = load_state(env.state_path)
        topics = env.load_json("topics.json")["topics"]
        print(json.dumps({"due": due_info(env.now(), cfg["schedule"], state),
                          "next_topic": topics[state["next_topic_index"] % len(topics)]["id"],
                          "channels": {k: v["status"] for k, v in cfg["channels"].items()},
                          "tts": {k: cfg["tts"][k] for k in ("provider", "model", "voice")},
                          "tts_model_shutdown": {k: v.isoformat() for k, v in tts.MODEL_SHUTDOWN.items()},
                          "recent_runs": state["runs"][-5:]}, indent=2))
        return 0
    try:
        code, record = run(env, if_due=a.if_due, topic_id=a.topic, audio_mode=a.audio, force=a.force, dry_run=a.dry_run)
    except StateError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return EXIT_FAILED
    keys = ("run_id", "status", "output_status", "video", "detail", "reason", "errors")
    out = {k: record[k] for k in keys if k in record}
    if "audio" in record:
        out["audio_status"] = record["audio"]["status"]
        if record["audio"].get("reason"):
            out["audio_reason"] = record["audio"]["reason"]
    if "qc" in record:
        out["qc_failed"] = [c["name"] for k in ("pre_render", "post_render") for c in record["qc"].get(k, []) if not c["ok"]]
    if "run_id" in record:
        out["status_file"] = f"video/marketing/output/runs/{record['run_id']}/status.json"
    print(json.dumps(out, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
