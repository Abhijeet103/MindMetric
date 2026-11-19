"""Scheduled entrypoint: preflight locally, then let Claude's demo skill orchestrate the run."""
from __future__ import annotations

import argparse
import json
import runpy
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "video/scripts/marketing-workflow.py"
PROMPT = ROOT / "docs/claude-marketing-run.md"


def preflight():
    process = subprocess.run(
        [sys.executable, str(WORKFLOW), "due"], cwd=ROOT,
        text=True, capture_output=True, check=False,
    )
    if process.returncode not in (0, 10):
        return {"status": "failed", "reason": "Workflow schedule check failed"}
    due = json.loads(process.stdout)
    if not due["due"]:
        return {"status": "skipped", "reason": due["reason"], "schedule": due}
    tts = runpy.run_path(str(ROOT / "video/scripts/marketing-tts.py"))
    cfg = json.loads((ROOT / "video/marketing/config.json").read_text())
    try:
        provider = tts["get_provider"](cfg["tts"], ROOT)
        import datetime
        provider.check_available(datetime.datetime.now(datetime.timezone.utc).date())
    except tts["TTSUnavailable"] as error:
        return {"status": "blocked_audio", "reason": str(error), "schedule": due}
    if not shutil.which("claude"):
        return {"status": "failed", "reason": "Claude CLI is unavailable"}
    return {"status": "ready", "schedule": due}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Preflight only; no Claude or TTS requests")
    args = parser.parse_args()
    state = preflight()
    if args.check or state["status"] != "ready":
        print(json.dumps(state, indent=2))
        return 1 if state["status"] == "failed" else 0
    command = [
        "claude", "-p", "--permission-mode", "dontAsk",
        "--allowedTools", "Skill", "Read", "Bash(python3 video/scripts/marketing-workflow.py *)",
        "--tools", "Skill,Read,Bash", "--output-format", "json", "--no-session-persistence",
    ]
    process = subprocess.run(
        command, input=PROMPT.read_text(), cwd=ROOT,
        text=True, capture_output=True, timeout=3600, check=False,
    )
    if process.returncode:
        # Avoid exposing provider responses or accidental credentials through stderr.
        print(json.dumps({"status": "failed", "reason": "Claude orchestration failed", "exit_code": process.returncode}))
        return 1
    result = json.loads(process.stdout)
    print(json.dumps({"status": "claude_finished", "summary": result.get("result", ""), "is_error": result.get("is_error", False)}, indent=2))
    return 1 if result.get("is_error") else 0


if __name__ == "__main__":
    raise SystemExit(main())
