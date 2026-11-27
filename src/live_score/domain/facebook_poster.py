# -*- coding: utf-8 -*-
"""Cyber-Stadium 1200x1200 HTML-to-PNG poster generator via Headless Chrome/Edge."""

from __future__ import annotations

import html
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.live_score.domain.facebook_caption import (
    format_arabic_date_label,
    format_cairo_mecca_times,
)

FALLBACK_LOGO_URL = "https://cdn-icons-png.flaticon.com/512/53/53283.png"

_BROWSER_CANDIDATES = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "google-chrome",
    "chromium",
    "chromium-browser",
    "msedge",
)

_BASE_POSTER_CSS = """
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html, body {
      width: 1200px;
      height: 1200px;
      overflow: hidden;
      background: #050811;
      font-family: 'Cairo', system-ui, sans-serif;
      color: #f8fafc;
    }
    .canvas {
      position: relative;
      width: 1200px;
      height: 1200px;
      padding: 44px 52px 38px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      background:
        radial-gradient(circle at 18% 0%, rgba(16, 185, 129, 0.22) 0%, transparent 48%),
        radial-gradient(circle at 82% 0%, rgba(6, 182, 212, 0.20) 0%, transparent 48%),
        radial-gradient(circle at 50% 100%, rgba(16, 185, 129, 0.14) 0%, transparent 55%),
        linear-gradient(180deg, #070c18 0%, #050811 100%);
    }
    .pitch-bg {
      position: absolute;
      inset: 22px;
      border: 1px solid rgba(16, 185, 129, 0.14);
      border-radius: 28px;
      pointer-events: none;
    }
    .pitch-circle {
      position: absolute;
      top: 50%;
      left: 50%;
      width: 340px;
      height: 340px;
      transform: translate(-50%, -50%);
      border-radius: 50%;
      border: 1px solid rgba(6, 182, 212, 0.08);
      pointer-events: none;
    }
    .header {
      position: relative;
      z-index: 2;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-bottom: 22px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.09);
    }
    .brand { display: flex; align-items: center; gap: 18px; }
    .brand-badge {
      width: 72px; height: 72px; border-radius: 20px;
      background: linear-gradient(135deg, #10b981 0%, #06b6d4 100%);
      display: flex; align-items: center; justify-content: center;
      font-size: 36px; box-shadow: 0 8px 28px rgba(16, 185, 129, 0.45);
    }
    .brand-text h1 { font-size: 40px; font-weight: 900; line-height: 1.1; }
    .brand-text h1 span { color: #34d399; }
    .brand-text p { font-size: 18px; font-weight: 700; color: #94a3b8; margin-top: 2px; }
    .date-pill {
      background: rgba(16, 185, 129, 0.14);
      border: 1.5px solid rgba(16, 185, 129, 0.45);
      color: #34d399;
      padding: 12px 26px;
      border-radius: 999px;
      font-size: 22px;
      font-weight: 800;
    }
    .footer {
      position: relative; z-index: 2;
      display: flex; align-items: center; justify-content: space-between;
      padding-top: 18px; border-top: 1px solid rgba(255, 255, 255, 0.09);
    }
    .cta-box { display: flex; align-items: center; gap: 12px; font-size: 22px; font-weight: 800; color: #e2e8f0; }
    .cta-pill {
      background: linear-gradient(135deg, #10b981 0%, #059669 100%);
      color: #ffffff; padding: 8px 22px; border-radius: 999px;
      font-size: 19px; font-weight: 900;
    }
    .site-tag { font-family: 'Chakra Petch', sans-serif; font-size: 20px; font-weight: 700; color: #34d399; }
"""


def find_headless_browser() -> str | None:
    """Locate Chrome or Edge executable on Windows or Linux CI."""
    for candidate in _BROWSER_CANDIDATES:
        p = Path(candidate)
        if p.is_absolute():
            if p.exists():
                return str(p)
        else:
            found = shutil.which(candidate)
            if found:
                return found
    return None


def _esc(val: Any) -> str:
    return html.escape(str(val or ""), quote=True)


