# -*- coding: utf-8 -*-
"""Test suite verifying Blogger Theme Adsterra units, zero-CLS containers, and homepage upgrades."""

import xml.etree.ElementTree as ET
from scripts.build_modern_blogger_theme import (
    build_preview_html,
    build_blogger_xml,
    generate_blogger_xml,
    generate_theme_preview,
)


def test_adsterra_popunder_and_frequency_capping():
    """Verify Popunder tag exists with 20-minute localStorage frequency capping."""
    html = build_preview_html()
    xml = build_blogger_xml()
    popunder_url = "https://capitalhospitals.org/1/9d3379bfa7b20556e0328830cd7e5e7f"
    
    assert popunder_url in html
    assert popunder_url in xml
    assert "kora_popunder_last" in html or "kora_last_pop" in html
    assert "20 * 60 * 1000" in html or "1200000" in html


def test_adsterra_socialbar_and_billboard_keys():
    """Verify SocialBar, 728x90 desktop, and 320x50 mobile keys are present."""
    html = build_preview_html()
    xml = build_blogger_xml()
    socialbar_url = "https://czernik.org/14/4d85a8908516d9c268b82f4a5df10c8a"
    key_728 = "6703ea03ffb309455182c593d4e6ea81"
    key_320 = "1cdf29d3af257663a92ffa6b5207a68a"

    for content in (html, xml):
        assert socialbar_url in content
        assert key_728 in content
        assert key_320 in content
        assert "adsterra-header-billboard" in content


def test_adsterra_skyscraper_sidebars():
    """Verify 160x600 skyscraper ad tags exist for desktop sidebars."""
    html = build_preview_html()
    xml = build_blogger_xml()
    key_160 = "bee904d3f2a415fcd8e41f64598a9680"

    for content in (html, xml):
        assert key_160 in content
        assert "desktop-side-banner" in content or "skyscraper" in content


def test_adsterra_native_banner_and_smartlinks():
    """Verify Native Banner container and smartlink rotation logic exist."""
    html = build_preview_html()
    xml = build_blogger_xml()
    native_script = "https://czernik.org/21/f1180bd1a9f13152d2247022e3f6f1b0"
    native_div = "container-f1180bd1a9f13152d2247022e3f6f1b0"
    smartlink_1 = "https://budgetezy.org/4/ae626546295ba9dbdec2ea24a521084c"
    smartlink_2 = "https://asiafilm.org/4/67d5c06c56eb1c96b2ff42f4dc88412e"

    for content in (html, xml):
        assert native_script in content
        assert native_div in content
        assert smartlink_1 in content
        assert smartlink_2 in content


def test_homepage_status_filter_chips_and_league_carousel():
    """Verify status chips (All, Live, Upcoming, Finished) and league navigation carousel."""
    html = build_preview_html()
    xml = build_blogger_xml()

    for content in (html, xml):
        assert "filter-status-chips" in content or "status-chips" in content
        assert 'data-filter="all"' in content or "data-filter='all'" in content
        assert 'data-filter="live"' in content or "data-filter='live'" in content
        assert 'data-filter="upcoming"' in content or "data-filter='upcoming'" in content
        assert 'data-filter="finished"' in content or "data-filter='finished'" in content
        assert "league-nav-carousel" in content or "league-carousel" in content


def test_homepage_seo_article_and_faq_schema():
    """Verify 400+ word Arabic SEO section, FAQ accordion, and Schema.org FAQPage JSON-LD."""
    html = build_preview_html()
    xml = build_blogger_xml()

    for content in (html, xml):
        assert "seo-content-block" in content or "kora-seo-article" in content
        assert "faq-accordion-section" in content or "kora-faq-section" in content
        assert "schema.org" in content
        assert "FAQPage" in content


def test_in_page_stream_modal_presence():
    """Verify modal for viewing match streams directly inside Blogger theme."""
    html = build_preview_html()
    xml = build_blogger_xml()

    for content in (html, xml):
        assert "koraStreamModal" in content
        assert "closeStreamModal" in content or "closeModal" in content


def test_generated_xml_is_strictly_valid():
    """Verify generated XML parses with ElementTree without syntax errors."""
    xml_path = generate_blogger_xml()
    assert xml_path.exists()
    tree = ET.parse(xml_path)
    root = tree.getroot()
    assert root.tag.endswith("html")


def test_blogger_xml_has_single_canonical_and_crawler_ad_guard():
    """Verify no duplicate canonical tag, canonical homepage link, and crawler guard for Adsterra."""
    html = build_preview_html()
    xml = build_blogger_xml()

    # all-head-content already emits the authoritative canonical link in Blogger
    assert "all-head-content" in xml
    assert "rel='canonical'" not in xml
    assert 'rel="canonical"' not in xml
    assert "data:blog.canonicalHomepageUrl" in xml

    for content in (html, xml):
        assert "isSearchCrawler" in content
        assert "__koraIsCrawler" in content
        assert "Googlebot" in content
        assert "InspectionTool" in content
