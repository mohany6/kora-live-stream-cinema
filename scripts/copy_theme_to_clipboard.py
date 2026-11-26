# -*- coding: utf-8 -*-
"""Copy Blogger Theme XML to Clipboard and open Blogger Theme settings."""

import subprocess
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
THEME_XML = ROOT / "blogger_theme" / "kora_pro_blogger_theme.xml"

def copy_to_clipboard(text: str) -> bool:
    try:
        proc = subprocess.Popen(["clip"], stdin=subprocess.PIPE, shell=True)
        proc.communicate(input=text.encode("utf-8"))
        return proc.returncode == 0
    except Exception:
        return False

def main():
    try:
        from scripts.build_modern_blogger_theme import main as build_theme
        build_theme()
    except Exception as e:
        print(f"[*] Notice during theme rebuild: {e}")

    if not THEME_XML.exists():
        print(f"[!] Theme file not found: {THEME_XML}")
        return

    content = THEME_XML.read_text(encoding="utf-8")
    copied = copy_to_clipboard(content)

    print("=" * 65)
    print("  🎨 تم نسخ قالب بلوجر المطور بالكامل إلى الحافظة (Clipboard) 🎨")
    print("=" * 65)
    if copied:
        print("[✓] تم نسخ كود كورة لايف PRO بنجاح!")
    print("\n[خطوات تفعيل القالب في بلوجر خلال 10 ثوانٍ]:")
    print("  1. افتح صفحة 'المظهر' في بلوجر (تم فتحها بمتصفحك تلقائياً).")
    print("  2. اضغط على السهم الصغير بجانب زر 'تخصيص' البرتقالي.")
    print("  3. اختر 'تعديل HTML' (Edit HTML).")
    print("  4. اضغط Ctrl + A لتحديد الكود القديم كاملاً، ثم اضغط Ctrl + V للصق الكود الجديد.")
    print("  5. اضغط على زر الحفظ (أيقونة القرص 💾) أعلى يسار الصفحة.")
    print("=================================================================")
    print("[*] تم فتح صفحة المظهر في بلوجر تلقائياً...")
    try:
        webbrowser.open("https://www.blogger.com/go/theme")
    except Exception:
        pass

if __name__ == "__main__":
    main()
