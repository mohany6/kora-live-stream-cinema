import re

def test_videojs_player_preserved_and_ads_stripped():
    sample_html = """
    <html>
      <head></head>
      <body>
        <script>const player = videojs('my-player', { autoplay: true });</script>
        <script src="https://acscdn.com/script.js"></script>
        <script>aclib.runPop({ zoneId: '999' });</script>
        <script>ConsoleBan.init();</script>
      </body>
    </html>
    """
    # Verify our updated regex preservation logic
    html = re.sub(r"<script[^>]*acscdn[^>]*>.*?</script>", "", sample_html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<script[^>]*>(?:(?!</script>).)*?aclib\.runPop.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<script[^>]*>(?:(?!</script>).)*?ConsoleBan.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<script[^>]*ima3[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    
    # Core videojs initialization must remain!
    assert "const player = videojs('my-player'" in html
    # Third party popunder and console ban must be gone
    assert "aclib.runPop" not in html
    assert "ConsoleBan" not in html
