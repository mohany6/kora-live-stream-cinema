# -*- coding: utf-8 -*-
"""Test suite for Dynamic Tunnel Discovery Bridge and Cloaked In-Theme Player Delivery."""

import pytest
from src.live_score.domain.article_generator import generate_blogger_article
from scripts.build_modern_blogger_theme import build_preview_html, build_blogger_xml


def test_article_contains_stream_bridge_and_no_raw_streams():
    """Verify generated Blogger article includes the hidden bridge tag and NO raw m3u8 or player iframes."""
    match = {
        "id": "123456",
        "home_name": "ريال مدريد",
        "away_name": "برشلونة",
        "league": "الدوري الإسباني",
        "kickoff_time": "2026-11-26T20:00:00Z",
    }
    art = generate_blogger_article(match, platform_base_url="https://active-tunnel-abc.trycloudflare.com")
    content = art["content"]

    assert 'id="kora-stream-bridge"' in content
    assert 'data-tunnel="https://active-tunnel-abc.trycloudflare.com"' in content
    # Anti-takedown: Must NOT contain raw stream extensions or third party streaming iframes
    assert ".m3u8" not in content
    assert "player.html" not in content
    assert "<iframe" not in content.lower() or "atOptions" in content  # Only Adsterra ad iframe is allowed


def test_theme_contains_tunnel_discovery_logic():
    """Verify Blogger theme JavaScript contains dynamic tunnel discovery and storage."""
    html = build_preview_html()
    xml = build_blogger_xml()

    for content in (html, xml):
        assert "kora_active_tunnel" in content
        assert "initTunnelDiscovery" in content or "discoverTunnel" in content
        assert "feeds/posts/default" in content or "kora-stream-bridge" in content
