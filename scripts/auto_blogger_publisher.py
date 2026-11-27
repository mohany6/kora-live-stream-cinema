# -*- coding: utf-8 -*-
"""Automated Daily Top 3-5 Trending Match Article Publisher for Blogger."""

from __future__ import annotations

import json
import os
import re
import sys
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import requests

# Ensure src and root are on sys.path
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from live_score.api.fixtures import create_catalog, load_fixtures
from live_score.domain.article_generator import generate_blogger_article
from scripts.extract_tunnel_url import copy_to_clipboard

MAX_DAILY_MATCHES = 5
PUBLISHED_CACHE_PATH = ROOT / "data" / "published_articles.json"

# League prestige scores for automated trend detection
LEAGUE_WEIGHTS = {
    "دوري أبطال أوروبا": 100,
    "الدوري الإنجليزي": 90,
    "الدوري الإسباني": 85,
    "دوري روشن السعودي": 80,
    "الدوري الإيطالي": 75,
    "الدوري الألماني": 70,
    "الدوري الفرنسي": 65,
    "الدوري المصري": 60,
    "كأس الملك": 55,
}

TOP_CLUBS = {
    "ريال مدريد", "برشلونة", "مانشستر سيتي", "ليفربول", "أرسنال",
    "مانشستر يونايتد", "بايرن ميونخ", "بوروسيا دورتموند", "نابولي",
    "باريس سان جيرمان", "الهلال", "النصر", "الاتحاد", "الأهلي",
    "الزمالك", "إنتر ميلان", "يوفنتوس", "أتلتيكو مدريد", "تشيلسي",
    "أستون فيلا", "غلطة سراي",
}

_LIVE_STATUSES = {"IN_PLAY", "HALFTIME", "EXTRA_TIME", "PENALTIES"}


def _extract_utc_date(kickoff: Any) -> str:
    """Extract YYYY-MM-DD in UTC from a datetime or ISO string."""
    if isinstance(kickoff, datetime):
        dt = kickoff if kickoff.tzinfo else kickoff.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
    if isinstance(kickoff, str) and kickoff.strip():
        clean = kickoff.strip()
        try:
            dt = datetime.fromisoformat(clean.replace("Z", "+00:00"))
            dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
        except ValueError:
            return clean[:10]
    return ""


def _status_value(match_obj: Any) -> str:
    raw = getattr(match_obj, "status", None)
    if hasattr(raw, "value"):
        return str(raw.value)
    return str(raw or "SCHEDULED")


def score_match_trend(match_obj: Any, target_date_str: str) -> int:
    """Calculate trending score strictly for today's active, upcoming, or finished matches."""
    kickoff = getattr(match_obj, "kickoff_time", None)
    if _extract_utc_date(kickoff) != target_date_str:
        return -9999  # Strictly discard past or future matches

    status_val = _status_value(match_obj)
    if status_val == "POSTPONED":
        return -9999

    score = 10
    if status_val in _LIVE_STATUSES:
        score += 200  # Highest priority: live right now
    elif status_val == "SCHEDULED":
        score += 50   # Upcoming today (pre-match preview)
    elif status_val == "FINISHED":
        score += 40   # Finished today (eligible for post-match highlights)

    league = getattr(match_obj, "league", None)
    league_name = (
        getattr(league, "name_ar", None) or getattr(league, "name_en", None) or ""
        if league is not None
        else ""
    )
    for key, weight in LEAGUE_WEIGHTS.items():
        if key in league_name:
            score += weight
            break

    home_team = getattr(match_obj, "home_team", None)
    away_team = getattr(match_obj, "away_team", None)
    home = (
        getattr(home_team, "name_ar", None) or getattr(home_team, "name_en", None) or ""
        if home_team is not None
        else ""
    )
    away = (
        getattr(away_team, "name_ar", None) or getattr(away_team, "name_en", None) or ""
        if away_team is not None
        else ""
    )

    for club in TOP_CLUBS:
        if club in home:
            score += 60
        if club in away:
            score += 60

    if getattr(match_obj, "has_stream", False) or getattr(match_obj, "stream_servers", None):
        score += 30

    return score


