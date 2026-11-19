"""Replaceable text-to-speech adapter for the marketing-short workflow.

The workflow only talks to `get_provider(cfg)` and `TTSProvider.synthesize()`. To switch
providers, add a class with the same interface and register it in PROVIDERS; nothing else
in the workflow needs to change.

OpenAI is the only narration provider (ElevenLabs is intentionally not supported).

DEPRECATION: OpenAI's docs state the gpt-4o-mini-tts Speech API model shuts down on
2027-01-06. MODEL_SHUTDOWN below makes the adapter refuse that model from that date, so
runs degrade to `blocked_audio` drafts instead of failing mid-render. Migrate the
adapter to OpenAI's Realtime API before then; changing only tts.model is insufficient.
https://developers.openai.com/api/docs/guides/text-to-speech

Secrets: the API key is read at runtime from the environment, or from the exact
`OPENAI_API_KEY=` line of a configured .env file. It is never printed, logged, written
to disk, or included in error messages.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

MODEL_SHUTDOWN = {name: dt.date(2027, 1, 6) for name in ("gpt-4o-mini-tts", "tts-1", "tts-1-hd")}
SHUTDOWN_WARN_DAYS = 60
OPENAI_SPEECH_URL = "https://api.openai.com/v1/audio/speech"


class TTSUnavailable(Exception):
    """Narration cannot be produced; the workflow turns this into status blocked_audio."""


def load_api_key(env_name: str, dotenv_files: list[Path]) -> str | None:
    value = os.environ.get(env_name, "").strip()
    if value:
        return value
    prefix = f"{env_name}="
    for path in dotenv_files:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            line = line.strip()
            if line.startswith("export "):
                line = line[7:].lstrip()
            if line.startswith(prefix):
                value = line[len(prefix):].strip().strip('"').strip("'")
                if value:
                    return value
    return None


class TTSProvider:
    name = "base"
    model = ""
    voice = ""

    def check_available(self, today: dt.date) -> list[str]:
        """Raise TTSUnavailable if unusable; return warnings otherwise."""
        raise NotImplementedError

    def synthesize(self, text: str, out_path: Path) -> None:
        raise NotImplementedError


class NoAudioProvider(TTSProvider):
    name = "none"

    def check_available(self, today):
        raise TTSUnavailable("TTS provider is set to 'none'")

    def synthesize(self, text, out_path):
        raise TTSUnavailable("TTS provider is set to 'none'")


class OpenAISpeechProvider(TTSProvider):
    name = "openai"

    def __init__(self, model: str, voice: str, instructions: str, api_key: str | None,
                 max_requests: int, opener=urllib.request.urlopen):
        self.model, self.voice, self.instructions = model, voice, instructions
        self._api_key = api_key
        self.max_requests = max_requests
        self.requests_made = 0
        self._opener = opener

    def __repr__(self):  # never expose the key
        return f"OpenAISpeechProvider(model={self.model!r}, voice={self.voice!r}, key={'set' if self._api_key else 'missing'})"

    def check_available(self, today):
        if not self._api_key:
            raise TTSUnavailable("OPENAI_API_KEY is not set (environment or configured .env)")
        if self.model.startswith("gpt-realtime"):
            raise TTSUnavailable("Realtime models need a Realtime API adapter; they cannot use audio/speech")
        shutdown = MODEL_SHUTDOWN.get(self.model)
        if shutdown and today >= shutdown:
            raise TTSUnavailable(f"{self.model} Speech API shut down on {shutdown.isoformat()}; migrate the OpenAI audio adapter to the Realtime API")
        warnings = []
        if shutdown and (shutdown - today).days <= SHUTDOWN_WARN_DAYS:
            warnings.append(f"{self.model} shuts down on {shutdown.isoformat()} ({(shutdown - today).days} days); plan the model switch")
        return warnings

    def synthesize(self, text, out_path):
        if self.requests_made >= self.max_requests:
            raise TTSUnavailable(f"TTS request budget of {self.max_requests} per run reached")
        self.requests_made += 1
        body = json.dumps({"model": self.model, "voice": self.voice, "input": text,
                           "instructions": self.instructions, "response_format": "mp3"}).encode()
        req = urllib.request.Request(OPENAI_SPEECH_URL, data=body, headers={
            "Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"})
        try:
            with self._opener(req, timeout=120) as resp:
                data = resp.read()
        except urllib.error.HTTPError as e:
            # Only the status code: error bodies can echo parts of the credential.
            raise TTSUnavailable(f"OpenAI speech request failed with HTTP {e.code}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise TTSUnavailable(f"OpenAI speech request failed: {type(e).__name__}") from None
        if len(data) < 1000:
            raise TTSUnavailable("OpenAI speech response was unexpectedly small")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = out_path.with_suffix(".part")
        tmp.write_bytes(data)
        tmp.replace(out_path)


def get_provider(tts_cfg: dict, repo_root: Path) -> TTSProvider:
    name = tts_cfg.get("provider", "openai")
    if name == "none":
        return NoAudioProvider()
    if name == "openai":
        key = load_api_key(tts_cfg.get("api_key_env", "OPENAI_API_KEY"),
                           [repo_root / p for p in tts_cfg.get("dotenv_files", [])])
        return OpenAISpeechProvider(tts_cfg["model"], tts_cfg["voice"], tts_cfg.get("instructions", ""),
                                    key, int(tts_cfg.get("max_requests_per_run", 6)))
    raise TTSUnavailable(f"Unknown TTS provider {name!r} (supported: openai, none)")
