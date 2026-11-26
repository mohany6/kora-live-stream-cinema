# High-Concurrency & Security Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the football live score platform into a production-grade, hardened service capable of sustaining 10,000 concurrent online users (500+ requests/second) without server degradation, with comprehensive defense against DoS, brute force, and memory exhaustion attacks, plus clean admin navigation and video player embedding.

**Architecture:** A multi-layered high-performance architecture featuring in-memory micro-caching (5-10s TTL) with HTTP 304 ETag short-circuiting to serve 95%+ of read traffic in sub-millisecond time. SQLite concurrency bottlenecks are resolved via WAL mode and an asynchronous write-behind batch queue for telemetry. A sliding-window token bucket rate limiter protects endpoints from abuse, while security headers and payload size guards prevent memory exhaustion and web attacks.

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn (multi-worker), SQLite (WAL mode, async batch buffer), React 18, Tailwind CSS, Vite.

**Spec:** `docs/superpowers/specs/2026-11-21-high-concurrency-and-security-hardening-design.md`

## Global Constraints

- Zero external daemon dependencies: Must run completely in Python/FastAPI and SQLite without requiring Redis, Memcached, or external message brokers.
- Concurrency target: Must handle 500+ requests/sec with average response latency < 50ms for cached responses.
- Memory budget: In-memory cache and rate limiter must have strict size bounds (bounded dicts with TTL cleanup) to avoid memory leaks.
- Zero emojis in UI / code components (clean SVG iconography only).
- Arabic RTL-first layout must be strictly preserved across all views.
- 100% passing test suite: All existing 113 Pytest, 41 Vitest, and 43 Live integration tests must remain passing with zero regressions.

## Review Focus

1. High Concurrency Polling (10k users requesting `/api/v1/matches/today` simultaneously): Micro-cache must return identical content with ETag; subsequent requests with `If-None-Match` must return `304 Not Modified` with 0-byte payload.
2. Burst Analytics Floods (hundreds of visitor tracking calls per second): The async telemetry queue must buffer entries without locking SQLite, flushing in atomic batches.
3. Rapid Route Mutations: When an admin updates a match or creates/toggles an ad, the micro-cache must immediately invalidate stale keys.
4. IP Rate Limiting Under NAT/Proxies: The limiter must correctly parse `X-Forwarded-For` while preventing spoofing, locking out brute-force attackers after 5 failed admin authentication attempts.
5. Direct `/admin` URL access: Visiting `http://localhost:5173/admin` must directly mount the Cockpit Admin Panel and clear any active match view.

---

### Task 1: Frontend Route Resolution & Video Player Centering Fix

**Files:**
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/components/StreamPlayerContainer.jsx`
- Test: `frontend/src/components/__tests__/StreamPlayerContainer.test.jsx`

- [x] **Step 1: Write unit tests for /admin direct URL loading and stream cleaning**
- [x] **Step 2: Update App.jsx to handle /admin direct URL and clear match selection**
- [x] **Step 3: Refine StreamPlayerContainer.jsx for centering and sandbox compatibility**
- [x] **Step 4: Run Vitest to verify all frontend tests pass** (41 / 41 passing)

---

### Task 2: SQLite WAL Mode & Asynchronous Batch Telemetry Buffer

**Files:**
- Modify: `src/live_score/api/store.py`
- Create: `tests/live_score/test_batch_telemetry.py`

- [x] **Step 1: Write failing test for batch telemetry queue and WAL pragma in test_batch_telemetry.py**
- [x] **Step 2: Run test to confirm failure**
- [x] **Step 3: Implement WAL initialization and async batch flush worker in store.py**
- [x] **Step 4: Run test to verify it passes** (2 / 2 passing)

---

### Task 3: In-Memory Micro-Cache & HTTP 304 ETag Middleware

**Files:**
- Create: `src/live_score/api/cache.py`
- Modify: `src/live_score/api/main.py`
- Modify: `src/live_score/api/public_routes.py`
- Modify: `src/live_score/api/admin_routes.py`
- Create: `tests/live_score/test_micro_cache.py`

- [x] **Step 1: Write failing test for MicroCache and ETag generation in test_micro_cache.py**
- [x] **Step 2: Run test to confirm failure**
- [x] **Step 3: Implement MicroCache class in src/live_score/api/cache.py**
- [x] **Step 4: Hook cache into public match and ad endpoints**
- [x] **Step 5: Run test to verify it passes** (3 / 3 passing)

---

### Task 4: Sliding-Window Rate Limiting & Admin Brute Force Jail

**Files:**
- Create: `src/live_score/api/security.py`
- Modify: `src/live_score/api/main.py`
- Create: `tests/live_score/test_rate_limiter.py`

- [x] **Step 1: Write failing test for rate limiting and IP lockout in test_rate_limiter.py**
- [x] **Step 2: Run test to confirm failure**
- [x] **Step 3: Implement SlidingWindowRateLimiter in src/live_score/api/security.py**
- [x] **Step 4: Run test to verify it passes** (3 / 3 passing)

---

### Task 5: Security Headers & Request Body Size Guard

**Files:**
- Modify: `src/live_score/api/security.py`
- Modify: `src/live_score/api/main.py`
- Create: `tests/live_score/test_security_headers.py`

- [x] **Step 1: Write failing test for security headers and payload size rejection**
- [x] **Step 2: Run test to confirm failure**
- [x] **Step 3: Implement SecurityHeadersMiddleware and RequestSizeLimiterMiddleware**
- [x] **Step 4: Run test to verify it passes** (2 / 2 passing)

---

### Task 6: Multi-Worker Production Runner & Comprehensive E2E Verification

**Files:**
- Create: `scripts/start_production.py`
- Modify: `scripts/full_live_test.py`

- [x] **Step 1: Create scripts/start_production.py**
- [x] **Step 2: Extend scripts/full_live_test.py with rate-limiting, ETag, security headers, and size guard tests** (48 / 48 passing)
- [x] **Step 3: Build frontend assets and run full test suites**
  - All 123 Pytest passing.
  - All 41 Vitest passing.
  - All 48 Live E2E tests passing.
