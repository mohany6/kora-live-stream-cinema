"""
Tests for the PRD specification and the RTL/Figma design-token contract.

The PRD is the binding document for data contracts, lifecycle states, stream
failover, timezone handling, and the admin override rules. The tokens file is
the single source of truth shared with Figma and the Tailwind theme.
"""

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOKENS_PATH = PROJECT_ROOT / "design" / "tokens.json"
PRD_PATH = PROJECT_ROOT / "docs" / "superpowers" / "specs" / "PRD.md"

HEX_COLOR = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


def _load_tokens() -> dict:
    assert TOKENS_PATH.exists(), "design/tokens.json is missing"
    return json.loads(TOKENS_PATH.read_text(encoding="utf-8"))


def _px(value: str) -> int:
    assert value.endswith("px"), f"expected a px value, got {value!r}"
    return int(value[:-2])


def test_tokens_metadata_declares_rtl_first_design_system():
    tokens = _load_tokens()
    assert tokens["meta"]["direction"] == "rtl"
    assert tokens["rtl"]["direction"] == "rtl"
    assert tokens["rtl"]["textAlign"] == "start"
    assert tokens["meta"]["version"]


def test_tokens_required_status_colors_are_present_and_exact():
    colors = _load_tokens()["colors"]["status"]
    assert colors["live-red"].lower() == "#dc2626"
    assert colors["countdown-green"].lower() == "#16a34a"
    assert colors["pitch-green"].lower() == "#15803d"

    for name in ("live-red", "countdown-green", "pitch-green"):
        assert HEX_COLOR.match(colors[name]), f"{name} must be a valid hex color"


def test_tokens_dark_and_light_neutral_scales_are_complete():
    colors = _load_tokens()["colors"]
    required = {"background", "surface", "surface-raised", "text", "text-muted", "border"}
    for mode in ("light", "dark"):
        assert required.issubset(colors[mode]), f"missing neutral keys in {mode}"
        for key in required:
            assert HEX_COLOR.match(colors[mode][key]), f"{mode}.{key} is not a hex color"


def test_tokens_spacing_scale_is_monotonic_and_uses_logical_rtl_properties():
    tokens = _load_tokens()
    scale = tokens["spacing"]["scale"]
    pixels = [_px(scale[key]) for key in sorted(scale, key=lambda k: int(k))]
    assert pixels[0] == 0
    assert pixels == sorted(pixels)
    assert {"4px", "8px", "16px", "24px"}.issubset(set(scale.values()))

    logical = set(tokens["rtl"]["logicalProperties"])
    assert {
        "margin-inline-start",
        "margin-inline-end",
        "padding-inline-start",
        "padding-inline-end",
        "inset-inline-start",
        "inset-inline-end",
    }.issubset(logical)

    # Physical direction properties must not be the design-system default.
    assert "margin-left" not in logical
    assert "padding-right" not in logical


def test_tokens_typography_supports_arabic_and_latin_lineups():
    typography = _load_tokens()["typography"]
    arabic = typography["fontFamily"]["arabic"]
    assert any(font in arabic for font in ("Cairo", "Tajawal", "Noto Kufi Arabic"))
    assert "Inter" in typography["fontFamily"]["latin"]

    assert typography["fontSize"]["base"] == "16px"
    assert typography["fontWeight"]["bold"] == 700
    assert typography["lineHeight"]["relaxed"] >= 1.5


def test_tokens_motion_and_component_contracts_for_live_badges_and_pitch():
    tokens = _load_tokens()
    motion = tokens["motion"]
    assert motion["livePulse"]["duration"] == "1.6s"
    assert motion["livePulse"]["iteration"] == "infinite"

    components = tokens["components"]
    assert components["matchCard"]["crestSize"]
    assert components["streamPlayer"]["aspectRatio"] == "16 / 9"
    assert components["pitch"]["aspectRatio"] == "68 / 105"
    assert components["pitch"]["lineColor"]


def test_prd_covers_lifecycle_data_contracts_failover_and_admin_rules():
    assert PRD_PATH.exists(), "PRD.md is missing"
    text = PRD_PATH.read_text(encoding="utf-8")

    required_sections = [
        "Product Requirements Document",
        "Data Contracts",
        "Match Lifecycle",
        "Stream Failover",
        "Admin",
        "Timezone",
        "Database",
        "Acceptance Criteria",
    ]
    for section in required_sections:
        assert section.lower() in text.lower(), f"PRD is missing section: {section}"

    for state in (
        "SCHEDULED",
        "IN_PLAY",
        "HALFTIME",
        "EXTRA_TIME",
        "PENALTIES",
        "FINISHED",
        "POSTPONED",
    ):
        assert state in text, f"PRD is missing lifecycle state {state}"

    for phrase in (
        "Admin Override",
        "Scraper",
        "Sports API",
        "mermaid",
        "erDiagram",
        "Asia/Riyadh",
        "api/v1/matches/today",
        "api/v1/matches/{match_id}",
        "api/v1/admin/matches/{match_id}/streams",
        "api/v1/admin/matches/{match_id}/override",
    ):
        assert phrase.lower() in text.lower(), f"PRD is missing contract: {phrase}"