def _dump_items(items: Any) -> list[Any]:
    if not items:
        return []
    out: list[Any] = []
    for item in items:
        if hasattr(item, "model_dump"):
            out.append(item.model_dump())
        else:
            out.append(item)
    return out


def _serialize_match_detail(detail: Any, score: int, fallback_now: datetime) -> dict[str, Any]:
    m = detail.match if hasattr(detail, "match") else detail
    status_val = _status_value(m)
    stage = "post_match" if status_val == "FINISHED" else "pre_match"
    kickoff = getattr(m, "kickoff_time", None)
    kickoff_iso = kickoff.isoformat() if hasattr(kickoff, "isoformat") else fallback_now.isoformat()

    return {
        "id": str(m.id),
        "home_team": m.home_team.name_ar or m.home_team.name_en,
        "away_team": m.away_team.name_ar or m.away_team.name_en,
        "home_team_en": m.home_team.name_en,
        "away_team_en": m.away_team.name_en,
        "home_team_id": getattr(m.home_team, "id", None),
        "away_team_id": getattr(m.away_team, "id", None),
        "home_logo": getattr(m.home_team, "logo_url", None),
        "away_logo": getattr(m.away_team, "logo_url", None),
        "competition": m.league.name_ar or m.league.name_en,
        "league_logo": getattr(m.league, "logo_url", None),
        "kickoff_time": kickoff_iso,
        "status": status_val,
        "stage": stage,
        "home_score": getattr(m, "home_score", 0) or 0,
        "away_score": getattr(m, "away_score", 0) or 0,
        "channel": getattr(m, "channel", None) or "beIN SPORTS 1 HD",
        "commentator": getattr(m, "commentator", None) or "يحدد لاحقاً",
        "venue": getattr(m, "stadium", None) or getattr(m, "venue", None) or "ملعب اللقاء",
        "referee": getattr(m, "referee", None) or "طاقم التحكيم الرسمي",
        "events": _dump_items(getattr(detail, "events", None)),
        "home_lineup": _dump_items(getattr(detail, "home_lineup", None)),
        "away_lineup": _dump_items(getattr(detail, "away_lineup", None)),
        "home_formation": getattr(detail, "home_formation", None),
        "away_formation": getattr(detail, "away_formation", None),
        "stats": getattr(detail, "stats", None),
        "standings": getattr(detail, "standings", None) or [],
        "highlight_embed_url": getattr(m, "highlight_embed_url", None) or getattr(detail, "highlight_embed_url", None),
        "score": score,
    }


def get_top_trending_matches(
    limit: int = MAX_DAILY_MATCHES,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Fetch today's fixtures and strictly select up to top 5 highest-ranking matches."""
    capped_limit = max(0, min(int(limit), MAX_DAILY_MATCHES))
    if capped_limit == 0:
        return []

    current_now = now or datetime.now(timezone.utc)
    if current_now.tzinfo is None:
        current_now = current_now.replace(tzinfo=timezone.utc)
    target_date_str = current_now.astimezone(timezone.utc).strftime("%Y-%m-%d")

    cat = create_catalog(current_now)
    if cat is not None:
        fixture_map = cat.fixture_map(current_now)
    else:
        fixture_map = {d.match.id: d for d in load_fixtures(current_now)}

    if not fixture_map:
        return []

    ranked: list[tuple[int, str, Any]] = []
    for match_id, detail in fixture_map.items():
        m = detail.match if hasattr(detail, "match") else detail
        rank_score = score_match_trend(m, target_date_str)
        if rank_score > 0:
            ranked.append((rank_score, str(match_id), detail))

    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)

    results: list[dict[str, Any]] = []
    for score, match_id, detail in ranked[:capped_limit]:
        resolved_detail = detail
        if cat is not None and hasattr(cat, "get_detail"):
            try:
                hydrated = cat.get_detail(match_id, current_now)
                if hydrated is not None:
                    resolved_detail = hydrated
            except Exception:
                pass
        results.append(_serialize_match_detail(resolved_detail, score, current_now))

    return results


# ---------------------------------------------------------------------------
# Deduplication & Daily Rate-Limit Cache (`data/published_articles.json`)
# ---------------------------------------------------------------------------

