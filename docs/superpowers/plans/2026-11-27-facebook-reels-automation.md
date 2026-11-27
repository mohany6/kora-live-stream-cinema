# Facebook Reels Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Automate generation and publishing of vertical `1080x1920` Arabic Cyber-Stadium Facebook Reels with Edge-TTS voiceover, 3-second viral hooks, per-match hashtags, and first-comment Blogger links.

**Architecture:** Python builds the 4-scene match script + Edge-TTS MP3 audio, passes props JSON to a Remotion (`1080x1920`, `30fps`) composition to render an original H.264/AAC MP4, then uploads via Meta Graph API `POST /{page_id}/video_reels` (3-step upload) and posts the Blogger URL in the first comment.

**Tech Stack:** Python 3.12, `edge-tts`, Node 26 + Remotion 4, Meta Graph API v25.0, pytest.

**Spec:** [2026-11-27-facebook-reels-automation-design.md](file:///C:/Users/Mohany/Desktop/football-live-score-platform/docs/superpowers/specs/2026-11-27-facebook-reels-automation-design.md)

## Global Constraints
- `1080x1920` (9:16), `30fps`, MP4 (`H.264` + `AAC`, `faststart`).
- Zero `http://` or `https://` URLs inside Reel `description`/`caption`; Blogger link strictly in first comment.
- Zero watermarks; 100% original Cyber-Stadium motion graphics.
- 30-minute pre-match window enforced in `mode="auto"` with `data/published_facebook_reels.json` deduplication.

## Tasks
- [ ] **Task 1:** Add `edge-tts` and create `src/live_score/domain/facebook_reel_script.py` (4-scene Arabic script + Edge-TTS synthesizer + Reel caption/comment builder).
- [ ] **Task 2:** Scaffold `video_reels/` Remotion project with `MatchReel` (`1080x1920`, `30fps`, `Series` scenes, Arabic RTL, club logos, audio track).
- [ ] **Task 3:** Create `scripts/auto_facebook_reels_publisher.py` with Remotion CLI invocation, 3-step `/{page_id}/video_reels` upload, first-comment link, 30m pre-match gate in `auto` mode, and `published_facebook_reels.json` cache.
- [ ] **Task 4:** Update `.github/workflows/sync_and_publish.yml` and `requirements.txt` for CI execution.
- [ ] **Task 5:** Write `tests/test_facebook_reels_publisher.py`, run full pytest suite, and verify real MP4 render.
