# Task 4 Brief: Serverless GitHub Actions Cron Workflow

**Working Directory:** `C:\Users\Mohany\Desktop\football-live-score-platform`
**Python Venv:** `C:\Users\Mohany\Desktop\football-live-score-platform\.venv\Scripts\python.exe`

## Goal
Create `.github/workflows/sync_and_publish.yml` and unit tests in `tests/test_github_workflow_syntax.py` that configure a 24/7 automated pipeline running every 20 minutes to scrape matches, export static streams, publish to Blogger, auto-commit updated data, and build/deploy the frontend.

## Files to Create
- `.github/workflows/sync_and_publish.yml`
- `tests/test_github_workflow_syntax.py`

## Detailed Requirements
1. **`.github/workflows/sync_and_publish.yml`**:
   - Triggers:
     - `schedule: - cron: "*/20 * * * *"`
     - `workflow_dispatch:`
     - `push: branches: [main, master]`
   - Permissions: `contents: write`
   - Job: `sync-and-publish` on `ubuntu-latest`:
     - Checks out repository (`actions/checkout@v4`).
     - Sets up Python 3.12 (`actions/setup-python@v5`).
     - Installs dependencies from `requirements.txt`.
     - Runs `python scripts/export_static_streams.py`.
     - Runs `python scripts/auto_blogger_publisher.py` with environment secrets (`BLOGGER_BLOG_ID`, `BLOGGER_CLIENT_SECRETS`, `BLOGGER_ACCESS_TOKEN`, `SMTP_USER`, `SMTP_PASSWORD`, `BLOGGER_PUBLISH_EMAIL`).
     - Commits and pushes changes to `frontend/public/data/matches.json`, `data/matches.json`, and `data/published_articles.json` with `[skip ci]`.
     - Sets up Node 22 (`actions/setup-node@v4`).
     - Installs frontend packages and builds: `cd frontend && npm ci && npm run build`.
     - Deploys to Cloudflare Pages (with `cloudflare/pages-action@v1` if configured) or prepares deployment artifact.
2. **`tests/test_github_workflow_syntax.py`**:
   - Parses `.github/workflows/sync_and_publish.yml` using `yaml` or basic parser.
   - Verifies cron schedule `"*/20 * * * *"`.
   - Verifies presence of key steps: `export_static_streams.py`, `auto_blogger_publisher.py`, `npm run build`.
   - Run tests: `.\.venv\Scripts\python.exe -m pytest tests/test_github_workflow_syntax.py` (Must PASS).
   - Run full suite: `.\.venv\Scripts\python.exe -m pytest` (Must PASS).