def article_cache_key(match_id: str, stage: str) -> str:
    """Return canonical deduplication key for a (match_id, stage) pair."""
    return f"{match_id}:{stage}"


def load_published_articles(cache_path: Path = PUBLISHED_CACHE_PATH) -> dict[str, Any]:
    """Load published article cache safely, returning empty structure if absent/corrupt."""
    if not cache_path.exists():
        return {"articles": {}}
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("articles"), dict):
            return data
    except (OSError, ValueError, TypeError):
        pass
    return {"articles": {}}


def save_published_articles(
    cache_data: Mapping[str, Any],
    cache_path: Path = PUBLISHED_CACHE_PATH,
) -> None:
    """Persist published article cache atomically as UTF-8 JSON."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = cache_path.with_name(cache_path.name + ".tmp")
    temp_path.write_text(
        json.dumps(cache_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temp_path, cache_path)


def is_article_published(
    cache_data: Mapping[str, Any],
    match_id: str,
    stage: str,
) -> bool:
    """Return True if the exact (match_id, stage) article was already published."""
    articles = cache_data.get("articles")
    if not isinstance(articles, Mapping):
        return False
    return article_cache_key(str(match_id), stage) in articles


def published_match_ids_for_date(
    cache_data: Mapping[str, Any],
    date_str: str,
) -> set[str]:
    """Return distinct match IDs already published on ``date_str``."""
    articles = cache_data.get("articles")
    if not isinstance(articles, Mapping):
        return set()
    return {
        str(entry["match_id"])
        for entry in articles.values()
        if isinstance(entry, Mapping)
        and entry.get("date") == date_str
        and entry.get("match_id")
    }


def record_published_article(
    cache_data: dict[str, Any],
    *,
    match_id: str,
    stage: str,
    date_str: str,
    title: str,
    labels: list[str] | None = None,
    method: str = "email",
    post_url: str | None = None,
) -> dict[str, Any]:
    """Record a published article entry in ``cache_data`` in place."""
    articles = cache_data.setdefault("articles", {})
    key = article_cache_key(str(match_id), stage)
    entry: dict[str, Any] = {
        "match_id": str(match_id),
        "stage": stage,
        "date": date_str,
        "title": title,
        "labels": list(labels or []),
        "method": method,
        "published_at": datetime.now(timezone.utc).isoformat(),
    }
    if post_url:
        entry["url"] = post_url
    articles[key] = entry
    return cache_data


def load_env_vars() -> dict[str, str]:
    """Load key-value pairs from .env if present."""
    env_file = ROOT / ".env"
    env_vars: dict[str, str] = {}
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env_vars[k.strip()] = v.strip()
    return env_vars


def _get_setting(key: str, env_vars: Mapping[str, str]) -> str:
    return (os.environ.get(key) or env_vars.get(key) or "").strip()


def _resolve_blogger_access_token(env_vars: Mapping[str, str]) -> str | None:
    """Resolve a Blogger OAuth2 Bearer token from env/secrets if configured."""
    direct_token = _get_setting("BLOGGER_ACCESS_TOKEN", env_vars)
    if direct_token:
        return direct_token

    raw_secrets = _get_setting("BLOGGER_CLIENT_SECRETS", env_vars)
    refresh_token = _get_setting("BLOGGER_REFRESH_TOKEN", env_vars)
    if not raw_secrets:
        return None

    try:
        parsed = json.loads(raw_secrets)
    except ValueError:
        return None

    creds_block = parsed.get("installed") or parsed.get("web") or parsed
    client_id = creds_block.get("client_id")
    client_secret = creds_block.get("client_secret")
    refresh = refresh_token or parsed.get("refresh_token") or creds_block.get("refresh_token")
    if client_id and client_secret and refresh:
        try:
            resp = requests.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh,
                    "grant_type": "refresh_token",
                },
                timeout=15,
            )
            resp.raise_for_status()
            access_token = resp.json().get("access_token")
            if access_token:
                return access_token
        except Exception as exc:
            print(f"  [-] تعذر تجديد رمز Blogger OAuth: {exc}")

    if isinstance(parsed, dict) and parsed.get("token"):
        return str(parsed["token"])

    return None


def publish_article_via_blogger_api(
    title: str,
    html_content: str,
    labels: list[str] | None = None,
    out_meta: dict[str, Any] | None = None,
) -> bool | None:
    """Publish directly via Blogger REST API v3 if credentials are configured.

    Returns ``None`` if Blogger API credentials are not configured, ``True`` on
    publish success, and ``False`` on delivery failure.
    """
    env_vars = load_env_vars()
    blog_id = _get_setting("BLOGGER_BLOG_ID", env_vars)
    if not blog_id:
        return None

    token = _resolve_blogger_access_token(env_vars)
    if not token:
        return None

    endpoint = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts/"
    payload = {
        "kind": "blogger#post",
        "blog": {"id": blog_id},
        "title": title,
        "content": html_content,
        "labels": list(labels or []),
    }
    try:
        resp = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=20,
        )
        resp.raise_for_status()
        if out_meta is not None:
            try:
                body = resp.json()
                if isinstance(body, dict) and body.get("url"):
                    out_meta["url"] = str(body["url"])
            except Exception:
                pass
        print("  [🎉] تم النشر عبر Blogger API v3 بنجاح!")
        return True
    except Exception as exc:
        print(f"  [-] تعذر النشر عبر Blogger API v3: {exc}")
        return False


def _email_is_configured(env_vars: Mapping[str, str]) -> bool:
    return bool(
        _get_setting("SMTP_USER", env_vars)
        and _get_setting("SMTP_PASSWORD", env_vars)
        and _get_setting("BLOGGER_PUBLISH_EMAIL", env_vars)
    )


def publish_article_via_email(title: str, html_content: str) -> bool:
    """Send generated article to Blogger via Mail-to-Blogger secret email address."""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    env_vars = load_env_vars()
    smtp_user = _get_setting("SMTP_USER", env_vars)
    smtp_pwd = _get_setting("SMTP_PASSWORD", env_vars)
    to_email = _get_setting("BLOGGER_PUBLISH_EMAIL", env_vars)
    smtp_host = _get_setting("SMTP_HOST", env_vars) or "smtp.gmail.com"
    smtp_port = int(_get_setting("SMTP_PORT", env_vars) or 587)

    if not (smtp_user and smtp_pwd and to_email):
        return False

    print(f"\n[*] جاري إرسال ونشر المقال تلقائياً إلى بلوجر ({to_email})...")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = title
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_pwd)
            server.sendmail(smtp_user, [to_email], msg.as_string())
        print("  [🎉] تم النشر في مدونة بلوجر تلقائياً بنجاح بنسبة 100%!")
        return True
    except Exception as e:
        print(f"  [-] تعذر النشر التلقائي عبر البريد: {e}")
        return False


def _resolve_platform_base_url(explicit_url: str | None, env_vars: Mapping[str, str]) -> str:
    if explicit_url is not None:
        return explicit_url.strip()
    from_env = _get_setting("STREAM_PLATFORM_URL", env_vars)
    if from_env:
        return from_env
    tunnel_file = ROOT / "data" / "tunnel_url.txt"
    if tunnel_file.exists():
        try:
            return tunnel_file.read_text(encoding="utf-8").strip()
        except OSError:
            pass
    return ""


def _should_open_browser(explicit: bool | None) -> bool:
    if explicit is not None:
        return explicit
    return not (
        os.environ.get("CI")
        or os.environ.get("GITHUB_ACTIONS")
        or os.environ.get("PYTEST_CURRENT_TEST")
    )


def run_auto_publisher(
    *,
    limit: int = MAX_DAILY_MATCHES,
    cache_path: Path = PUBLISHED_CACHE_PATH,
    output_dir: Path | None = None,
    platform_base_url: str | None = None,
    now: datetime | None = None,
    open_browser: bool | None = None,
    record_unconfigured: bool = False,
) -> list[dict[str, Any]]:
    """Find today's top 3-5 trending matches, deduplicate, generate & publish articles."""
    print("=" * 65)
    print("  ⚽ محرك كورة لايف التلقائي لكشف ونشر أكثر المباريات طلباً (Trend) ⚽")
    print("=" * 65)

    current_now = now or datetime.now(timezone.utc)
    if current_now.tzinfo is None:
        current_now = current_now.replace(tzinfo=timezone.utc)
    today_str = current_now.astimezone(timezone.utc).strftime("%Y-%m-%d")

    capped_limit = max(1, min(int(limit), MAX_DAILY_MATCHES))
    print(f"[*] جاري فحص جدول مباريات اليوم ({today_str}) بحد أقصى {capped_limit} مباريات...")
    trending = get_top_trending_matches(limit=capped_limit, now=current_now)

    if not trending:
        print("[-] لم يتم العثور على مباريات مجدولة اليوم في المصدر المباشر.")
        return []

    env_vars = load_env_vars()
    resolved_base_url = _resolve_platform_base_url(platform_base_url, env_vars)
    out_dir = output_dir or (ROOT / "data" / "daily_articles")
    out_dir.mkdir(parents=True, exist_ok=True)

    cache_data = load_published_articles(cache_path)
    published_today_ids = published_match_ids_for_date(cache_data, today_str)
    processed: list[dict[str, Any]] = []
    first_unpublished_article: dict[str, Any] | None = None
    first_unpublished_file: Path | None = None

    for match in trending:
        match_id = str(match["id"])
        stage = match.get("stage") or (
            "post_match" if match.get("status") == "FINISHED" else "pre_match"
        )

        if is_article_published(cache_data, match_id, stage):
            print(f"  [SKIP] تم نشر مقال ({stage}) مسبقاً للمباراة {match_id}.")
            continue

        if match_id not in published_today_ids and len(published_today_ids) >= MAX_DAILY_MATCHES:
            print(f"  [CAP] تم بلوغ الحد الأقصى اليومي ({MAX_DAILY_MATCHES} مباريات).")
            break

        print(f"\n[🔥] معالجة مواجهة: {match['home_team']} ضد {match['away_team']} [{stage}]")
        article = generate_blogger_article(
            match,
            platform_base_url=resolved_base_url,
            stage=stage,
        )

        safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(match_id))
        out_file = out_dir / f"{today_str}_{safe_id}_{stage}.html"
        out_file.write_text(article["content"], encoding="utf-8")

        api_meta: dict[str, Any] = {}
        api_result = publish_article_via_blogger_api(
            article["title"],
            article["content"],
            labels=article.get("labels"),
            out_meta=api_meta,
        )
        method = ""
        published = False

        if api_result is True:
            published = True
            method = "blogger_api"
        elif api_result is None:
            if _email_is_configured(env_vars):
                if publish_article_via_email(article["title"], article["content"]):
                    published = True
                    method = "email"
            elif record_unconfigured:
                published = True
                method = "local_archive"
        elif api_result is False and record_unconfigured:
            published = True
            method = "local_archive"

        if published:
            record_published_article(
                cache_data,
                match_id=match_id,
                stage=stage,
                date_str=today_str,
                title=article["title"],
                labels=article.get("labels"),
                method=method,
                post_url=api_meta.get("url"),
            )
            published_today_ids.add(match_id)
            save_published_articles(cache_data, cache_path)
            print(f"  [✓] نُشر وحُفظ في السجل: {article['title']}")
        else:
            if first_unpublished_article is None:
                first_unpublished_article = article
                first_unpublished_file = out_file

        processed.append(
            {
                "match_id": match_id,
                "stage": stage,
                "title": article["title"],
                "labels": article.get("labels", []),
                "output_file": str(out_file),
                "published": published,
                "method": method or "archive_only",
            }
        )

    if first_unpublished_article is not None and first_unpublished_file is not None:
        if _should_open_browser(open_browser):
            copied = copy_to_clipboard(first_unpublished_article["content"])
            print(f"\n📌 عنوان المقال: {first_unpublished_article['title']}")
            print(f"📁 المسار: {first_unpublished_file}")
            if copied:
                print("📋 تم نسخ كود HTML للمقال إلى الحافظة!")
            try:
                webbrowser.open("https://www.blogger.com/go/create-post")
            except Exception:
                pass

    return processed


if __name__ == "__main__":
    run_auto_publisher()
