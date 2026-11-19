# MindMetric marketing shorts

A reusable local workflow that turns a topic into a **1080x1920, 30fps, 30-60s** product short made from
real, pre-existing MindMetric screenshots, with an English AI voiceover (OpenAI TTS only), burned-in
subtitles that match the narration, a CTA to **mindmetric.store**, and draft post copy for each platform.

It **never publishes**, schedules external posts, calls a social network, deploys, or touches git.
Both channels (`youtube_shorts`, `instagram_reels`) stay `awaiting_connection` until publishing
accounts and adapters are connected. The user has authorized automatic publishing after quality
checks. Claude performs the visual review; per-video human approval is not required.

## Layout

| Path | What it is |
| --- | --- |
| `video/marketing/config.json` | schedule, duration limits, TTS provider/model/voice, disclosure text, channel status |
| `video/marketing/topics.json` | rotation order, per-scene screenshots/crops/callouts, narration script, **claims with codebase evidence**, captions |
| `video/marketing/layout.json` | 1080x1920 boxes and font sizes, shared by the renderer and the QC |
| `video/marketing/src/` | separate Remotion entrypoint (`index.ts` → composition `MarketingShort`). `video/src` (MainVideo) is not touched |
| `video/scripts/marketing-workflow.py` | CLI: due check, rotation, lock, audio, QC, render, captions, status |
| `video/scripts/marketing-tts.py` | replaceable TTS adapter (OpenAI Speech API) |
| `video/marketing/tests/` | unit tests (no network, no render) |
| `video/marketing/output/` | **git-ignored**: `runs/<run_id>/` (mp4, props, captions, status, stills), `tts-cache/` |
| `video/marketing/state/` | **git-ignored**: `state.json` (rotation + history), `run.lock` |

## Commands

Run from the repository root. Requires the already-installed `video/node_modules` (Remotion 4.0.290), `ffmpeg`/`ffprobe`, Python 3.9+.

```bash
# Is a run due? Every 2 days at 19:00 Asia/Kolkata, starting 2026-11-15. Exit 0 = due, 10 = not due.
python3 video/scripts/marketing-workflow.py due
python3 video/scripts/marketing-workflow.py due --now 2026-11-17T19:05:00+05:30

# Rotation, next topic, channels, recent runs
python3 video/scripts/marketing-workflow.py status
python3 video/scripts/marketing-workflow.py topics

# Scheduled run: does nothing unless the current slot is open (use this from a scheduler)
python3 video/scripts/marketing-workflow.py run --if-due

# Manual run of the next topic in rotation (TTS if OPENAI_API_KEY is available, otherwise a blocked_audio draft)
python3 video/scripts/marketing-workflow.py run

# Sample that reuses the pre-existing MainVideo narration (no new TTS; labelled reused_existing_audio)
python3 video/scripts/marketing-workflow.py run --audio existing --topic gia-instant-feedback

# Plan + QC + captions only: no TTS calls, no render, no state change
python3 video/scripts/marketing-workflow.py run --dry-run --topic gia-full-timed-test

# Re-run a slot that already completed
python3 video/scripts/marketing-workflow.py run --force

# Tests
python3 -m unittest discover -s video/marketing/tests -v

# Type-check the Remotion entry / preview it in Studio
cd video && npx --no-install tsc --noEmit --jsx react-jsx --strict --skipLibCheck --esModuleInterop \
  --resolveJsonModule --moduleResolution bundler --module esnext --target es2020 marketing/src/index.ts
cd video && npx remotion studio marketing/src/index.ts \
  --props=marketing/output/runs/<run_id>/props.json --public-dir=marketing/output/runs/<run_id>/public
```

`run` options: `--if-due`, `--topic ID`, `--audio auto|existing|none`, `--force`, `--dry-run`, `--now ISO+offset`.

