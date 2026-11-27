# -*- coding: utf-8 -*-
"""Cyber-Stadium Desktop Studio GUI for 1-Button Facebook Page Poster & Publishing."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.auto_blogger_publisher import _get_setting, get_top_trending_matches, load_env_vars
from scripts.auto_facebook_publisher import (
    FB_ASSETS_DIR,
    run_facebook_publisher,
    save_fb_credentials_to_env,
)


class KoraFacebookStudioApp:
    """Tkinter Cyber-Stadium GUI for generating and publishing Facebook match posters."""

    BG_DARK = "#050811"
    BG_PANEL = "#0f172a"
    BG_INPUT = "#1e293b"
    EMERALD = "#10b981"
    CYAN = "#06b6d4"
    TEXT_WHITE = "#f8fafc"
    TEXT_MUTED = "#94a3b8"

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("كورة لايف — استوديو النشر الآلي لفيسبوك")
        self.root.geometry("1040x760")
        self.root.configure(bg=self.BG_DARK)
        self.root.minsize(920, 680)

        self.matches: list[dict] = []
        self.latest_poster_path: Path | None = None
        self.preview_photo: tk.PhotoImage | None = None

        self.mode_var = tk.StringVar(value="daily_slate")
        self.selected_match_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="جاري تحميل مباريات اليوم...")

        env_vars = load_env_vars()
        self.page_id_var = tk.StringVar(value=_get_setting("FB_PAGE_ID", env_vars))
        self.token_var = tk.StringVar(value=_get_setting("FB_PAGE_ACCESS_TOKEN", env_vars))

        self._build_ui()
        self._load_matches_async()

    def _build_ui(self) -> None:
        # Top header
        header = tk.Frame(self.root, bg=self.BG_PANEL, padx=20, pady=12)
        header.pack(fill="x", padx=14, pady=(12, 8))

        tk.Label(
            header,
            text="⚽ كورة لايف — استوديو النشر الآلي لصفحة فيسبوك",
            bg=self.BG_PANEL,
            fg=self.TEXT_WHITE,
            font=("Segoe UI", 15, "bold"),
        ).pack(side="right")

        tk.Button(
            header,
            text="🔄 تحديث المباريات",
            command=self._load_matches_async,
            bg=self.BG_INPUT,
            fg=self.CYAN,
            activebackground="#334155",
            activeforeground=self.TEXT_WHITE,
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left")

        # Controls Bar
        ctrl = tk.Frame(self.root, bg=self.BG_PANEL, padx=16, pady=12)
        ctrl.pack(fill="x", padx=14, pady=4)

        mode_frame = tk.Frame(ctrl, bg=self.BG_PANEL)
        mode_frame.pack(fill="x")

        tk.Radiobutton(
            mode_frame,
            text="جدول مباريات اليوم",
            variable=self.mode_var,
            value="daily_slate",
            bg=self.BG_PANEL,
            fg=self.TEXT_WHITE,
            selectcolor=self.BG_DARK,
            activebackground=self.BG_PANEL,
            activeforeground=self.EMERALD,
            font=("Segoe UI", 10, "bold"),
        ).pack(side="right", padx=(8, 12))

        tk.Radiobutton(
            mode_frame,
            text="نتائج مباريات اليوم",
            variable=self.mode_var,
            value="daily_results",
            bg=self.BG_PANEL,
            fg=self.TEXT_WHITE,
            selectcolor=self.BG_DARK,
            activebackground=self.BG_PANEL,
            activeforeground=self.EMERALD,
            font=("Segoe UI", 10, "bold"),
        ).pack(side="right", padx=8)

        tk.Radiobutton(
            mode_frame,
            text="كل مباريات الترند (بوست لكل مباراة)",
            variable=self.mode_var,
            value="trending_matches",
            bg=self.BG_PANEL,
            fg=self.TEXT_WHITE,
            selectcolor=self.BG_DARK,
            activebackground=self.BG_PANEL,
            activeforeground=self.EMERALD,
            font=("Segoe UI", 10, "bold"),
        ).pack(side="right", padx=8)

        tk.Radiobutton(
            mode_frame,
            text="مباراة محددة",
            variable=self.mode_var,
            value="match",
            bg=self.BG_PANEL,
            fg=self.TEXT_WHITE,
            selectcolor=self.BG_DARK,
            activebackground=self.BG_PANEL,
            activeforeground=self.EMERALD,
            font=("Segoe UI", 10, "bold"),
        ).pack(side="right", padx=8)

        self.match_combo = ttk.Combobox(
            mode_frame,
            textvariable=self.selected_match_var,
            state="readonly",
            width=44,
        )
        self.match_combo.pack(side="left", padx=6)

        # Primary 1-Click Action Row
        btn_row = tk.Frame(ctrl, bg=self.BG_PANEL, pady=8)
        btn_row.pack(fill="x", pady=(6, 0))

        self.run_btn = tk.Button(
            btn_row,
            text="🚀 توليد البوستر والنص (ونشره الآن بضغطة واحدة)",
            command=self._run_publisher_async,
            bg=self.EMERALD,
            fg="#ffffff",
            activebackground="#059669",
            activeforeground="#ffffff",
            relief="flat",
            padx=20,
            pady=10,
            cursor="hand2",
            font=("Segoe UI", 11, "bold"),
        )
        self.run_btn.pack(side="right")

        tk.Button(
            btn_row,
            text="📂 فتح مجلد البوستر",
            command=self._open_assets_folder,
            bg=self.BG_INPUT,
            fg=self.TEXT_WHITE,
            relief="flat",
            padx=12,
            pady=8,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=4)

        tk.Button(
            btn_row,
            text="🌐 فتح فيسبوك",
            command=lambda: webbrowser.open("https://www.facebook.com/"),
            bg=self.BG_INPUT,
            fg=self.CYAN,
            relief="flat",
            padx=12,
            pady=8,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=4)

        # Main Split Area: Left = Poster Preview, Right = Caption + First Comment
        body = tk.Frame(self.root, bg=self.BG_DARK)
        body.pack(fill="both", expand=True, padx=14, pady=6)

        # Poster Preview Panel
        left = tk.Frame(body, bg=self.BG_PANEL, width=420, padx=12, pady=12)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)

        tk.Label(
            left,
            text="🖼️ معاينة البوستر (1200×1200 PNG)",
            bg=self.BG_PANEL,
            fg=self.CYAN,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="e", pady=(0, 8))

        self.preview_label = tk.Label(
            left,
            text="اضغط على زر التوليد لعرض البوستر هنا",
            bg=self.BG_DARK,
            fg=self.TEXT_MUTED,
            width=46,
            height=22,
            font=("Segoe UI", 10),
        )
        self.preview_label.pack(fill="both", expand=True)

        # Copy Panel
        right = tk.Frame(body, bg=self.BG_PANEL, padx=14, pady=12)
        right.pack(side="right", fill="both", expand=True)

        cap_hdr = tk.Frame(right, bg=self.BG_PANEL)
        cap_hdr.pack(fill="x")
        tk.Label(
            cap_hdr,
            text="📝 نص المنشور (خالٍ من الروابط لرفع الوصول)",
            bg=self.BG_PANEL,
            fg=self.TEXT_WHITE,
            font=("Segoe UI", 10, "bold"),
        ).pack(side="right")
        tk.Button(
            cap_hdr,
            text="📋 نسخ النص",
            command=lambda: self._copy_text_widget(self.caption_box, "تم نسخ نص المنشور!"),
            bg=self.EMERALD,
            fg="#ffffff",
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left")

        self.caption_box = tk.Text(
            right,
            height=12,
            bg=self.BG_DARK,
            fg=self.TEXT_WHITE,
            insertbackground=self.TEXT_WHITE,
            relief="flat",
            wrap="word",
            font=("Segoe UI", 10),
            padx=10,
            pady=8,
        )
        self.caption_box.pack(fill="both", expand=True, pady=(6, 10))

        cmt_hdr = tk.Frame(right, bg=self.BG_PANEL)
        cmt_hdr.pack(fill="x")
        tk.Label(
            cmt_hdr,
            text="💬 أول تعليق (رابط مدونة بلوجر — ثبّته تحت المنشور)",
            bg=self.BG_PANEL,
            fg=self.CYAN,
            font=("Segoe UI", 10, "bold"),
        ).pack(side="right")
        tk.Button(
            cmt_hdr,
            text="📋 نسخ التعليق الأول",
            command=lambda: self._copy_text_widget(self.comment_box, "تم نسخ التعليق الأول!"),
            bg=self.CYAN,
            fg="#050811",
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left")

        self.comment_box = tk.Text(
            right,
            height=4,
            bg=self.BG_DARK,
            fg=self.TEXT_WHITE,
            insertbackground=self.TEXT_WHITE,
            relief="flat",
            wrap="word",
            font=("Segoe UI", 10),
            padx=10,
            pady=8,
        )
        self.comment_box.pack(fill="x", pady=(6, 0))

        # Credentials Panel (for 1-click Graph API auto-posting)
        creds = tk.Frame(self.root, bg=self.BG_PANEL, padx=14, pady=10)
        creds.pack(fill="x", padx=14, pady=(2, 6))

        tk.Label(creds, text="FB Page ID:", bg=self.BG_PANEL, fg=self.TEXT_MUTED, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        tk.Entry(creds, textvariable=self.page_id_var, width=20, bg=self.BG_INPUT, fg=self.TEXT_WHITE, relief="flat").pack(side="left", padx=(0, 12))

        tk.Label(creds, text="Page Access Token:", bg=self.BG_PANEL, fg=self.TEXT_MUTED, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        tk.Entry(creds, textvariable=self.token_var, width=36, show="*", bg=self.BG_INPUT, fg=self.TEXT_WHITE, relief="flat").pack(side="left", padx=(0, 12))

        tk.Button(
            creds,
            text="💾 حفظ للنشر الآلي",
            command=self._save_creds,
            bg=self.BG_INPUT,
            fg=self.EMERALD,
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left")

        # Status Bar
        tk.Label(
            self.root,
            textvariable=self.status_var,
            bg=self.BG_DARK,
            fg=self.EMERALD,
            anchor="e",
            padx=18,
            pady=6,
            font=("Segoe UI", 9, "bold"),
        ).pack(fill="x")

    def _load_matches_async(self) -> None:
        self.status_var.set("جاري جلب أحدث مباريات اليوم...")

        def worker() -> None:
            try:
                matches = get_top_trending_matches(limit=5)
            except Exception as exc:
                self.root.after(0, lambda: self.status_var.set(f"تعذر جلب المباريات: {exc}"))
                return

            def update_ui() -> None:
                self.matches = matches
                options = [f"{m['id']} | {m['home_team']} ضد {m['away_team']} ({m['competition']})" for m in matches]
                self.match_combo["values"] = options
                if options:
                    self.match_combo.current(0)
                    self.status_var.set(f"جاهز — تم تحميل {len(matches)} مباريات ترند لليوم.")
                else:
                    self.status_var.set("لا توجد مباريات مسجلة حالياً.")

            self.root.after(0, update_ui)

        threading.Thread(target=worker, daemon=True).start()

    def _run_publisher_async(self) -> None:
        self.run_btn.configure(state="disabled", text="⏳ جاري رسم البوستر والتجهيز...")
        self.status_var.set("جاري توليد البوستر بجودة 1200×1200...")

        mode = self.mode_var.get()
        match_id = None
        if mode == "match" and self.selected_match_var.get():
            match_id = self.selected_match_var.get().split("|", 1)[0].strip()

        def worker() -> None:
            try:
                res = run_facebook_publisher(mode=mode, match_id=match_id)
            except Exception as exc:
                self.root.after(0, lambda: self._on_publish_error(str(exc)))
                return
            self.root.after(0, lambda: self._on_publish_done(res))

        threading.Thread(target=worker, daemon=True).start()

    def _on_publish_error(self, err: str) -> None:
        self.run_btn.configure(state="normal", text="🚀 توليد البوستر والنص (ونشره الآن بضغطة واحدة)")
        self.status_var.set(f"خطأ: {err}")
        messagebox.showerror("خطأ", err)

    def _on_publish_done(self, res: dict) -> None:
        self.run_btn.configure(state="normal", text="🚀 توليد البوستر والنص (ونشره الآن بضغطة واحدة)")
        self.status_var.set(res.get("status_message", "تم بنجاح"))

        self.caption_box.delete("1.0", tk.END)
        self.caption_box.insert("1.0", res.get("caption", ""))

        self.comment_box.delete("1.0", tk.END)
        self.comment_box.insert("1.0", res.get("first_comment", ""))

        # Auto-copy caption to clipboard for instant 1-click convenience
        if res.get("caption"):
            self.root.clipboard_clear()
            self.root.clipboard_append(res["caption"])

        poster = res.get("poster_path")
        if poster and Path(poster).exists():
            self.latest_poster_path = Path(poster)
            try:
                img = tk.PhotoImage(file=str(self.latest_poster_path))
                self.preview_photo = img.subsample(3, 3)
                self.preview_label.configure(image=self.preview_photo, text="")
            except Exception:
                self.preview_label.configure(text=f"تم حفظ البوستر في:\n{poster}")

    def _copy_text_widget(self, widget: tk.Text, msg: str) -> None:
        content = widget.get("1.0", tk.END).strip()
        if not content:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.status_var.set(msg)

    def _save_creds(self) -> None:
        pid = self.page_id_var.get().strip()
        tok = self.token_var.get().strip()
        if not pid or not tok:
            messagebox.showwarning("تنبيه", "أدخل FB Page ID و Page Access Token أولاً.")
            return
        env_path = save_fb_credentials_to_env(pid, tok)
        self.status_var.set(f"تم حفظ مفاتيح فيسبوك بنجاح في {env_path.name}!")
        messagebox.showinfo("تم الحفظ", "تم حفظ مفاتيح فيسبوك! عند الضغط على زر النشر سيتم النشر تلقائياً على صفحتك.")

    def _open_assets_folder(self) -> None:
        FB_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(FB_ASSETS_DIR))  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(FB_ASSETS_DIR)])


def main() -> None:
    root = tk.Tk()
    KoraFacebookStudioApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
