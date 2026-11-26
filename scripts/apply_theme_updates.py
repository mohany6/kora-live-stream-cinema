import json
from pathlib import Path

ROOT = Path(r"C:\Users\Mohany\Desktop\football-live-score-platform")
ds_path = ROOT / "data" / "multi_day_dataset.json"
with open(ds_path, encoding="utf-8") as f:
    multi_day = json.load(f)

script_path = ROOT / "scripts" / "build_modern_blogger_theme.py"
content = script_path.read_text(encoding="utf-8")

# 1. Format and replace MULTI_DAY_DATA
formatted_data = "MULTI_DAY_DATA = " + json.dumps(multi_day, ensure_ascii=False, indent=4)
start_idx = content.find("MULTI_DAY_DATA = {")
end_idx = content.find("\nCSS_STYLES = \"\"\"")
if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + formatted_data + "\n\n" + content[end_idx:]
    print("[✓] Replaced MULTI_DAY_DATA block")
else:
    print(f"[!] Indices not found: {start_idx}, {end_idx}")

script_path.write_text(content, encoding="utf-8")
print("[✓] File saved")
