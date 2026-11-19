"""Tests for video/scripts/marketing-workflow.py and marketing-tts.py.

Run from the repo root:  python3 -m unittest discover -s video/marketing/tests -v
No network, no Remotion, no ffmpeg: rendering/probing/TTS are injected fakes.
"""
import datetime as dt
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
MARKETING = Path(__file__).resolve().parents[1]


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / file)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclasses need the module registered
    spec.loader.exec_module(mod)
    return mod


wf = _load("marketing_workflow", "marketing-workflow.py")
tts = wf.tts
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
SCHED = {"timezone": "Asia/Kolkata", "time": "19:00", "every_days": 2, "anchor_date": "2026-11-15"}


def ist(y, m, d, hh, mm=0):
    return dt.datetime(y, m, d, hh, mm, tzinfo=IST)


class ScheduleTests(unittest.TestCase):
    def test_before_anchor_slot_has_no_slot(self):
        self.assertIsNone(wf.latest_slot(ist(2026, 11, 15, 18, 59), SCHED))
        self.assertEqual(wf.next_slot(ist(2026, 11, 15, 18, 59), SCHED), ist(2026, 11, 15, 19))

    def test_every_two_days_at_1900_ist(self):
        self.assertEqual(wf.latest_slot(ist(2026, 11, 15, 19, 0), SCHED), ist(2026, 11, 15, 19))
        self.assertEqual(wf.latest_slot(ist(2026, 11, 16, 23, 0), SCHED), ist(2026, 11, 15, 19))
        self.assertEqual(wf.latest_slot(ist(2026, 11, 17, 18, 59), SCHED), ist(2026, 11, 15, 19))
        self.assertEqual(wf.latest_slot(ist(2026, 11, 17, 19, 0), SCHED), ist(2026, 11, 17, 19))
        self.assertEqual(wf.next_slot(ist(2026, 11, 17, 19, 1), SCHED), ist(2026, 11, 19, 19))

    def test_utc_input_is_converted(self):
        now = dt.datetime(2026, 11, 17, 13, 30, tzinfo=dt.timezone.utc)  # 19:00 IST
        self.assertEqual(wf.latest_slot(now, SCHED), ist(2026, 11, 17, 19))

    def test_due_info_states(self):
        now = ist(2026, 11, 17, 20)
        self.assertTrue(wf.due_info(now, SCHED, {"last_completed_slot": None})["due"])
        done = {"last_completed_slot": ist(2026, 11, 17, 19).isoformat()}
        self.assertFalse(wf.due_info(now, SCHED, done)["due"])
        # a missed slot is caught up once, not once per missed slot
        old = {"last_completed_slot": ist(2026, 11, 13, 19).isoformat()}
        self.assertEqual(wf.due_info(now, SCHED, old)["slot"], ist(2026, 11, 17, 19).isoformat())
        failing = {"last_completed_slot": None, "slot_failures": {ist(2026, 11, 17, 19).isoformat(): 3}}
        info = wf.due_info(now, SCHED, failing)
        self.assertFalse(info["due"])
        self.assertIn("blocked_after_failures", info["reason"])


class FakeProvider(tts.TTSProvider):
    name, model, voice = "openai", "gpt-4o-mini-tts", "coral"

    def __init__(self):
        self.calls = []

    def check_available(self, today):
        return []

    def synthesize(self, text, out_path):
        self.calls.append(text)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"ID3" + b"\0" * 2000)


