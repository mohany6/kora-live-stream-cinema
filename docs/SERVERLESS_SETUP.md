# 🚀 Serverless Deployment & 24/7 Automation Setup Guide

This guide walks you through deploying the **Kora Live Stream Cinema & Blogger Hub** on 100% free cloud infrastructure without needing any server running or personal computer kept online.

---

## 🏗️ Architecture Overview

The platform uses a decoupled, high-performance serverless architecture:

```
                  ┌────────────────────────────────────────────────────────┐
                  │                 GitHub Actions Cron                    │
                  │             (Runs every 20 minutes 24/7)                │
                  └───────────────┬────────────────────────┬───────────────┘
                                  │                        │
               [Export Static Streams]          [Publish Top 3-5 Articles]
                                  │                        │
                                  ▼                        ▼
     ┌──────────────────────────────────────┐    ┌──────────────────────────────────┐
     │      Cloudflare Pages (Vite SPA)     │    │   Blogger Hub (Adsterra Monetized)
     │       Pure Match Stream Cinema       │    │    https://kora-live-to.blogspot.com │
     │  - Responsive Stream Embeds          │    │  - Top 3-5 Trending Matches / Day│
     │  - Multi-Server & Direct HLS (.m3u8) │    │  - 800+ Word Tactical Analysis   │
     │  - VIP 4K Server Smartlink CTA       │    │  - 16:9 Video Highlight Embeds   │
     │  - Loopback Button to Blogger Hub    │    │  - Interactive POTM Fan Poll     │
     └──────────────────────────────────────┘    └──────────────────────────────────┘
```

- **Cost:** $0.00 / month forever.
- **Maintenance:** Zero server patching, no sleeping dynos, no persistent PC.
- **Traffic Scaling:** Cloudflare Pages global CDN handles unlimited viewers effortlessly.

---

## 📋 Step 1: Push Repository to GitHub (Public)

GitHub offers **unlimited free GitHub Actions minutes** for public repositories.

1. Create a new **Public** repository on [GitHub](https://github.com/new).
2. Push your codebase:
   ```bash
   cd C:\Users\Mohany\Desktop\football-live-score-platform
   git init
   git add .
   git commit -m "feat: complete serverless blogger and stream cinema architecture"
   git branch -M main
   git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/<YOUR_REPOSITORY_NAME>.git
   git push -u origin main
   ```

---

## 🔑 Step 2: Configure GitHub Secrets

Go to your GitHub repository:
**Settings** ➔ **Secrets and variables** ➔ **Actions** ➔ **New repository secret**.

Add the following repository secrets:

### 1. Blogger Secrets (Automated Article Publishing)
| Secret Name | Description | Example / Notes |
|---|---|---|
| `BLOGGER_BLOG_ID` | Numeric Blog ID for `kora-live-to.blogspot.com` | Found in Blogger URL: `blogID=XXXXXXXXXXXXXXXX` |
| `BLOGGER_REFRESH_TOKEN` | OAuth2 Refresh Token for Google Blogger API v3 | Long-lived refresh token |
| `BLOGGER_CLIENT_SECRETS` | *(Optional)* Google OAuth Client JSON | Contents of client secrets file |
| `BLOGGER_ACCESS_TOKEN` | *(Optional)* Short-lived Bearer token | Used if refresh token is omitted |
| `SMTP_USER` | *(Optional Fallback)* Gmail address | For posting by email fallback |
| `SMTP_PASSWORD` | *(Optional Fallback)* Google App Password | 16-character App Password |
| `BLOGGER_PUBLISH_EMAIL` | *(Optional Fallback)* Secret Blogger email | Configured in Blogger Settings |

### 2. Cloudflare Pages Secrets (Automated SPA Deployment)
| Secret Name | Description | Example / Notes |
|---|---|---|
| `CLOUDFLARE_API_TOKEN` | Cloudflare API Token with `Pages: Edit` permission | Create in Cloudflare Dashboard ➔ My Profile ➔ API Tokens |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare Account ID | Visible in your Cloudflare dashboard URL or sidebar |
| `CLOUDFLARE_PROJECT_NAME` | Project name in Cloudflare Pages | `kora-stream-cinema` (default if omitted) |

### 3. Stream Platform & Ad Configuration
| Secret Name | Description | Default / Value |
|---|---|---|
| `STREAM_PLATFORM_URL` | Public URL of your Cloudflare Pages streaming site | e.g., `https://kora-stream-cinema.pages.dev` |
| `LIVE_SCORE_API_URL` | *(Optional)* Custom backend live score API | Defaults to standard live scraper |
| `LIVE_SCORE_SCRAPER_URL`| *(Optional)* Scraper override URL | Live match source |
| `LIVE_SCORE_LEAGUES` | *(Optional)* Priority league IDs | e.g., `champions_league,premier_league,la_liga` |

---

## ⚡ Step 3: Deploying Cloudflare Pages

You have two simple options to host the streaming frontend on Cloudflare Pages:

### Option A: Automatic via GitHub Actions (Recommended)
Once you set `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` in your GitHub secrets:
1. Every run of the GitHub Actions workflow will automatically build `frontend` and deploy `frontend/dist` to Cloudflare Pages.
2. The site will immediately be live at `https://<CLOUDFLARE_PROJECT_NAME>.pages.dev`.

### Option B: Cloudflare Dashboard Git Integration
If you prefer Cloudflare to build directly from GitHub:
1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com/) ➔ **Workers & Pages** ➔ **Create application** ➔ **Pages** ➔ **Connect to Git**.
2. Select your repository.
3. Configure build settings:
   - **Framework preset:** `Vite`
   - **Root directory:** `frontend`
   - **Build command:** `npm run build`
   - **Build output directory:** `dist`
