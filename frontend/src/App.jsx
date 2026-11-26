import { useEffect, useMemo, useState } from "react";

import MatchCard from "./components/MatchCard";
import MatchDetailHybrid from "./components/MatchDetailHybrid";
import ScheduleFilterTabs, { SCHEDULE_TABS } from "./components/ScheduleFilterTabs";
import { isLiveStatus } from "./lib/format";
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

function LoadingCards() {
  return (
    <div className="space-y-3" aria-label="جارٍ تحميل المباريات">
      {[0, 1, 2].map((index) => (
        <div
          key={index}
          className="h-[104px] animate-pulse rounded-2xl border border-slate-200/60 bg-white/60 dark:border-slate-700/50 dark:bg-surface-dark/60"
        />
      ))}
    </div>
  );
}

function EmptyState({ label }) {
  return (
    <div className="rounded-3xl border border-dashed border-slate-300 bg-white/50 px-6 py-14 text-center dark:border-slate-700 dark:bg-surface-dark/40">
      <p className="text-4xl" aria-hidden="true">
        ⚽
      </p>
      <p className="mt-3 text-sm font-bold text-slate-600 dark:text-slate-300">{label}</p>
      <p className="mt-1 text-xs text-slate-400">تابعنا لاحقاً لمعرفة مواعيد المباريات</p>
    </div>
  );
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
  const [activeTab, setActiveTab] = useState("today");
  const [selectedLeague, setSelectedLeague] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [matches, setMatches] = useState([]);
  const [timezoneLabel, setTimezoneLabel] = useState("بتوقيت مكة المكرمة");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [selectedId, setSelectedId] = useState(() => getMatchIdFromPath());
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(null);

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

  const activeTabConfig = useMemo(
    () => SCHEDULE_TABS.find((tab) => tab.key === activeTab) || SCHEDULE_TABS[1],
    [activeTab],
  );

  const liveMatchesCount = useMemo(
    () => matches.filter((m) => isLiveStatus(m.status)).length,
    [matches],
  );
  const upcomingMatchesCount = useMemo(
    () => matches.filter((m) => m.status === "SCHEDULED").length,
    [matches],
  );
  const finishedMatchesCount = useMemo(
    () => matches.filter((m) => m.status === "FINISHED").length,
    [matches],
  );

  const availableLeagues = useMemo(() => {
    const map = new Map();
    for (const m of matches) {
      const name = m.league?.name_ar || m.competition_subtitle || "أخرى";
      if (!map.has(name)) {
        map.set(name, { name, count: 0 });
      }
      map.get(name).count += 1;
    }
    return Array.from(map.values());
  }, [matches]);

  const filteredMatches = useMemo(() => {
    return matches.filter((m) => {
      if (selectedLeague !== "all") {
        const comp = m.league?.name_ar || m.competition_subtitle || "أخرى";
        if (comp !== selectedLeague) return false;
      }
      if (statusFilter === "live") {
        return isLiveStatus(m.status);
      }
      if (statusFilter === "upcoming") {
        return m.status === "SCHEDULED";
      }
      if (statusFilter === "finished") {
        return m.status === "FINISHED";
      }
      return true;
    });
  }, [matches, selectedLeague, statusFilter]);

  const groupedMatches = useMemo(() => {
    const map = new Map();
    for (const m of filteredMatches) {
      const comp = m.league?.name_ar || m.competition_subtitle || "أخرى";
      if (!map.has(comp)) {
        map.set(comp, []);
      }
      map.get(comp).push(m);
    }
    return Array.from(map.entries()).map(([competition, items]) => ({
      competition,
      items,
    }));
  }, [filteredMatches]);

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

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    fetchTodayMatches({
      date: localDateForOffset(activeTabConfig.offset, { timeZone: selectedTz }),
      tz: selectedTz,
      signal: controller.signal,
    })
      .then((payload) => {
        if (cancelled) return;
        setMatches(payload.matches || []);
        if (payload.timezone_label_ar) setTimezoneLabel(payload.timezone_label_ar);
      })
      .catch((requestError) => {
        if (!cancelled && requestError.name !== "AbortError") {
          setError(requestError.message || "تعذر تحميل المباريات");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [activeTabConfig.offset, reloadKey, selectedTz]);

  // Silently refresh today's scores without blanking the schedule.
  useEffect(() => {
    if (activeTabConfig.offset !== 0) return undefined;
    let cancelled = false;
    let controller = null;

    const timer = window.setInterval(() => {
      if (document.visibilityState === "hidden") return;
      if (controller) controller.abort();
      controller = new AbortController();
      fetchTodayMatches({
        date: localDateForOffset(0, { timeZone: selectedTz }),
        tz: selectedTz,
        signal: controller.signal,
      })
        .then((payload) => {
          if (!cancelled) {
            setMatches(payload.matches || []);
            if (payload.timezone_label_ar) setTimezoneLabel(payload.timezone_label_ar);
          }
        })
        .catch(() => {
          // Keep the last good slate; the next poll retries.
        });
    }, LIVE_POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      if (controller) controller.abort();
      window.clearInterval(timer);
    };
  }, [activeTabConfig.offset, reloadKey, selectedTz]);

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
        .catch(() => {
          // Keep the last good detail; the next poll retries.
        });
    }, LIVE_POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      if (controller) controller.abort();
      window.clearInterval(timer);
    };
  }, [selectedId, selectedTz]);

  function closeDetail() {
    if (typeof window !== "undefined" && window.history?.pushState && window.location.pathname.startsWith("/match/")) {
      window.history.pushState(null, "", "/");
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
              كورة لايف
            </h1>
            <p className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
              نتائج مباشرة • بث متعدد السيرفرات • تحليل تكتيكي
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

      {selectedId ? (
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
                العودة إلى المباريات
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
      ) : (
        <main className="space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-base font-extrabold text-slate-900 dark:text-white sm:text-lg">
                {activeTabConfig.label}
              </h2>
              <p className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                جدول المباريات • {timezoneLabel}
              </p>
            </div>
            <ScheduleFilterTabs
              activeTab={activeTab}
              onTabChange={(tab) => {
                setActiveTab(tab);
                setSelectedLeague("all");
                setStatusFilter("all");
              }}
            />
          </div>

          {/* Status Filter Chips */}
          <div
            className="flex items-center gap-2 overflow-x-auto pb-1 text-xs no-scrollbar"
            role="tablist"
            aria-label="تصفية حالة المباريات"
          >
            <button
              type="button"
              role="tab"
              aria-selected={statusFilter === "all"}
              data-testid="status-filter-all"
              onClick={() => setStatusFilter("all")}
              className={[
                "whitespace-nowrap rounded-xl px-3.5 py-1.5 text-xs font-bold transition flex items-center gap-1.5",
                statusFilter === "all"
                  ? "bg-brand text-white shadow-sm shadow-brand/30"
                  : "border border-slate-200 bg-white/70 text-slate-600 hover:border-brand/40 dark:border-slate-700 dark:bg-surface-dark/70 dark:text-slate-300",
              ].join(" ")}
            >
              <span>الكل</span>
              <span className="rounded-full bg-black/10 px-1.5 py-0.2 text-[10px] dark:bg-white/10">
                {matches.length}
              </span>
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={statusFilter === "live"}
              data-testid="status-filter-live"
              onClick={() => setStatusFilter("live")}
              className={[
                "whitespace-nowrap rounded-xl px-3.5 py-1.5 text-xs font-bold transition flex items-center gap-1.5",
                statusFilter === "live"
                  ? "bg-red-600 text-white shadow-sm shadow-red-500/30"
                  : "border border-red-500/30 bg-red-500/5 text-red-600 hover:border-red-500/60 dark:bg-red-500/10 dark:text-red-400",
              ].join(" ")}
            >
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
              </span>
              <span>مباشر الآن</span>
              <span className="rounded-full bg-black/10 px-1.5 py-0.2 text-[10px] dark:bg-white/10">
                {liveMatchesCount}
              </span>
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={statusFilter === "upcoming"}
              data-testid="status-filter-upcoming"
              onClick={() => setStatusFilter("upcoming")}
              className={[
                "whitespace-nowrap rounded-xl px-3.5 py-1.5 text-xs font-bold transition flex items-center gap-1.5",
                statusFilter === "upcoming"
                  ? "bg-sky-600 text-white shadow-sm shadow-sky-500/30"
                  : "border border-slate-200 bg-white/70 text-slate-600 hover:border-sky-500/40 dark:border-slate-700 dark:bg-surface-dark/70 dark:text-slate-300",
              ].join(" ")}
            >
              <span>⏳</span>
              <span>لم تبدأ</span>
              <span className="rounded-full bg-black/10 px-1.5 py-0.2 text-[10px] dark:bg-white/10">
                {upcomingMatchesCount}
              </span>
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={statusFilter === "finished"}
              data-testid="status-filter-finished"
              onClick={() => setStatusFilter("finished")}
              className={[
                "whitespace-nowrap rounded-xl px-3.5 py-1.5 text-xs font-bold transition flex items-center gap-1.5",
                statusFilter === "finished"
                  ? "bg-slate-700 text-white shadow-sm"
                  : "border border-slate-200 bg-white/70 text-slate-600 hover:border-slate-400 dark:border-slate-700 dark:bg-surface-dark/70 dark:text-slate-300",
              ].join(" ")}
            >
              <span>🏁</span>
              <span>انتهت</span>
              <span className="rounded-full bg-black/10 px-1.5 py-0.2 text-[10px] dark:bg-white/10">
                {finishedMatchesCount}
              </span>
            </button>
          </div>

          {availableLeagues.length > 1 && (
            <div
              className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs no-scrollbar"
              role="tablist"
              aria-label="تصفية حسب الدوري"
            >
              <button
                type="button"
                role="tab"
                aria-selected={selectedLeague === "all"}
                onClick={() => setSelectedLeague("all")}
                className={[
                  "whitespace-nowrap rounded-full px-3 py-1 text-xs font-bold transition",
                  selectedLeague === "all"
                    ? "bg-brand text-white shadow-sm shadow-brand/30"
                    : "border border-slate-200 bg-white/70 text-slate-600 hover:border-brand/40 dark:border-slate-700 dark:bg-surface-dark/70 dark:text-slate-300",
                ].join(" ")}
              >
                الكل ({matches.length})
              </button>
              {availableLeagues.map((league) => (
                <button
                  key={league.name}
                  type="button"
                  role="tab"
                  aria-selected={selectedLeague === league.name}
                  onClick={() => setSelectedLeague(league.name)}
                  className={[
                    "whitespace-nowrap rounded-full px-3 py-1 text-xs font-bold transition",
                    selectedLeague === league.name
                      ? "bg-brand text-white shadow-sm shadow-brand/30"
                      : "border border-slate-200 bg-white/70 text-slate-600 hover:border-brand/40 dark:border-slate-700 dark:bg-surface-dark/70 dark:text-slate-300",
                  ].join(" ")}
                >
                  {league.name} ({league.count})
                </button>
              ))}
            </div>
          )}

          {loading && <LoadingCards />}

          {!loading && error && (
            <div className="glass-card rounded-3xl p-8 text-center">
              <p className="text-sm font-bold text-red-600 dark:text-red-300">{error}</p>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                تعذر تحميل بيانات المباريات حالياً. يرجى المحاولة مرة أخرى.
              </p>
              <button
                type="button"
                onClick={() => setReloadKey((value) => value + 1)}
                className="mt-3 rounded-full bg-brand px-4 py-2 text-xs font-bold text-white transition hover:bg-brand-hover"
              >
                إعادة المحاولة
              </button>
            </div>
          )}

          {!loading && !error && filteredMatches.length === 0 && (
            <EmptyState
              label={
                statusFilter === "live"
                  ? "لا توجد مباريات جارية حالياً"
                  : statusFilter === "upcoming"
                  ? "لا توجد مباريات مجدولة قادمة"
                  : statusFilter === "finished"
                  ? "لا توجد مباريات منتهية"
                  : selectedLeague === "all"
                  ? "لا توجد مباريات في هذا اليوم"
                  : `لا توجد مباريات في ${selectedLeague}`
              }
            />
          )}

          {!loading && !error && filteredMatches.length > 0 && (
            <section className="space-y-6" aria-label="قائمة المباريات">
              {groupedMatches.map((group, idx) => (
                <div key={group.competition} className="space-y-2.5">
                  <div className="flex items-center justify-between border-b border-slate-200/60 pb-1.5 px-1 dark:border-slate-700/50">
                    <div className="flex items-center gap-2">
                      <span className="h-2.5 w-1 rounded-full bg-brand" aria-hidden="true" />
                      <h3 className="text-xs font-black tracking-wide text-slate-800 dark:text-slate-200 sm:text-sm">
                        {group.competition}
                      </h3>
                    </div>
                    <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[10px] font-bold text-slate-500 dark:bg-surface-dark dark:text-slate-400">
                      {group.items.length === 1 ? "مباراة واحدة" : `${group.items.length} مباريات`}
                    </span>
                  </div>
                  <div className="space-y-3">
                    {group.items.map((match) => (
                      <MatchCard
                        key={match.id}
                        match={match}
                        onSelect={handleSelectMatch}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </section>
          )}
        </main>
      )}

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
