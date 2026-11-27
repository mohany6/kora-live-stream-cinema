# كورة لايف — Arabic Football Live Score & Streaming Platform

RTL-first football matchday portal: KoraCity-style schedule cards, a hybrid match center with multi-server streams, tactical lineups on a pitch, live stats, standings, and an admin CMS API with emergency score/stream overrides.

This project is intentionally standalone and lives **outside** the radar project:

```
C:\Users\Mohany\Desktop\football-live-score-platform
```

---

## What is implemented

| Area | Status |
|---|---|
| Domain models + 3-tier priority resolver (`Admin > API > Scraper`) | ✅ |
| livescoreFootball v2 ingestion (real fixtures, summaries, standings) | ✅ |
| Arabic team alias matcher (accent-tolerant English lookup) | ✅ |
| Stream scraper adapter (iframes, `.m3u8`, quality detection, sandboxing) | ✅ |
| FastAPI public schedule + hybrid match detail API | ✅ |
| Admin stream add/edit/delete + manual score/status override API | ✅ |
| SQLite persistence so admin overrides survive API sync + restart | ✅ |
| PRD + Figma-ready design tokens (`design/tokens.json`) | ✅ |
| React + Tailwind RTL home schedule (Option A) | ✅ |
| Hybrid match center: stream player, timeline, pitch, stats, standings | ✅ |
| Backend tests (67) + frontend tests (21) | ✅ |

---

## Project structure

```
football-live-score-platform/
├── design/
│   └── tokens.json                 # RTL/Figma token contract
├── docs/superpowers/
│   ├── plans/2026-11-18-football-live-score-platform.md
│   └── specs/
│       ├── 2026-11-18-football-live-score-platform-design.md
│       └── PRD.md
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── MatchCard.jsx
│   │   │   ├── ScheduleFilterTabs.jsx
│   │   │   ├── StreamPlayerContainer.jsx
│   │   │   ├── TacticalPitchView.jsx
│   │   │   ├── MatchDetailHybrid.jsx
│   │   │   └── __tests__/
│   │   ├── lib/
│   │   └── test/
│   ├── package.json
│   └── vite.config.js
├── src/live_score/
│   ├── domain/                     # models.py, resolver.py
│   ├── adapters/                   # livescore_v2.py, livescore_client.py, scraper_adapter.py
│   └── api/                        # app.py, public_routes.py, admin_routes.py,
│                                   # catalog.py, schemas.py, store.py, presenters.py, fixtures.py
├── tests/live_score/
│   ├── test_resolver.py
│   ├── test_adapters.py
│   ├── test_livescore_v2.py
│   ├── test_api.py
│   └── test_tokens.py
├── conftest.py
├── pytest.ini
├── requirements.txt
├── run.py
└── .env.example
```

---

## Quick start

### 1. Backend

The project already contains a local `.venv` (Python 3.12).

```powershell
cd C:\Users\Mohany\Desktop\football-live-score-platform
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

API: `http://127.0.0.1:8000`  
Swagger: `http://127.0.0.1:8000/docs`  
Health: `http://127.0.0.1:8000/health`

