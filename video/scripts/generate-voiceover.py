"""Generate one MP3 per scene with OpenAI TTS. Needs OPENAI_API_KEY in the environment."""
import json, os, subprocess, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(os.environ["OUT_DIR"]) if os.environ.get("OUT_DIR") else ROOT / "voiceover"
VOICE = os.environ.get("VOICE", "ballad")
MODEL = "gpt-4o-mini-tts"
STYLE = os.environ.get("STYLE") or (
    "Speak like a real person talking to a friend who just got a job-test invite: relaxed, conversational, "
    "genuinely warm, with natural rises and falls in pitch and a hint of a smile. Vary your rhythm; "
    "lean into key words, let short sentences land, and take small natural breaths between ideas. "
    "Never sound like an announcer, a robot or an advert.")
SHORT_PACE = " Keep a lively, brisk pace with short pauses: this is a 30-second social video."

SEGMENTS = {
    "hook": "The email arrives. You've been invited to an online aptitude test. It's timed. And it decides whether you get the interview.",
    "contrast": "Most people prepare with random question banks and no clock. Then the real test feels nothing like practice.",
    "pitch": "MindMetric is practice built for the test in your invite. The real section formats. The real timing. And a clear explanation after every answer.",
    "home": "Type the test, or the company that sent your invite, and you're practising in seconds. No sign-up needed.",
    "tracks": "Choose from Thomas GIA, CCAT, SHL-style reasoning, Watson-Glaser critical thinking, and two consulting tracks.",
    "question": "Practice mode has no timer. Answer, and you instantly see whether you were right, and why.",
    "spatial": "Every section matches the real format, from rotated shapes to number speed and accuracy.",
    "case": "For consulting, work through linked business cases with real exhibits: charts, tables, and the maths behind the decision.",
    "language": "Thomas GIA is now available in German and Spanish too.",
    "testmode": "When you're ready, switch to test mode. Fullscreen, timed, and scored section by section, just like the real thing.",
    "close": "Free to start. Never auto-renews. MindMetric. From invite to interview.",
}

# 30-second single-test shorts: one set per test, written to voiceover/<set>/.
SHORTS = {
    "shl": {
        "hook": "SHL test coming up? Three types of reasoning, and the clock never stops.",
        "sections": "Practise all three: numerical, deductive, and inductive reasoning.",
        "explain": "Every question has a worked solution, so you see exactly how to crack it.",
        "fulltest": "Then take a full mixed test: twenty-four questions in thirty-six minutes.",
        "cta": "Start free, at mindmetric dot store.",
    },
    "gia": {
        "hook": "Thomas GIA test coming up? Five timed sections, where speed counts as much as accuracy.",
        "sections": "Practise all five: reasoning, perceptual speed, number speed, word meaning, and spatial.",
        "explain": "Every answer shows you why, so you get faster with each question.",
        "fulltest": "Then take the full timed test, in English, German or Spanish.",
        "cta": "Start free, at mindmetric dot store.",
    },
    "ccat": {
        "hook": "CCAT invite in your inbox? Fifty questions, fifteen minutes, and very few people finish.",
        "sections": "Practise all three question types: maths, verbal reasoning, and spatial and abstract logic.",
        "explain": "Every answer comes with a quick explanation, so you learn the shortcut.",
        "fulltest": "Then take a full fifty-question test, against the real fifteen-minute clock.",
        "cta": "Start free, at mindmetric dot store.",
    },
}


def tts(text, path):
    body = json.dumps({"model": MODEL, "voice": VOICE, "input": text, "instructions": STYLE, "response_format": "mp3"}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/audio/speech", data=body, headers={
        "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        path.write_bytes(r.read())

def trim_silence(path):
    """Drop leading/trailing silence the TTS adds, so scene timing follows the speech."""
    tmp = path.with_suffix(".tmp.mp3")
    trim = "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(path), "-af",
                    f"{trim},areverse,{trim},areverse", "-b:a", "192k", str(tmp)], check=True)
    tmp.replace(path)


def duration(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]))

def main():
    global OUT, STYLE
    args = sys.argv[1:]
    segments = SEGMENTS
    if args and args[0] in SHORTS:
        segments, OUT, STYLE = SHORTS[args[0]], OUT / args[0], STYLE + SHORT_PACE
        args = args[1:]
    OUT.mkdir(parents=True, exist_ok=True)
    only = set(args)
    durations = {}
    for key, text in segments.items():
        path = OUT / f"{key}.mp3"
        if not only or key in only or not path.exists():
            tts(text, path)
            trim_silence(path)
        durations[key] = round(duration(path), 2)
        print(key, durations[key])
    (OUT / "durations.json").write_text(json.dumps(durations, indent=2))


# ---------------------------------------------------------------- shorts: one continuous take
SHORT_STYLE = (
    "Read this as one continuous, flowing take, like a friendly person casually telling a friend about something useful. "
    "Conversational and upbeat, natural pitch movement, connected phrasing. Keep moving from one sentence to the next "
    "with only the tiny breath a person would naturally take. No dramatic pauses, no announcer voice."
)


def cap_pauses(path, keep=0.22):
    """Shorten any internal pause longer than ~0.3s to `keep` seconds."""
    tmp = path.with_suffix(".tmp.mp3")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(path), "-af",
                    f"silenceremove=stop_periods=-1:stop_duration=0.3:stop_threshold=-42dB:stop_silence={keep}",
                    "-b:a", "192k", str(tmp)], check=True)
    tmp.replace(path)


def word_timestamps(path):
    import uuid
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in (("model", "whisper-1"), ("response_format", "verbose_json"), ("timestamp_granularities[]", "word")):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="a.mp3"\r\nContent-Type: audio/mpeg\r\n\r\n'.encode()
                 + path.read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request("https://api.openai.com/v1/audio/transcriptions", data=b"".join(parts), headers={
        "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)["words"]


def norm(word):
    return "".join(ch for ch in word.lower() if ch.isalnum())


def segment_starts(segments, words):
    """Find where each segment's first word is spoken: exact match first, then a 4-letter prefix (practise/practice)."""
    starts, i = {}, 0
    for key, text in segments.items():
        first = norm(text.split()[0])
        found = next((j for j in range(i, len(words)) if norm(words[j][0]) == first), None)
        if found is None:
            found = next((j for j in range(i, len(words)) if norm(words[j][0])[:4] == first[:4]), None)
        if found is None:
            raise SystemExit(f"could not find the start of '{key}' ({first}) in the transcript")
        starts[key], i = words[found][1], found + 1
    return starts


def make_short(name):
    """One TTS take for the whole short, plus a timeline the video uses for scene cuts."""
    segments = SHORTS[name]
    out = ROOT / "voiceover" / name
    out.mkdir(parents=True, exist_ok=True)
    path = out / "full.mp3"
    body = json.dumps({"model": MODEL, "voice": VOICE, "input": " ".join(segments.values()), "instructions": SHORT_STYLE,
                       "response_format": "mp3"}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/audio/speech", data=body, headers={
        "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        path.write_bytes(r.read())
    trim_silence(path)
    cap_pauses(path)
    words = [[w["word"], round(w["start"], 2), round(w["end"], 2)] for w in word_timestamps(path)]
    timeline = {"duration": round(duration(path), 2), "starts": segment_starts(segments, words), "words": words}
    (out / "timeline.json").write_text(json.dumps(timeline, indent=1))
    print(name, timeline["duration"], timeline["starts"])


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--short":
        for name in sys.argv[2:]:
            make_short(name)
    else:
        main()