Exit codes: `0` ok · `2` failed (see `errors` in the run's `status.json`) · `3` another run holds the lock · `10` not due · `11` this slot already has a completed run.

### Scheduling

The active app automation **MindMetric demo shorts** runs every two days at 19:00 IST.
It invokes `python3 scripts/run_claude_marketing.py`, which preflights the schedule and
OpenAI key, then invokes the authenticated Claude CLI and this project's demo-video
skill. Keep this computer and the desktop app running for these local jobs. Claude's
run instructions are in `docs/claude-marketing-run.md`.

`python3 scripts/run_claude_marketing.py --check` performs preflight without Claude or
TTS calls. Missing narration credentials block the scheduled entrypoint before rendering.
The direct media CLI can still render explicitly labelled silent drafts for layout review.
No social publishing is implemented or enabled yet.

Rules: a slot is consumed only by a **completed** run. A missed slot is caught up once, not once per missed slot.
A failed run does not consume the slot or advance the rotation, so it is retried on the next check. After 3 failures
in the same slot `due` reports `blocked_after_failures` and stops retrying until you fix it and use `--force`.
The rotation advances when the topic due in the rotation completes with narration. A
`draft_blocked_audio` run keeps the same topic and slot available for retry after credentials are configured;
`--topic` runs of a different topic do not move it.

## Statuses (in `output/runs/<run_id>/status.json` and `state/state.json`)

| Field | Values |
| --- | --- |
| `status` | `completed`, `failed`, `dry_run` (CLI also prints `skipped_not_due`, `skipped_duplicate`, `skipped_locked`) |
| `output_status` | `narrated_draft_ready_for_review`, `draft_blocked_audio`, `not_rendered`, `failed` |
| `audio.status` | `generated_tts`, `reused_existing_audio`, `blocked_audio` (with `reason`) |
| `channels.*` | `awaiting_connection` |
| `qc.pre_render` / `qc.post_render` | per-check `ok` + `detail` |
| `screenshots[]` | source path, sha256, file mtime, provenance `pre-existing capture … (not recorded by this workflow)` |

Every video remains a **draft until publishing is connected**; Claude conducts visual quality review. A `draft_blocked_audio` video is silent, carries an amber
`DRAFT: no voiceover yet` label, gets a `-DRAFT-no-audio.mp4` file name, and its captions say not to post it.

## Narration (OpenAI TTS only)

* Provider, model and voice live in `config.json` → `tts`. The adapter (`marketing-tts.py`) is the only code that
  talks to a TTS API; add a class with `check_available()` / `synthesize()` and register it in `get_provider()` to swap it.
  ElevenLabs is intentionally not supported.
* **Deadline:** OpenAI's docs say the `gpt-4o-mini-tts` Speech API model **shuts down on 2027-01-06**. The adapter
  warns within 60 days of that date and refuses the model from that date on, so runs become `blocked_audio`
  drafts instead of failing. Migrate the adapter to the Realtime API before then: **changing only
  `tts.model` is insufficient**. The recommended `gpt-realtime-2.1-mini` cannot use `/v1/audio/speech`.
  Verified against [OpenAI's TTS documentation](https://developers.openai.com/api/docs/guides/text-to-speech).
* **Credentials:** `OPENAI_API_KEY` is read at runtime from the environment, or from that exact line in `.env` /
  `video/.env`. It is never printed, logged, written to output, or put into error messages (only HTTP status codes).
  No key → `blocked_audio`, never a silent "narrated" claim. Today the project `.env` has no key.
* **Cost guard:** at most `max_requests_per_run` (6) speech requests per run, one per scene. Audio is cached in
  `output/tts-cache/` by provider+model+voice+instructions+text, so re-runs and re-renders do not pay again.
  (Do not use the old `video/scripts/generate-voiceover.py` for this; it regenerates everything.)
* `--audio existing` reuses the narration files listed in a topic's `existing_audio` (currently the MainVideo
  `voiceover/*.mp3`, originally generated with OpenAI `gpt-4o-mini-tts`). Subtitles then use that audio's exact text,
  and the run is recorded as `reused_existing_audio` with file hashes and "No new TTS was generated".

## AI disclosure and claims

* On screen: `AI-generated voiceover` pill for the whole video (or the amber DRAFT pill when there's no audio).
* Post copy: every caption carries the AI-voiceover line, "Screens are real MindMetric product screenshots." and
  the independence disclaimer. QC fails a run if any caption lacks the disclosure.
* Each topic lists its claims with the file/screenshot that backs them. QC blocks wording like *official,
  endorsed, certified, guaranteed, pass rate, real/actual questions, past papers, 100%*. The CTA states
  "Independent practice. Not affiliated with any test publisher." (from `templates/base.html`).

## Quality checks

Pre-render (blocks the render): assets exist · 30-60s duration · each narration segment fits its scene ·
all boxes ≥ 60px from every edge and subtitles/callouts/CTA clear of the bottom 340px platform UI · fonts ≥ 28px ·
estimated line wrapping keeps headlines, labels, URLs, callouts, subtitles and CTA within their line limits ·
screenshot crops in bounds and ≥ 0.5x scale (mobile readability) · subtitle text equals narration text ·
hook → demo → CTA structure with `mindmetric.store` · banned-claims scan · captions checks.

Post-render (marks the run failed): 1080x1920 · 30fps · duration matches the plan · narrated: audio present,
mean volume > -45 dB and not longer than the video; drafts: no audible audio. Review stills (first frame plus
early/late frame of each scene) are written to `stills/` for Claude's visual review before any future publishing.

Limits: text fitting is an estimate (average glyph width), which is why the stills exist. Subtitle timing is
spread across each narration segment in proportion to text length, not word-aligned.

## Adding a topic

Add an object to `topics.json` → `topics` (order = rotation). Use only screenshots that exist in
`video/public/shots/`; crops are in 2560x1440 source pixels (height is derived; keep `w` ≤ 1920 for the
0.5x readability limit). Add each claim with evidence, then run
`python3 video/scripts/marketing-workflow.py run --dry-run --topic <id>` and the tests.
