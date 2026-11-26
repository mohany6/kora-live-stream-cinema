from unittest.mock import patch, MagicMock
from scripts.duckdns_sync import update_duckdns


def test_duckdns_update_success():
    mock_response = MagicMock()
    mock_response.read.return_value = b"OK"
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        success, message = update_duckdns("kora-test", "token-12345")
        assert success is True
        assert message == "OK"

        # Verify correct DuckDNS URL parameters
        args, _ = mock_urlopen.call_args
        req = args[0]
        url = req.full_url
        assert "domains=kora-test" in url
        assert "token=token-12345" in url


def test_duckdns_update_failure():
    mock_response = MagicMock()
    mock_response.read.return_value = b"KO"
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        success, message = update_duckdns("kora-test", "bad-token")
        assert success is False
        assert message == "KO"