def build_daily_schedule_poster_html(
    matches: Sequence[Mapping[str, Any]],
    *,
    date_label: str | None = None,
) -> str:
    """Build 1200x1200 Cyber-Stadium HTML for up to 5 top daily matches."""
    label = _esc(date_label or format_arabic_date_label())
    cards_html: list[str] = []

    for idx, m in enumerate(matches[:5]):
        home = _esc(m.get("home_team") or "")
        away = _esc(m.get("away_team") or "")
        h_logo = _esc(m.get("home_logo") or FALLBACK_LOGO_URL)
        a_logo = _esc(m.get("away_logo") or FALLBACK_LOGO_URL)
        comp = _esc(m.get("competition") or "بطولة كبرى")
        ch = _esc(m.get("channel") or "beIN SPORTS HD")
        times = format_cairo_mecca_times(m.get("kickoff_time"))
        cls = "card featured" if idx < 2 else "card"
        cards_html.append(
            f"""
      <div class="{cls}">
        <div class="team home">
          <div class="logo-wrap"><img src="{h_logo}" alt="{home}" onerror="this.onerror=null;this.src='{FALLBACK_LOGO_URL}';"/></div>
          <div class="team-name">{home}</div>
        </div>
        <div class="center">
          <span class="league-tag">{comp}</span>
          <div class="time-box">{_esc(times['mecca'])}</div>
          <div class="time-sub">مكة • {_esc(times['cairo'])} القاهرة</div>
          <div class="channel-tag">📺 {ch}</div>
        </div>
        <div class="team away">
          <div class="team-name">{away}</div>
          <div class="logo-wrap"><img src="{a_logo}" alt="{away}" onerror="this.onerror=null;this.src='{FALLBACK_LOGO_URL}';"/></div>
        </div>
      </div>"""
        )

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@600;700;800;900&family=Chakra+Petch:wght@700;800&display=swap" rel="stylesheet" />
  <style>
{_BASE_POSTER_CSS}
    .matches {{ position: relative; z-index: 2; display: flex; flex-direction: column; gap: 18px; margin: 18px 0; }}
    .card {{
      background: linear-gradient(135deg, rgba(15, 23, 42, 0.90) 0%, rgba(11, 18, 34, 0.85) 100%);
      border: 1px solid rgba(255, 255, 255, 0.09); border-radius: 22px; padding: 18px 28px;
      display: grid; grid-template-columns: 1fr 250px 1fr; align-items: center; gap: 16px;
    }}
    .card.featured {{
      border-color: rgba(16, 185, 129, 0.55);
      background: linear-gradient(135deg, rgba(16, 185, 129, 0.14) 0%, rgba(15, 23, 42, 0.95) 55%, rgba(6, 182, 212, 0.12) 100%);
    }}
    .team {{ display: flex; align-items: center; gap: 16px; }}
    .team.away {{ justify-content: flex-end; }}
    .logo-wrap {{
      width: 72px; height: 72px; border-radius: 18px; background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.12); display: flex; align-items: center; justify-content: center;
      padding: 8px; flex-shrink: 0;
    }}
    .logo-wrap img {{ width: 54px; height: 54px; object-fit: contain; }}
    .team-name {{ font-size: 26px; font-weight: 900; color: #f8fafc; line-height: 1.2; }}
    .center {{ display: flex; flex-direction: column; align-items: center; text-align: center; gap: 5px; }}
    .league-tag {{
      font-size: 13px; font-weight: 800; color: #38bdf8;
      background: rgba(56, 189, 248, 0.12); border: 1px solid rgba(56, 189, 248, 0.28);
      padding: 2px 12px; border-radius: 999px; white-space: nowrap;
    }}
    .time-box {{ font-family: 'Chakra Petch', 'Cairo', sans-serif; font-size: 32px; font-weight: 800; color: #ffffff; }}
    .time-box.score-mode {{ font-size: 38px; color: #34d399; letter-spacing: 2px; }}
    .time-sub {{ font-size: 14px; font-weight: 700; color: #34d399; }}
    .channel-tag {{ font-size: 13px; font-weight: 700; color: #cbd5e1; opacity: 0.9; }}
  </style>
</head>
<body>
  <div class="canvas">
    <div class="pitch-bg"></div>
    <div class="pitch-circle"></div>
    <header class="header">
      <div class="brand">
        <div class="brand-badge">⚽</div>
        <div class="brand-text">
          <h1>أهم مباريات <span>اليوم</span></h1>
          <p>كورة لايف — نتائج مباشرة وتغطية لحظة بلحظة</p>
        </div>
      </div>
      <div class="date-pill">{label}</div>
    </header>
    <main class="matches">
      {"".join(cards_html)}
    </main>
    <footer class="footer">
      <div class="cta-box">
        <span class="cta-pill">الرابط في أول تعليق 👇</span>
        <span>تابع النتائج والتشكيلات وملخصات الأهداف</span>
      </div>
      <div class="site-tag">KORA LIVE</div>
    </footer>
  </div>
</body>
</html>"""


def build_daily_results_poster_html(
    matches: Sequence[Mapping[str, Any]],
    *,
    date_label: str | None = None,
) -> str:
    """Build 1200x1200 Cyber-Stadium HTML summarizing today's final match results."""
    label = _esc(date_label or format_arabic_date_label())
    cards_html: list[str] = []

    for idx, m in enumerate(matches[:5]):
        home = _esc(m.get("home_team") or "")
        away = _esc(m.get("away_team") or "")
        h_logo = _esc(m.get("home_logo") or FALLBACK_LOGO_URL)
        a_logo = _esc(m.get("away_logo") or FALLBACK_LOGO_URL)
        comp = _esc(m.get("competition") or "بطولة كبرى")
        h_score = int(m.get("home_score") or 0)
        a_score = int(m.get("away_score") or 0)
        cls = "card featured" if idx < 2 else "card"
        cards_html.append(
            f"""
      <div class="{cls}">
        <div class="team home">
          <div class="logo-wrap"><img src="{h_logo}" alt="{home}" onerror="this.onerror=null;this.src='{FALLBACK_LOGO_URL}';"/></div>
          <div class="team-name">{home}</div>
        </div>
        <div class="center">
          <span class="league-tag">{comp}</span>
          <div class="time-box score-mode">{h_score} - {a_score}</div>
          <div class="time-sub">نتيجة نهائية</div>
        </div>
        <div class="team away">
          <div class="team-name">{away}</div>
          <div class="logo-wrap"><img src="{a_logo}" alt="{away}" onerror="this.onerror=null;this.src='{FALLBACK_LOGO_URL}';"/></div>
        </div>
      </div>"""
        )

    base = build_daily_schedule_poster_html([], date_label=label)
    return (
        base.replace("<h1>أهم مباريات <span>اليوم</span></h1>", "<h1>نتائج مباريات <span>اليوم</span></h1>")
        .replace("<main class=\"matches\">\n      \n    </main>", f"<main class=\"matches\">\n      {''.join(cards_html)}\n    </main>")
        .replace("تابع النتائج والتشكيلات وملخصات الأهداف", "ملخصات الأهداف وترتيب الفرق في أول تعليق")
    )


def build_match_poster_html(match: Mapping[str, Any], *, stage: str = "pre_match") -> str:
    """Build 1200x1200 Cyber-Stadium HTML for a single pre-match VS or post-match result card."""
    home = _esc(match.get("home_team") or "")
    away = _esc(match.get("away_team") or "")
    h_logo = _esc(match.get("home_logo") or FALLBACK_LOGO_URL)
    a_logo = _esc(match.get("away_logo") or FALLBACK_LOGO_URL)
    comp = _esc(match.get("competition") or "مواجهة كبرى")
    ch = _esc(match.get("channel") or "beIN SPORTS HD")
    times = format_cairo_mecca_times(match.get("kickoff_time"))
    h_score = int(match.get("home_score") or 0)
    a_score = int(match.get("away_score") or 0)

    is_post = stage == "post_match"
    badge_text = "النتيجة النهائية" if is_post else "قمة اليوم"
    center_main = f"{h_score} - {a_score}" if is_post else "VS"
    center_sub = "ملخص الأهداف والتقييمات في أول تعليق" if is_post else f"{times['mecca']} مكة • {times['cairo']} القاهرة"

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@600;700;800;900&family=Chakra+Petch:wght@700;800&display=swap" rel="stylesheet" />
  <style>
{_BASE_POSTER_CSS}
    .spotlight {{
      position: relative; z-index: 2; flex: 1; margin: 28px 0;
      border-radius: 30px; border: 1.5px solid rgba(16, 185, 129, 0.48);
      background: linear-gradient(135deg, rgba(16, 185, 129, 0.14) 0%, rgba(15, 23, 42, 0.94) 50%, rgba(6, 182, 212, 0.14) 100%);
      display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 36px; padding: 48px;
    }}
    .comp-pill {{
      font-size: 24px; font-weight: 800; color: #38bdf8;
      background: rgba(56, 189, 248, 0.14); border: 1px solid rgba(56, 189, 248, 0.35);
      padding: 8px 30px; border-radius: 999px;
    }}
    .vs-grid {{ width: 100%; display: grid; grid-template-columns: 1fr 260px 1fr; align-items: center; gap: 24px; }}
    .big-team {{ display: flex; flex-direction: column; align-items: center; gap: 20px; text-align: center; }}
    .big-logo {{
      width: 210px; height: 210px; border-radius: 36px; background: rgba(255, 255, 255, 0.06);
      border: 1.5px solid rgba(255, 255, 255, 0.14); display: flex; align-items: center; justify-content: center; padding: 24px;
    }}
    .big-logo img {{ width: 160px; height: 160px; object-fit: contain; }}
    .big-name {{ font-size: 36px; font-weight: 900; color: #ffffff; }}
    .score-hero {{
      font-family: 'Chakra Petch', sans-serif; font-size: 86px; font-weight: 800;
      color: #34d399; text-align: center; text-shadow: 0 0 36px rgba(16, 185, 129, 0.45);
    }}
    .info-bar {{
      font-size: 24px; font-weight: 800; color: #e2e8f0;
      background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(255, 255, 255, 0.10);
      padding: 14px 36px; border-radius: 999px;
    }}
    .channel-sub {{ font-size: 20px; font-weight: 700; color: #94a3b8; }}
  </style>
</head>
<body>
  <div class="canvas">
    <div class="pitch-bg"></div>
    <div class="pitch-circle"></div>
    <header class="header">
      <div class="brand">
        <div class="brand-badge">⚽</div>
        <div class="brand-text">
          <h1>كورة <span>لايف</span></h1>
          <p>تغطية مباشرة • تشكيلات • ملخصات</p>
        </div>
      </div>
      <div class="date-pill">{_esc(badge_text)}</div>
    </header>
    <main class="spotlight">
      <div class="comp-pill">{comp}</div>
      <div class="vs-grid">
        <div class="big-team">
          <div class="big-logo"><img src="{h_logo}" alt="{home}" onerror="this.onerror=null;this.src='{FALLBACK_LOGO_URL}';"/></div>
          <div class="big-name">{home}</div>
        </div>
        <div class="score-hero">{_esc(center_main)}</div>
        <div class="big-team">
          <div class="big-logo"><img src="{a_logo}" alt="{away}" onerror="this.onerror=null;this.src='{FALLBACK_LOGO_URL}';"/></div>
          <div class="big-name">{away}</div>
        </div>
      </div>
      <div class="info-bar">{_esc(center_sub)}</div>
      <div class="channel-sub">📺 القناة الناقلة: {ch}</div>
    </main>
    <footer class="footer">
      <div class="cta-box">
        <span class="cta-pill">الرابط في أول تعليق 👇</span>
        <span>شاركنا توقعك في التعليقات!</span>
      </div>
      <div class="site-tag">KORA LIVE</div>
    </footer>
  </div>
</body>
</html>"""


def render_poster_png(
    html_content: str,
    out_path: Path,
    *,
    browser_bin: str | None = None,
    timeout_s: int = 25,
) -> Path:
    """Render HTML poster content to a 1200x1200 PNG using headless Chrome or Edge."""
    browser = browser_bin or find_headless_browser()
    if not browser:
        raise RuntimeError("No Chrome or Edge browser executable found for poster rendering.")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile("w", suffix=".html", encoding="utf-8", delete=False) as tmp:
        tmp.write(html_content)
        tmp_html = Path(tmp.name)

    try:
        cmd = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--window-size=1200,1200",
            "--hide-scrollbars",
            "--virtual-time-budget=6000",
            f"--screenshot={out_path}",
            tmp_html.as_uri(),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
        if result.returncode != 0 or not out_path.exists():
            raise RuntimeError(f"Headless browser failed (rc={result.returncode}): {result.stderr}")
        return out_path
    finally:
        try:
            tmp_html.unlink(missing_ok=True)
        except OSError:
            pass