Environment variables (see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `LIVE_SCORE_ADMIN_TOKEN` | `dev-admin-token` | Required `X-Admin-Token` for admin writes. |
| `LIVE_SCORE_DB_PATH` | `data/live_score.db` | SQLite file for overrides/admin streams. |
| `LIVE_SCORE_TIMEZONE` | `Asia/Riyadh` | Default display timezone. |
| `LIVE_SCORE_API_URL` | empty (ESPN primary) | Hosted livescoreFootball API. Defaults to ESPN primary with `worldcup26.ir` secondary. Set `demo` to force offline demo data. |
| `LIVE_SCORE_SCRAPER_URL` | empty (disabled) | Optional streaming portal URL for automated live stream scraping. |
| `LIVE_SCORE_LEAGUES` | 10 top competitions | Comma-separated upstream slugs (e.g. `eng.1,esp.1,uefa.champions`). |
| `LIVE_SCORE_ESPN_FALLBACK` | `on` | Automatic failover between ESPN and the hosted API (5-minute cooldown). |
| `LIVE_SCORE_SNAPSHOT` | `on` | Persist the last good live slate (set `off` to disable). |
| `LIVE_SCORE_SNAPSHOT_PATH` | `data/live_fixtures_snapshot.json` | Snapshot file used after a restart during an outage. |
| `LIVE_SCORE_SNAPSHOT_MAX_AGE_HOURS` | `36` | Ignore snapshots older than this. |
| `LIVE_SCORE_CORS_ORIGINS` | Vite local origins | Comma-separated CORS allowlist. |

### 2. Frontend

Node.js/npm are vendored inside `.tools/node-v22.14.0-win-x64` for this project. No system-wide install is required.

```powershell
cd C:\Users\Mohany\Desktop\football-live-score-platform\frontend
$node = "..\.tools\node-v22.14.0-win-x64"
$env:Path = "$(Resolve-Path $node);$env:Path"
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

`VITE_API_BASE_URL` defaults to `http://127.0.0.1:8000`. The Vite dev server also proxies `/api` to the backend.

### 3. Tests

```powershell
# Backend
cd C:\Users\Mohany\Desktop\football-live-score-platform
.\.venv\Scripts\python.exe -m pytest -q

# Frontend
cd frontend
$env:Path = "$(Resolve-Path ..\.tools\node-v22.14.0-win-x64);$env:Path"
npm test
```

---

## API overview

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/matches/today?date=YYYY-MM-DD&tz=Asia/Riyadh` | Option A schedule cards. |
| GET | `/api/v1/matches/{match_id}` | Hybrid match center payload. |
| POST | `/api/v1/admin/matches/{match_id}/streams` | Add/edit a stream server. |
| DELETE | `/api/v1/admin/matches/{match_id}/streams/{server_id}` | Remove an admin stream. |
| POST | `/api/v1/admin/matches/{match_id}/override` | Manual score/status/broadcast override. |
| DELETE | `/api/v1/admin/matches/{match_id}/override` | Clear the override. |
| GET | `/health` | Liveness + fixture count. |

Admin requests require:

```http
X-Admin-Token: dev-admin-token
```

### Example: force a final score

```powershell
$headers = @{ "X-Admin-Token" = "dev-admin-token" }
$body = @{
  home_score = 3
  away_score = 0
  status = "FINISHED"
  elapsed_time = 90
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/admin/matches/match_clasico/override `
  -Headers $headers -ContentType "application/json" -Body $body
```

The override is persisted in SQLite and re-applied after every API/scraper sync.

---

## Design decisions

- **Zero video proxying:** streams are embedded directly client-side. Iframe embeds are sandboxed; URLs must be absolute `http(s)`.
- **Admin precedence is read-time:** base fixtures may refresh freely, but stored admin patches are applied last, so automated sync can never silently overwrite an emergency decision.
- **Live data by default:** fixtures come from ESPN's public soccer API, with
  the [livescoreFootball API](https://worldcup26.ir/football-api) as an
  automatic secondary, across 10 top competitions (Europe's big five, the three
  UEFA club competitions, and the Saudi and Turkish leagues). The two providers
  share the same payload shape; if one fails the other is used for five
  minutes before retrying the primary. A five-day window is cached for 25
  seconds; match summaries (lineups, timeline, stats, standings) hydrate lazily
  when a match is opened. The frontend polls today's slate and the open match
  center every 30 seconds.
- **Graceful degradation:** upstream failures keep the last good snapshot;
  the demo matchday is used only when no live snapshot has ever loaded.
  `LIVE_SCORE_API_URL=demo` forces the offline demo. The last live slate is
  also persisted to `data/live_fixtures_snapshot.json`, so a restart during an
  upstream outage still serves real fixtures.
- **Arabic UI, Latin player names:** team names, competitions, and events are Arabic; pitch players use Latin/English names (Option B).
- **UTC storage, local presentation:** `Asia/Riyadh` by default with `Africa/Casablanca`, `Africa/Cairo`, `Asia/Dubai`, `Europe/London`, and `UTC` labels.

See `docs/superpowers/specs/PRD.md` for the full data contracts, lifecycle state machine, failover flow, ERD, acceptance criteria, and test matrix.

---

## Live data source

Default upstream (no API key):

```text
https://worldcup26.ir/get/soccer
```

| Endpoint | Used for |
|---|---|
| `GET /{slug}/fixtures?status=all&from=YYYYMMDD&to=YYYYMMDD&limit=200` | Five-day fixture window per league. |
| `GET /{slug}/events/{event_id}` | Lineups, formation, timeline, stats, venue/referee. |
| `GET /{slug}/standings?season=YYYY` | League table with the two clubs highlighted. |

Default leagues: `eng.1, eng.2, esp.1, esp.2, ita.1, ger.1, fra.1, ned.1,
por.1, sco.1, bel.1, tur.1, ksa.1, usa.1, mex.1, arg.1, bra.1, jpn.1`.

`GET /health` reports the active data source and last refresh time:

```json
{
  "status": "ok",
  "data_source": "live",
  "matches": 61,
  "leagues": 18,
  "last_refresh": "2026-11-19T03:09:21Z",
  "last_error": null
}
```

### Demo matchday

Set `LIVE_SCORE_API_URL=demo` (or run with the upstream unreachable and no
cached snapshot) to serve four deterministic fixtures:

- ريال مدريد vs برشلونة — live, 68', 2-1, full lineups/stats/standings.
- الهلال vs النصر — scheduled, countdown.
- ليفربول vs مانشستر سيتي — finished, 1-1.
- الوداد vs الرجاء — postponed.
