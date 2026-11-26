import { useEffect, useState } from "react";

import MatchDetailHybrid from "./components/MatchDetailHybrid";
import {
  SUPPORTED_TIMEZONES,
  fetchMatchDetail,
  fetchTodayMatches,
  localDateForOffset,
} from "./lib/api";

const LIVE_POLL_INTERVAL_MS = 30_000;

export function getMatchIdFromPath(pathname = typeof window !== "undefined" ? window.location.pathname : "") {
  if (!pathname) return null;
  const match = pathname.match(/^\/match\/([a-zA-Z0-9_-]+)/);
  return match ? match[1] : null;
}

export default function App() {
  const [darkMode, setDarkMode] = useState(() => {
    try {
      const stored = typeof window !== "undefined" && window.localStorage ? window.localStorage.getItem("kora-theme") : null;
      return stored ? stored === "dark" : true;
    } catch {
      return true;
    }
  });
  const [selectedTz, setSelectedTz] = useState(() => {
    try {
      const stored = typeof window !== "undefined" && window.localStorage ? window.localStorage.getItem("kora-selected-timezone") : null;
      return stored || "Asia/Riyadh";
    } catch {
      return "Asia/Riyadh";
    }
  });
  const [selectedId, setSelectedId] = useState(() => getMatchIdFromPath());
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(null);
  const [matches, setMatches] = useState([]);

  useEffect(() => {
    function handleLocationChange() {
      if (typeof window === "undefined") return;
      const matchId = getMatchIdFromPath(window.location.pathname);
      if (matchId) {
        setSelectedId(matchId);
      } else {
        setSelectedId(null);
        setDetail(null);
      }
    }
    window.addEventListener("popstate", handleLocationChange);
    return () => {
      window.removeEventListener("popstate", handleLocationChange);
    };
  }, []);

  // Root redirect to Blogger Hub (schedule lives exclusively on Blogger)
  useEffect(() => {
    if (!selectedId && typeof window !== "undefined") {
      try {
        window.location.replace("https://kora-live-to.blogspot.com");
      } catch (e) {
        window.location.href = "https://kora-live-to.blogspot.com";
      }
    }
  }, [selectedId]);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        window.localStorage.setItem("kora-theme", darkMode ? "dark" : "light");
      }
    } catch {}
  }, [darkMode]);

  useEffect(() => {
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        window.localStorage.setItem("kora-selected-timezone", selectedTz);
      }
    } catch {}
  }, [selectedTz]);

  // Load matches slate for quick match switcher inside cinema player
  useEffect(() => {
    if (!selectedId) return undefined;
    let cancelled = false;
    const controller = new AbortController();

    fetchTodayMatches({ date: localDateForOffset(0), tz: selectedTz, signal: controller.signal })
      .then((data) => {
        if (!cancelled && data?.matches) {
          setMatches(data.matches);
        }
      })
      .catch(() => {});

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [selectedId, selectedTz]);

  // Fetch match details when selectedId is active
  useEffect(() => {
    if (!selectedId) return undefined;
    let cancelled = false;
    const controller = new AbortController();
    setDetailLoading(true);
    setDetailError(null);
    setDetail(null);

    fetchMatchDetail(selectedId, { tz: selectedTz, signal: controller.signal })
      .then((payload) => {
        if (!cancelled) setDetail(payload);
      })
      .catch((requestError) => {
        if (!cancelled && requestError.name !== "AbortError") {
          setDetailError(requestError.message || "تعذر تحميل تفاصيل المباراة");
        }
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false);
      });

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [selectedId, selectedTz]);

  // Keep an open match center live (score, timeline, stats, standings).
  useEffect(() => {
    if (!selectedId) return undefined;
    let cancelled = false;
    let controller = null;

    const timer = window.setInterval(() => {
      if (document.visibilityState === "hidden") return;
      if (controller) controller.abort();
      controller = new AbortController();
      fetchMatchDetail(selectedId, { tz: selectedTz, signal: controller.signal })
        .then((payload) => {
          if (!cancelled) setDetail(payload);
        })
        .catch(() => {});
    }, LIVE_POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      if (controller) controller.abort();
      window.clearInterval(timer);
    };
  }, [selectedId, selectedTz]);

  function closeDetail() {
    if (typeof window !== "undefined") {
      window.location.href = "https://kora-live-to.blogspot.com";
      return;
    }
    setSelectedId(null);
    setDetail(null);
    setDetailError(null);
  }

  function handleSelectMatch(item) {
    const matchId = typeof item === "object" && item !== null ? item.id : item;
    if (typeof window !== "undefined" && window.history?.pushState) {
      window.history.pushState(null, "", `/match/${matchId}`);
    }
    setSelectedId(matchId);
    setDetail(null);
  }

  // When visiting root or non-match path, show redirect splash with direct link to Blogger Hub
  if (!selectedId) {
    return (
      <div
        data-testid="stream-cinema-redirect"
        className="min-h-screen bg-slate-950 text-white flex flex-col items-center justify-center p-6 text-center select-none"
      >
        <div className="max-w-md w-full bg-slate-900/90 border border-emerald-500/30 rounded-3xl p-8 shadow-2xl backdrop-blur-md">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-3xl">
            ⚽
          </div>
          <h1 className="text-xl font-black text-white mb-2">كورة لايف — سينما البث المباشر</h1>
          <p className="text-sm text-slate-300 mb-6">
            جدول المباريات والتحليلات التكتيكية متوفر حصرياً على موقعنا الرئيسي في بلوجر. جاري تحويلك الآن...
          </p>
          <a
            href="https://kora-live-to.blogspot.com"
            data-testid="blogger-hub-redirect-link"
            className="inline-flex items-center justify-center gap-2 w-full py-3.5 px-6 rounded-2xl bg-gradient-to-r from-emerald-500 to-teal-500 text-slate-950 font-black text-sm shadow-lg shadow-emerald-500/20 hover:scale-[1.02] active:scale-[0.98] transition"
          >
            الانتقال إلى جدول مباريات اليوم في كورة لايف ↗
          </a>
        </div>
      </div>
    );
  }

  // Match live cinema view
  return (
    <div className="app-shell">
      <header className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span
            aria-hidden="true"
            className="flex h-11 w-11 items-center justify-center rounded-2xl bg-brand text-xl shadow-sm shadow-brand/30"
          >
            ⚽
          </span>
          <div>
            <h1 className="text-lg font-extrabold leading-6 text-slate-900 dark:text-white sm:text-xl">
              كورة لايف — سينما البث المباشر
            </h1>
            <p className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
              بث متعدد السيرفرات • سيرفر VIP 4K • تحليل تكتيكي
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <a
            href="https://kora-live-to.blogspot.com"
            target="_blank"
            rel="noopener noreferrer"
            data-testid="blogger-hub-link"
            className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2.5 py-1.5 text-[11px] font-extrabold text-emerald-600 hover:bg-emerald-500/20 hover:border-emerald-500 dark:text-emerald-400 transition shadow-sm sm:px-3 sm:text-xs"
            title="الانتقال إلى موقع كورة لايف الرئيسي على بلوجر"
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span>🌐 الموقع الرئيسي (بلوجر) ↗</span>
          </a>

          <select
            data-testid="timezone-select"
            value={selectedTz}
            onChange={(e) => setSelectedTz(e.target.value)}
            className="rounded-full border border-slate-200 bg-white/70 px-2.5 py-1 text-[11px] font-bold text-slate-600 outline-none transition focus:border-brand dark:border-slate-700 dark:bg-surface-dark/70 dark:text-slate-300 sm:text-xs"
            aria-label="اختيار المنطقة الزمنية"
          >
            {SUPPORTED_TIMEZONES.map((tz) => (
              <option key={tz.id} value={tz.id} className="dark:bg-surface-dark dark:text-white">
                {tz.labelAr}
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={() => setDarkMode((value) => !value)}
            aria-label={darkMode ? "التبديل إلى الوضع النهاري" : "التبديل إلى الوضع الليلي"}
            className="rounded-full border border-slate-200 bg-white/70 px-3 py-1.5 text-xs font-bold text-slate-600 transition hover:border-brand/50 hover:text-brand dark:border-slate-700 dark:bg-surface-dark/70 dark:text-slate-300"
          >
            {darkMode ? "☀️ نهاري" : "🌙 ليلي"}
          </button>
        </div>
      </header>

      <main>
        {detailLoading && (
          <div className="glass-card rounded-3xl p-10 text-center text-sm font-bold text-slate-500 dark:text-slate-300">
            جارٍ تحميل مركز المباراة…
          </div>
        )}
        {detailError && !detailLoading && (
          <div className="glass-card rounded-3xl p-8 text-center">
            <p className="text-sm font-bold text-red-600 dark:text-red-300">{detailError}</p>
            <button
              type="button"
              onClick={closeDetail}
              className="mt-3 rounded-full bg-brand px-4 py-2 text-xs font-bold text-white"
            >
              العودة إلى جدول المباريات في بلوجر
            </button>
          </div>
        )}
        {detail && !detailLoading && (
          <MatchDetailHybrid
            detail={detail}
            onBack={closeDetail}
            onSelectMatch={handleSelectMatch}
            todayMatches={matches}
          />
        )}
      </main>

      <footer className="mt-8 border-t border-slate-200/70 py-5 text-center text-[10px] font-semibold leading-5 text-slate-400 dark:border-slate-700/60">
        <div className="mb-2">
          <a
            href="https://kora-live-to.blogspot.com"
            target="_blank"
            rel="noopener noreferrer"
            data-testid="blogger-footer-link"
            className="inline-flex items-center gap-1 font-bold text-emerald-600 hover:underline dark:text-emerald-400"
          >
            🌐 الانتقال إلى موقع كورة لايف الرئيسي (Blogger Hub) لمشاهدة جميع المباريات والأخبار الحصرية
          </a>
        </div>
        جميع روابط البث تعرض من مصادر خارجية ولا يتم استضافتها على خوادمنا.
        <br />
        كورة لايف — تجربة عربية أولاً لكرة القدم.
      </footer>
    </div>
  );
}
