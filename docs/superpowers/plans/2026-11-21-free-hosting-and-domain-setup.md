# Free Hosting & Free Domain Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide zero-cost global hosting from the user's local machine, unifying frontend SPA assets with the FastAPI backend onto a single port (8000) and enabling free public HTTPS exposure via Cloudflare Quick Tunnel and DuckDNS.

**Architecture:** The production FastAPI application mounts the compiled React distribution (`frontend/dist`) as static assets with an SPA catch-all fallback for client-side routes like `/admin`. A portable runner manages the `cloudflared` binary to expose `http://127.0.0.1:8000` via a secure, worldwide HTTPS URL without port-forwarding or public IP requirements. An auxiliary DuckDNS synchronization script provides automated DDNS updates for permanent named subdomains.

**Tech Stack:** Python 3.12, FastAPI, Starlette StaticFiles, Uvicorn, Cloudflared Tunnel, React (Vite build), DuckDNS API.

**Spec:** `docs/superpowers/specs/2026-11-21-free-hosting-and-domain-setup-design.md`

## Global Constraints

- 100% Free: No credit cards, trial traps, or paid services required.
- Single Port Production: Entire app (HTML, CSS, JS, API, Admin, Video Player, Ads) must run out of port 8000.
- Zero CORS regressions: Client-side routing to `/admin` and API polling must function seamlessly both locally and through public tunnel URLs.
- 100% test suite passing: All existing 124 Pytest, 41 Vitest, and 48 Live tests must continue passing.

## Review Focus

1. SPA Fallback Routing: Requesting `/` or `/admin` directly in the browser must return `index.html` with status 200 and `Content-Type: text/html`.
2. Static Asset Delivery: Files under `/assets/*` (JS, CSS) must be served with proper MIME types and caching headers.
3. API Route Integrity: API calls (`/api/v1/*`) must never be intercepted or shadowed by the SPA fallback route.
4. Binary Portability: `cloudflared.exe` must be located or cleanly downloaded into `.tools/` if not found in PATH.
5. DuckDNS Error Handling: The sync script must gracefully handle network downtime or invalid tokens without crashing.

---

### Task 1: Unified Static Asset & HTML SPA Mounting in FastAPI

**Files:**
- Modify: `src/live_score/api/app.py`
- Create: `tests/live_score/test_unified_spa.py`

- [x] **Step 1: Write failing test for SPA and static asset serving in test_unified_spa.py**
  - Verify `GET /` returns HTML content from `frontend/dist/index.html`.
  - Verify `GET /admin` returns HTML content for SPA client routing.
  - Verify `GET /api/v1/matches/today` still returns JSON (not intercepted by SPA).
- [x] **Step 2: Run test to confirm failure**
  - `pytest tests/live_score/test_unified_spa.py`
- [x] **Step 3: Implement static asset mounting and SPA fallback in app.py**
  - Mount `/assets` to `frontend/dist/assets` if directory exists.
  - Add catch-all route for non-API GET requests returning `FileResponse("frontend/dist/index.html")`.
- [x] **Step 4: Run test to verify it passes**
  - `pytest tests/live_score/test_unified_spa.py`

---

### Task 2: DuckDNS IP Auto-Sync Script

**Files:**
- Create: `scripts/duckdns_sync.py`
- Create: `tests/live_score/test_duckdns_sync.py`

- [x] **Step 1: Write failing unit test for DuckDNS updater**
  - Mock HTTP response from `https://www.duckdns.org/update` and verify URL parameters (domain, token).
  - Verify success parsing ("OK") and failure handling ("KO").
- [x] **Step 2: Run test to confirm failure**
  - `pytest tests/live_score/test_duckdns_sync.py`
- [x] **Step 3: Implement DuckDNS updater in scripts/duckdns_sync.py**
  - Provide `update_duckdns(domain, token, ip=None)` function.
  - Provide CLI entrypoint with `--domain`, `--token`, and `--interval` (for recurring daemon updates).
- [x] **Step 4: Run test to verify it passes**
  - `pytest tests/live_score/test_duckdns_sync.py`

---

### Task 3: Cloudflared Tunnel Automated Launcher Script

**Files:**
- Create: `scripts/start_tunnel.py`

- [x] **Step 1: Implement scripts/start_tunnel.py**
  - Checks if `cloudflared.exe` exists in PATH or `.tools/cloudflared.exe`.
  - If missing, downloads official Windows 64-bit binary from Cloudflare GitHub releases (`https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe`) into `.tools/cloudflared.exe`.
  - Spawns `cloudflared tunnel --url http://127.0.0.1:8000`.
  - Parses stderr/stdout in real time to capture the generated `https://*.trycloudflare.com` URL.
  - Prints clear banner with the public HTTPS URL for the user.

---

### Task 4: Full Test Suite Verification & Public Live Launch

**Files:**
- All files

- [x] **Step 1: Run full Pytest test suite**
  - `pytest`
- [x] **Step 2: Run full Vitest test suite**
  - `npm test -- --run`
- [x] **Step 3: Run full live end-to-end integration test**
  - `python scripts/full_live_test.py`
- [x] **Step 4: Restart unified server and start tunnel to verify live public URL**
