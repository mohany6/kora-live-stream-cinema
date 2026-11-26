import xml.etree.ElementTree as ET
from pathlib import Path
import pytest
from scripts.build_modern_blogger_theme import generate_theme_preview, generate_blogger_xml, get_platform_url

def test_blogger_theme_valid_xml():
    xml_path = generate_blogger_xml()
    assert xml_path.exists()
    tree = ET.parse(xml_path)
    root = tree.getroot()
    assert "html" in root.tag.lower()

def test_blogger_match_links_use_path_route():
    xml_path = generate_blogger_xml()
    content = xml_path.read_text(encoding="utf-8")
    platform_url = get_platform_url()
    assert "/match/" in content
    assert "ad-slot-header" in content or "Official Sponsor" in content
    assert "ad-slot-sticky" in content or "sticky-ad" in content


def test_blogger_theme_javascript_syntax_validity():
    """Verify with Node.js that every single inline script in the Blogger theme has ZERO syntax errors."""
    import subprocess
    import shutil

    node_bin = Path(r"C:\Users\Mohany\Desktop\football-live-score-platform\.tools\node-v22.14.0-win-x64\node.exe")
    if not node_bin.exists():
        node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("Node.js not available for syntax check")

    check_script = Path(r"C:\Users\Mohany\Desktop\football-live-score-platform\test_theme_js_syntax.js")
    result = subprocess.run([str(node_bin), str(check_script)], capture_output=True, text=True)
    assert result.returncode == 0, f"JS Syntax Errors found:\n{result.stderr}\n{result.stdout}"


