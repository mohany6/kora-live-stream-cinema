# -*- coding: utf-8 -*-
"""Automated Backup and Disaster Recovery Script for Blogger Content & Theme."""

from datetime import datetime
import json
from pathlib import Path
import shutil
import sys
import requests

ROOT = Path(__file__).resolve().parent.parent


def run_backup(
    backup_dir: Path | None = None,
    blog_url: str = "https://kora-live-to.blogspot.com"
) -> tuple[Path, Path]:
    """Fetch all Blogger posts from public JSON feed and snapshot current theme XML."""
    if backup_dir is None:
        backup_dir = ROOT / "data" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    out_json = backup_dir / f"blogger_posts_{date_str}.json"
    out_xml = backup_dir / f"theme_backup_{date_str}.xml"

    # 1. Backup all posts and published match articles
    feed_url = f"{blog_url.rstrip('/')}/feeds/posts/default?alt=json&max-results=500"
    try:
        resp = requests.get(feed_url, timeout=15)
        if resp.status_code == 200:
            posts_data = resp.json()
        else:
            posts_data = {
                "backup_date": date_str,
                "status": f"HTTP {resp.status_code}",
                "feed": {"title": {"$t": "كورة لايف"}, "entry": []}
            }
    except Exception as e:
        posts_data = {
            "backup_date": date_str,
            "error": str(e),
            "feed": {"title": {"$t": "كورة لايف"}, "entry": []}
        }

    out_json.write_text(json.dumps(posts_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2. Backup current Theme XML
    theme_xml_path = ROOT / "blogger_theme" / "kora_pro_blogger_theme.xml"
    if theme_xml_path.exists():
        shutil.copy2(theme_xml_path, out_xml)
    else:
        out_xml.write_text("<html/>", encoding="utf-8")

    return out_json, out_xml


if __name__ == "__main__":
    j, x = run_backup()
    print(f"Blogger Posts Backup saved: {j}")
    print(f"Blogger Theme Backup saved: {x}")
