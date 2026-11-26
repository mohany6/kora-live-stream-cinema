import xml.etree.ElementTree as ET
from pathlib import Path
from scripts.build_modern_blogger_theme import (
    build_preview_html,
    build_blogger_xml,
    MULTI_DAY_DATA,
)

def test_multi_day_datasets_present():
    assert "yesterday" in MULTI_DAY_DATA
    assert "today" in MULTI_DAY_DATA
    assert "tomorrow" in MULTI_DAY_DATA
    assert len(MULTI_DAY_DATA["yesterday"]) >= 2
    assert len(MULTI_DAY_DATA["today"]) >= 2
    assert len(MULTI_DAY_DATA["tomorrow"]) >= 2

def test_xml_is_valid_and_contains_day_switcher():
    xml = build_blogger_xml()
    tree = ET.fromstring(xml)
    assert tree.tag == "{http://www.w3.org/1999/xhtml}html"
    assert "dayTab_yesterday" in xml
    assert "dayTab_today" in xml
    assert "dayTab_tomorrow" in xml

def test_day_switcher_script_in_html():
    html = build_preview_html()
    assert "switchDayTab" in html
    assert "activeDayKey" in html
    assert "dayTab_today" in html

def test_compact_mode_markup_and_style():
    html = build_preview_html()
    assert "ay-match-compact" in html
    assert "toggleViewMode" in html
    assert "ad-card-behind-match" in html
