import pytest
from scripts.extract_tunnel_url import parse_trycloudflare_url

def test_parse_trycloudflare_url_success():
    log_content = """
    2026-11-24T02:00:00Z INF +--------------------------------------------------------------------------------------------+
    2026-11-24T02:00:00Z INF |  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):  |
    2026-11-24T02:00:00Z INF |  https://crisp-banana-xyz.trycloudflare.com                                                |
    2026-11-24T02:00:00Z INF +--------------------------------------------------------------------------------------------+
    """
    url = parse_trycloudflare_url(log_content)
    assert url == "https://crisp-banana-xyz.trycloudflare.com"

def test_parse_trycloudflare_url_none():
    assert parse_trycloudflare_url("some random startup logs with no url") is None
