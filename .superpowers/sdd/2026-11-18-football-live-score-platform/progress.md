# SDD ledger — plan: docs/superpowers/plans/2026-11-18-football-live-score-platform.md

## Pre-flight Conflict Scan

| Pair / Task | Produces vs Consumes | Findings | Ruling |
|---|---|---|---|
| Task 1 (Models & Resolver) | Produces `Match`, `Team`, `StreamServer`, `PriorityResolver` | Self-contained, agrees with spec. | Clean |
| Task 1 -> Task 2 (Adapters) | Task 2 consumes `Match` domain models from Task 1 | Interface consistent across schemas. | Clean |
| Task 1 & 2 -> Task 3 (API) | Task 3 consumes domain models and resolver | Public & admin routes expose agreed REST specs. | Clean |
| Task 4 (PRD & Tokens) | Produces `PRD.md` and `design/tokens.json` | Agrees with Option A & Hybrid spec; no code conflicts. | Clean |
| Task 3 & 4 -> Task 5 (Card UI) | Task 5 consumes `/api/v1/matches/today` and tokens | RTL card layout aligns with Option A. | Clean |
| Task 3 & 5 -> Task 6 (Hybrid Detail) | Task 6 consumes `/api/v1/matches/{id}` and stream server array | Video container + tactical tabs match spec. | Clean |

---

## Task Progress

- [x] Task 1: Core Domain Models & Priority Data Resolver — complete (review clean: spec ✅, quality approved)
- [x] Task 2: Upstream Ingestion Adapters (livescoreFootball client & Scraper stub) — complete (review clean)
- [x] Task 3: Admin CMS & Match Stream Override API — complete
- [x] Task 4: PRD Specification Document & Figma Design System Tokens — complete
- [x] Task 5: Frontend Match Card & Home Schedule Component (Option A - RTL) — complete
- [x] Task 6: Hybrid Match Detail Screen (Stream Player + Tactical Center) — complete

---

## Environment Rulings

| Topic | Ruling |
|---|---|
| Project location | Relocated to `C:\Users\Mohany\Desktop\football-live-score-platform`, outside the radar repository. |
| Git | No git executable or repository is available in this environment. All plan "Commit" steps were skipped; no commits were created. |
| Python environment | Self-contained `.venv` with Python 3.12 in the new project; the radar repo `venv` is not used. |
| Node.js | Vendored project-locally at `.tools/node-v22.14.0-win-x64`; no system Node/npm installation. |
| API shape | Responses use snake_case; extra modules (`schemas.py`, `store.py`, `presenters.py`, `fixtures.py`) support the planned routes. |
| Admin precedence | Overrides persist in SQLite and are re-applied at read time; admin streams are prepended to base streams. |
| Timezone | Default `Asia/Riyadh`; the frontend computes schedule dates in Mecca time so "today" matches the API. |

---

## Task 3 Deliverables

- `src/live_score/api/app.py` — FastAPI application factory and CORS/Cache-Control wiring.
- `src/live_score/api/public_routes.py` — `GET /health`, `/api/v1/matches/today`, `/api/v1/matches/{id}`.
- `src/live_score/api/admin_routes.py` — token-protected stream upsert/delete and match override set/clear.
- `src/live_score/api/store.py` — SQLite persistence for overrides and admin stream servers.
- `src/live_score/api/presenters.py` — admin > API > scraper precedence and Arabic response shaping.
- `src/live_score/api/fixtures.py` — demo matchday + optional `LIVE_SCORE_API_URL` ingestion.
- `src/live_score/api/schemas.py` — public/admin response models.
- `tests/live_score/test_api.py` — 13 API contract tests.

## Task 4 Deliverables

- `docs/superpowers/specs/PRD.md` — product requirements, state schemas, API contracts, failover rules, ERD.
- `design/tokens.json` — RTL spacing, dark-mode neutrals, live/countdown/pitch colors.
- `tests/live_score/test_tokens.py` — 7 token/schema tests.

## Tasks 5–6 Deliverables

- `frontend/src/components/MatchCard.jsx` — Option A RTL match card with live, countdown, finished and postponed states.
- `frontend/src/components/ScheduleFilterTabs.jsx` — yesterday/today/tomorrow tabs.
- `frontend/src/components/StreamPlayerContainer.jsx` — sandboxed iframe + HLS player, server pills, watchdog and Arabic fallback.
- `frontend/src/components/TacticalPitchView.jsx` — combined pitch with Latin player names (Option B).
- `frontend/src/components/MatchDetailHybrid.jsx` — hybrid header, player, timeline, lineup, stats and standings tabs.
- `frontend/src/lib/api.js`, `frontend/src/lib/format.js` — API client, Mecca-time date helper and formatters.
- `frontend/src/components/__tests__/` and `frontend/src/lib/__tests__/` — 21 Vitest tests.

---

## Verification (2026-11-18)

| Check | Result |
|---|---|
| Backend suite (`pytest -q`) | 46 passed |
| Frontend suite (`npm test`) | 21 passed (5 files) |
| Production build (`npm run build`) | Succeeded (Vite 6.4.6) |
| `GET /health` | `{"status":"ok","matches":4,"timezone":"Asia/Riyadh"}` |
| `GET /api/v1/matches/today` | 4 demo matches with Arabic labels |
| `GET /api/v1/matches/match_clasico` | Full detail: 4 servers, lineups, events, stats, standings |
| Admin auth | Wrong token returns 401; valid token accepts mutations |
| Admin override | Set 3–1/FINISHED, read path reflected `is_admin_override=true`, clear restored 2–1/IN_PLAY |
| Admin stream | Added server appeared first, delete restored the base list |
| Browser smoke | Home + detail, timeline/lineup/stats/standings, RTL and dark theme verified with no console errors |