class WorkflowHarness(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.video = self.tmp / "video"
        self.mk = self.video / "marketing"
        self.mk.mkdir(parents=True)
        for f in ("config.json", "layout.json", "topics.json"):
            shutil.copy(MARKETING / f, self.mk / f)
        topics = json.loads((self.mk / "topics.json").read_text())["topics"]
        shots = self.video / "public" / "shots"
        shots.mkdir(parents=True)
        for t in topics:
            for sc in t["scenes"]:
                for s in sc.get("shots", []):
                    (shots / s["src"]).write_bytes(b"png")
            for k, v in t.get("existing_audio", {}).items():
                if not k.startswith("_"):
                    p = self.video / v["file"]
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes(b"mp3")
        self.topics = topics
        self.now = ist(2026, 11, 17, 19, 5)
        self.renders = []
        self.render_error = None
        self.provider = None  # None => provider without API key

    def make_env(self):
        last = {}

        def render(props_path, public, out):
            if self.render_error:
                raise wf.WorkflowError(self.render_error)
            last["props"] = json.loads(Path(props_path).read_text())
            self.renders.append(out)
            Path(out).write_bytes(b"mp4")

        def inspect(path):
            p = last["props"]
            narrated = any(s["audio"] for s in p["scenes"])
            d = p["durationInFrames"] / p["fps"]
            return {"width": 1080, "height": 1920, "fps": 30.0, "duration": d, "has_audio": narrated,
                    "audio_duration": d if narrated else 0, "mean_volume": -20.0 if narrated else None,
                    "max_volume": -3.0 if narrated else None}

        def provider_factory(cfg):
            if self.provider is not None:
                return self.provider
            return tts.OpenAISpeechProvider(cfg["model"], cfg["voice"], "", None, 6)

        return wf.Env(marketing_dir=self.mk, video_dir=self.video, repo_root=self.tmp,
                      now=lambda: self.now, probe_duration=lambda p: 8.0, inspect_video=inspect,
                      extract_stills=lambda v, t, d: [], render=render, provider_factory=provider_factory)

    def state(self):
        return json.loads((self.mk / "state" / "state.json").read_text())


class RunTests(WorkflowHarness):
    def test_missing_key_yields_explicit_blocked_audio_draft(self):
        code, rec = wf.run(self.make_env(), if_due=True)
        self.assertEqual(code, wf.EXIT_OK)
        self.assertEqual(rec["output_status"], "draft_blocked_audio")
        self.assertEqual(rec["audio"]["status"], "blocked_audio")
        self.assertIn("OPENAI_API_KEY", rec["audio"]["reason"])
        self.assertTrue(rec["video"].endswith("-DRAFT-no-audio.mp4"))
        props = json.loads((self.mk / "output" / "runs" / rec["run_id"] / "props.json").read_text())
        self.assertTrue(props["draft"])
        self.assertTrue(all(s["audio"] is None for s in props["scenes"]))
        self.assertIn("DRAFT", props["disclosure"]["text"])
        captions = json.loads((self.mk / "output" / "runs" / rec["run_id"] / "captions.json").read_text())
        for ch in ("youtube_shorts", "instagram_reels"):
            self.assertEqual(captions[ch]["channel_status"], "awaiting_connection")
            self.assertEqual(captions[ch]["post_status"], "draft_not_published")
        self.assertIn("DRAFT: this video has no voiceover", captions["instagram_reels"]["caption"])

    def test_blocked_audio_keeps_topic_and_can_resume_when_key_is_configured(self):
        env = self.make_env()
        wf.run(env, if_due=True)
        state = self.state()
        self.assertEqual(state["next_topic_index"], 0)
        self.assertIsNone(state["last_completed_slot"])
        self.assertEqual(state["slot_failures"], {})
        self.provider = FakeProvider()
        code, record = wf.run(env, if_due=True)
        self.assertEqual(code, wf.EXIT_OK)
        self.assertEqual(record["topic_id"], self.topics[0]["id"])
        self.assertEqual(record["audio"]["status"], "generated_tts")
        self.assertEqual(self.state()["next_topic_index"], 1)

    def test_rotation_advances_per_completed_slot(self):
        self.provider = FakeProvider()
        env = self.make_env()
        wf.run(env, if_due=True)
        self.now = ist(2026, 11, 19, 19, 1)
        code, rec = wf.run(env, if_due=True)
        self.assertEqual(code, wf.EXIT_OK)
        self.assertEqual(rec["topic_id"], self.topics[1]["id"])
        st = self.state()
        self.assertEqual(st["next_topic_index"], 2)
        self.assertEqual(st["last_completed_slot"], ist(2026, 11, 19, 19).isoformat())
        self.assertEqual([r["topic_id"] for r in st["runs"]], [self.topics[0]["id"], self.topics[1]["id"]])

    def test_duplicate_and_not_due_runs_are_skipped(self):
        self.provider = FakeProvider()
        env = self.make_env()
        wf.run(env, if_due=True)
        code, rec = wf.run(env, if_due=True)
        self.assertEqual((code, rec["status"]), (wf.EXIT_NOT_DUE, "skipped_not_due"))
        code, rec = wf.run(env)  # manual run, same slot
        self.assertEqual((code, rec["status"]), (wf.EXIT_DUPLICATE, "skipped_duplicate"))
        self.assertEqual(len(self.renders), 1)
        code, _ = wf.run(env, force=True)
        self.assertEqual(code, wf.EXIT_OK)
        self.assertEqual(len(self.renders), 2)

    def test_live_lock_blocks_concurrent_run(self):
        lock = self.mk / "state" / "run.lock"
        lock.parent.mkdir(parents=True)
        lock.write_text(json.dumps({"pid": os.getpid(), "started": self.now.timestamp()}))
        env = self.make_env()
        env.clock = lambda: self.now.timestamp() + 10
        code, rec = wf.run(env, if_due=True)
        self.assertEqual((code, rec["status"]), (wf.EXIT_LOCKED, "skipped_locked"))
        self.assertTrue(lock.exists(), "must not delete another run's live lock")
        self.assertEqual(self.renders, [])

    def test_stale_lock_is_replaced_and_released(self):
        lock = self.mk / "state" / "run.lock"
        lock.parent.mkdir(parents=True)
        lock.write_text(json.dumps({"pid": os.getpid(), "started": 0}))  # far older than lock_stale_seconds
        code, _ = wf.run(self.make_env(), if_due=True)
        self.assertEqual(code, wf.EXIT_OK)
        self.assertFalse(lock.exists())

    def test_render_failure_keeps_topic_and_stops_after_three_attempts(self):
        self.render_error = "boom"
        env = self.make_env()
        for _ in range(3):
            code, rec = wf.run(env, if_due=True)
            self.assertEqual(code, wf.EXIT_FAILED)
            self.assertEqual(rec["status"], "failed")
            self.assertIn("boom", rec["errors"][0])
        st = self.state()
        self.assertEqual(st["next_topic_index"], 0)
        self.assertIsNone(st["last_completed_slot"])
        self.assertFalse((self.mk / "state" / "run.lock").exists())
        code, rec = wf.run(env, if_due=True)
        self.assertEqual(code, wf.EXIT_NOT_DUE)
        self.assertIn("blocked_after_failures", rec["reason"])

    def test_corrupt_state_is_not_overwritten(self):
        p = self.mk / "state" / "state.json"
        p.parent.mkdir(parents=True)
        p.write_text("{not json")
        with self.assertRaises(wf.StateError):
            wf.run(self.make_env(), if_due=True)
        self.assertEqual(p.read_text(), "{not json")
        self.assertFalse((self.mk / "state" / "run.lock").exists())

    def test_existing_audio_is_labelled_as_reused(self):
        code, rec = wf.run(self.make_env(), audio_mode="existing")
        self.assertEqual(code, wf.EXIT_OK)
        self.assertEqual(rec["audio"]["status"], "reused_existing_audio")
        self.assertIn("No new TTS", rec["audio"]["note"])
        self.assertTrue(all(s["source"] == "reused_existing_audio" for s in rec["audio"]["segments"]))
        self.assertTrue(all(s["provenance"].startswith("pre-existing") for s in rec["screenshots"]))

    def test_tts_generation_is_cached_across_runs(self):
        self.provider = FakeProvider()
        env = self.make_env()
        code, rec = wf.run(env, if_due=True)
        self.assertEqual(code, wf.EXIT_OK)
        self.assertEqual(rec["audio"]["status"], "generated_tts")
        self.assertEqual(rec["output_status"], "narrated_draft_ready_for_review")
        n = len(self.provider.calls)
        self.assertEqual(n, len(self.topics[0]["scenes"]))
        wf.run(env, topic_id=self.topics[0]["id"], force=True)
        self.assertEqual(len(self.provider.calls), n, "re-run must reuse cached narration, not pay again")

    def test_dry_run_changes_no_state_and_calls_no_tts(self):
        self.provider = FakeProvider()
        code, rec = wf.run(self.make_env(), dry_run=True)
        self.assertEqual((code, rec["status"]), (wf.EXIT_OK, "dry_run"))
        self.assertEqual(self.provider.calls, [])
        self.assertEqual(self.renders, [])
        self.assertFalse((self.mk / "state" / "state.json").exists())


class QCTests(WorkflowHarness):
    def _plan(self, topic):
        cfg = json.loads((self.mk / "config.json").read_text())
        layout = json.loads((self.mk / "layout.json").read_text())
        doc = json.loads((self.mk / "topics.json").read_text())
        segs = {sc["id"]: wf.Segment(sc["id"], topic["script"][sc["id"]]["text"],
                                     topic["script"][sc["id"]].get("caption", topic["script"][sc["id"]]["text"]), 8.0)
                for sc in topic["scenes"]}
        props = wf.build_props(topic, doc, segs, cfg, layout, {"status": "blocked_audio"})
        checks = wf.pre_render_qc(props, topic, segs, cfg, layout, self.video / "public" / "shots")
        return {c["name"]: c for c in checks}

    def test_all_shipped_topics_pass_pre_render_qc(self):
        for t in self.topics:
            failed = [n for n, c in self._plan(t).items() if not c["ok"]]
            self.assertEqual(failed, [], t["id"])

    def test_qc_rejects_guarantee_claims_cutoff_text_and_unreadable_crops(self):
        t = json.loads(json.dumps(self.topics[0]))
        t["scenes"][1]["headline"] = "Guaranteed pass with the official Thomas GIA questions, every single time you try"
        t["scenes"][2]["shots"][0]["crops"][0]["w"] = 2500
        checks = self._plan(t)
        self.assertFalse(checks["no_endorsement_or_guarantee_claims"]["ok"])
        self.assertFalse(checks["text_fits_no_cutoff"]["ok"])
        self.assertFalse(checks["screenshot_mobile_readability"]["ok"])

    def test_subtitles_cover_narration_exactly(self):
        self.assertTrue(self._plan(self.topics[0])["subtitles_match_narration"]["ok"])


class TTSAdapterTests(unittest.TestCase):
    SECRET = "sk-test-DO-NOT-LEAK-123"

    def test_key_from_env_then_dotenv_line_only(self):
        with tempfile.TemporaryDirectory() as d:
            env_file = Path(d) / ".env"
            env_file.write_text(f"OTHER=1\nexport OPENAI_API_KEY='{self.SECRET}'\n")
            old = os.environ.pop("MM_TEST_KEY", None)
            try:
                self.assertIsNone(tts.load_api_key("MM_TEST_KEY", [env_file]))
                env_file.write_text(f"MM_TEST_KEY={self.SECRET}\n")
                self.assertEqual(tts.load_api_key("MM_TEST_KEY", [env_file]), self.SECRET)
                os.environ["MM_TEST_KEY"] = "from-env"
                self.assertEqual(tts.load_api_key("MM_TEST_KEY", [env_file]), "from-env")
            finally:
                os.environ.pop("MM_TEST_KEY", None)
                if old is not None:
                    os.environ["MM_TEST_KEY"] = old

    def test_model_shutdown_date_blocks_and_warns(self):
        p = tts.OpenAISpeechProvider("gpt-4o-mini-tts", "coral", "", self.SECRET, 6)
        self.assertTrue(p.check_available(dt.date(2026, 11, 15)))  # warning within 60 days
        with self.assertRaises(tts.TTSUnavailable):
            p.check_available(dt.date(2027, 1, 6))
        self.assertEqual(tts.OpenAISpeechProvider("future-tts", "coral", "", self.SECRET, 6)
                         .check_available(dt.date(2027, 2, 1)), [])

    def test_errors_and_repr_never_contain_the_key(self):
        def opener(req, timeout):
            raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {},
                                         io.BytesIO(f"Incorrect API key {self.SECRET}".encode()))
        p = tts.OpenAISpeechProvider("gpt-4o-mini-tts", "coral", "", self.SECRET, 6, opener=opener)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(tts.TTSUnavailable) as cm:
                p.synthesize("hi", Path(d) / "a.mp3")
        self.assertNotIn(self.SECRET, str(cm.exception))
        self.assertIn("401", str(cm.exception))
        self.assertNotIn(self.SECRET, repr(p))

    def test_request_budget_is_enforced(self):
        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        p = tts.OpenAISpeechProvider("gpt-4o-mini-tts", "coral", "", self.SECRET, 2,
                                     opener=lambda req, timeout: Resp(b"\0" * 5000))
        with tempfile.TemporaryDirectory() as d:
            p.synthesize("a", Path(d) / "1.mp3")
            p.synthesize("b", Path(d) / "2.mp3")
            with self.assertRaises(tts.TTSUnavailable):
                p.synthesize("c", Path(d) / "3.mp3")

    def test_unknown_provider_is_rejected(self):
        with self.assertRaises(tts.TTSUnavailable):
            tts.get_provider({"provider": "elevenlabs"}, Path("."))


if __name__ == "__main__":
    unittest.main()
