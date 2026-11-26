# -*- coding: utf-8 -*-
"""Test suite for automated Blogger backup and disaster recovery."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


def test_backup_script_creates_feed_and_theme_snapshots(tmp_path):
    """Verify backup_blogger_content creates JSON and XML snapshots in data/backups."""
    from scripts.backup_blogger_content import run_backup

    fake_feed = {
        "feed": {
            "title": {"$t": "كورة لايف"},
            "entry": [
                {"title": {"$t": "مباراة اليوم"}, "content": {"$t": "تفاصيل المباراة"}}
            ]
        }
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_feed

    with patch("requests.get", return_value=mock_resp):
        out_json, out_xml = run_backup(backup_dir=tmp_path)
        assert out_json.exists()
        assert out_xml.exists()
        
        saved_data = json.loads(out_json.read_text(encoding="utf-8"))
        assert saved_data["feed"]["title"]["$t"] == "كورة لايف"
        assert len(saved_data["feed"]["entry"]) == 1