4. Click **Save and Deploy**.

---

## 🌐 Step 4: Monetization & Traffic Loop Verification

The system is configured to maximize your Adsterra revenue safely:

1. **Blogger Revenue Hub (`https://kora-live-to.blogspot.com`):**
   - Adsterra Account ID: `6226474`.
   - Adsterra script units, banners, and native formats stay on Blogger where domain approval is active.
   - High dwell time strategy: Articles include 800+ word tactical previews, verified 16:9 highlight videos, visual event timelines, and interactive polls.
   - Direct Call-to-Action buttons lead viewers to your Cloudflare Stream Cinema for live matches.

2. **Stream Cinema (`https://kora-stream-cinema.pages.dev`):**
   - High-performance, ad-free player container (no ad network flags on Cloudflare).
   - Prominent **VIP 4K Server** Smartlink button:
     `https://budgetezy.org/4/ae626546295ba9dbdec2ea24a521084c`
   - Floating header/footer loopback button: `🌐 عودة إلى كورة لايف (الأخبار وملخصات الأهداف)` returning traffic back to Blogger.

---

## ⚙️ Step 5: Testing & Triggering the Cron Workflow

1. Navigate to your repository on GitHub.
2. Click the **Actions** tab.
3. In the left sidebar, click **Sync Matches, Publish to Blogger & Deploy Stream Cinema**.
4. Click **Run workflow** ➔ select branch `main` ➔ click **Run workflow**.
5. The workflow will:
   - Scrape today's live matches and generate `frontend/public/data/matches.json`.
   - Analyze trending matches, publish the top 3-5 articles to Blogger, and update `data/published_articles.json`.
   - Commit and push any updated data files back to the repository with `[skip ci]`.
   - Build the React 18 SPA and deploy to Cloudflare Pages.

---

## 🛠️ Local Development & Manual Runs

To run the sync and publishing scripts manually on your local machine:

```powershell
# 1. Activate Python virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Export static match streams
python scripts/export_static_streams.py

# 3. Publish trending matches to Blogger
python scripts/auto_blogger_publisher.py

# 4. Run frontend locally
Set-Location frontend
npm run dev
```
