import { useEffect, useState } from "react";

import { formatCountdown, isLiveStatus, liveMinuteLabel, teamInitial } from "../lib/format";
import { useCountdown } from "../lib/useCountdown";
import { fetchTodayMatches, localDateForOffset } from "../lib/api";
import StreamPlayerContainer from "./StreamPlayerContainer";
import TacticalPitchView from "./TacticalPitchView";

const TABS = [
  { id: "summary", label: "الملخص" },
  { id: "lineup", label: "التشكيلة" },
  { id: "stats", label: "الإحصائيات" },
  { id: "standings", label: "الترتيب" },
];

const EVENT_ICONS = {
  goal: "⚽",
  yellow_card: "🟨",
  red_card: "🟥",
  substitution: "🔄",
  var: "📺",
};

function TeamBlock({ team }) {
  if (!team) return <div className="flex flex-1" />;
  return (
    <div className="flex flex-1 flex-col items-center gap-1.5 text-center">
      {team.logo_url ? (
        <img
          src={team.logo_url}
          alt=""
          className="h-12 w-12 rounded-full object-contain sm:h-14 sm:w-14"
          onError={(e) => {
            e.currentTarget.onerror = null;
            e.currentTarget.src = "https://cdn-icons-png.flaticon.com/512/53/53283.png";
          }}
        />
      ) : (
        <span
          aria-hidden="true"
          className="flex h-12 w-12 items-center justify-center rounded-full bg-white/10 text-lg font-extrabold text-white sm:h-14 sm:w-14"
        >
          {teamInitial(team.name_ar || team.name_en)}
        </span>
      )}
      <span className="text-xs font-bold leading-5 text-white sm:text-sm">{team.name_ar || team.name_en || "الفريق"}</span>
    </div>
  );
}

function HeaderStatus({ match }) {
  if (!match) return null;
  const live = isLiveStatus(match.status);
  const scheduled = match.status === "SCHEDULED";
  const seconds = useCountdown(match.countdown_seconds);

  return (
    <div className="flex flex-col items-center gap-1">
      {live ? (
        <>
          <div data-testid="detail-score" dir="ltr" className="font-latin text-2xl font-black text-white sm:text-3xl">
            {match.home_score ?? 0} - {match.away_score ?? 0}
          </div>
          <span
            data-testid="detail-live-badge"
            className="rounded-full bg-red-500/20 px-2.5 py-0.5 text-[10px] font-bold text-red-300"
          >
            {match.status_label_ar || "مباشر الآن"}
            {liveMinuteLabel(match) ? ` (${liveMinuteLabel(match)})` : ""}
          </span>
        </>
      ) : scheduled ? (
        <>
          <span className="font-latin text-lg font-bold text-white sm:text-xl">
            {match.kickoff_time_local || "--:--"}
          </span>
          <span className="text-[10px] font-semibold text-slate-300">
            {match.status_label_ar || "لم تبدأ"}
            {seconds !== null && seconds > 0 ? ` (تبدأ بعد ${formatCountdown(seconds)})` : ""}
          </span>
        </>
      ) : (
        <>
          <div data-testid="detail-score" dir="ltr" className="font-latin text-2xl font-black text-white sm:text-3xl">
            {match.home_score ?? 0} - {match.away_score ?? 0}
          </div>
          <span className="rounded-full bg-slate-700/60 px-2.5 py-0.5 text-[10px] font-bold text-slate-300">
            {match.status_label_ar || "انتهت"}
          </span>
        </>
      )}
    </div>
  );
}

function Timeline({ events = [] }) {
  if (!events.length) {
    return <p className="py-8 text-center text-sm text-slate-500 dark:text-slate-400">لا توجد أحداث مسجلة بعد</p>;
  }

  return (
    <ul data-testid="timeline" className="relative space-y-3 ps-4 text-xs sm:text-sm">
      <span aria-hidden="true" className="absolute bottom-1 top-1 start-1 w-0.5 bg-slate-200 dark:bg-slate-700" />
      {events.map((event) => (
        <li key={event.id} className="relative flex items-start gap-3">
          <span
            aria-hidden="true"
            className="relative z-10 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs shadow-sm dark:bg-surface-dark-raised"
          >
            {EVENT_ICONS[event.type] || "•"}
          </span>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span dir="ltr" className="font-latin text-[11px] font-bold text-brand sm:text-xs">
                {event.minute ? `${event.minute}'` : ""}
              </span>
              <span className="font-bold text-slate-800 dark:text-slate-100">{event.player_name}</span>
              {event.team_name_ar && <span className="text-[11px] text-slate-400">({event.team_name_ar})</span>}
            </div>
            {event.description_ar && (
              <p className="mt-0.5 text-[11px] leading-5 text-slate-500 dark:text-slate-400 sm:text-xs">
                {event.description_ar}
              </p>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}

function StatsPanel({ stats = [] }) {
  if (!stats.length) {
    return <p className="py-8 text-center text-sm text-slate-500 dark:text-slate-400">لا توجد إحصائيات متاحة</p>;
  }

  return (
    <div data-testid="stats-panel" className="space-y-4">
      {stats.map((stat) => {
        const total = Number(stat.home) + Number(stat.away);
        const homeShare = total > 0 ? (Number(stat.home) / total) * 100 : 50;
        return (
          <div key={stat.key}>
            <div className="mb-1.5 flex items-center justify-between text-xs font-bold sm:text-sm">
              <span dir="ltr" className="font-latin text-brand">
                {stat.home}
                {stat.unit}
              </span>
              <span className="text-slate-600 dark:text-slate-300">{stat.label_ar}</span>
              <span dir="ltr" className="font-latin text-slate-500 dark:text-slate-400">
                {stat.away}
                {stat.unit}
              </span>
            </div>
            <div className="flex h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-surface-dark-raised">
              <div className="h-full bg-brand" style={{ width: `${homeShare}%` }} />
              <div className="h-full flex-1 bg-slate-400 dark:bg-slate-600" />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function StandingsTable({ rows = [] }) {
  if (!rows.length) {
    return <p className="py-8 text-center text-sm text-slate-500 dark:text-slate-400">لا يوجد جدول ترتيب متاح</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table data-testid="standings-table" className="w-full min-w-[560px] text-center text-[11px] sm:text-xs">
        <thead>
          <tr className="text-slate-500 dark:text-slate-400">
            <th className="px-2 py-2 font-bold">#</th>
            <th className="px-2 py-2 text-start font-bold">الفريق</th>
            <th className="px-2 py-2 font-bold">لعب</th>
            <th className="px-2 py-2 font-bold">فاز</th>
            <th className="px-2 py-2 font-bold">تعادل</th>
            <th className="px-2 py-2 font-bold">خسر</th>
            <th className="px-2 py-2 font-bold">له</th>
            <th className="px-2 py-2 font-bold">عليه</th>
            <th className="px-2 py-2 font-bold">النقاط</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const highlighted = row.is_home || row.is_away;
            return (
              <tr
                key={`${row.position}-${row.team_name_ar}`}
                className={
                  highlighted
                    ? "border-t border-brand/20 bg-brand/10 font-bold"
                    : "border-t border-slate-200/70 dark:border-slate-700/60"
                }
              >
                <td className="px-2 py-2 font-latin">{row.position}</td>
                <td className="px-2 py-2 text-start">
                  {row.team_name_ar}
                  {row.is_home && <span className="ms-1 text-[9px] text-brand">(المضيف)</span>}
                  {row.is_away && <span className="ms-1 text-[9px] text-brand">(الضيف)</span>}
                </td>
                <td className="px-2 py-2 font-latin">{row.played}</td>
                <td className="px-2 py-2 font-latin">{row.won}</td>
                <td className="px-2 py-2 font-latin">{row.drawn}</td>
                <td className="px-2 py-2 font-latin">{row.lost}</td>
                <td className="px-2 py-2 font-latin">{row.goals_for}</td>
                <td className="px-2 py-2 font-latin">{row.goals_against}</td>
                <td className="px-2 py-2 font-latin font-extrabold text-brand">{row.points}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function calculateRegionalTimes(kickoffUtc) {
  if (!kickoffUtc) return null;
  try {
    const d = new Date(kickoffUtc);
    if (isNaN(d.getTime())) return null;
    const fmt = (tz) =>
      new Intl.DateTimeFormat("en-US", {
        timeZone: tz,
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      }).format(d);

    return {
      makkah: fmt("Asia/Riyadh"),
      cairo: fmt("Africa/Cairo"),
      uae: fmt("Asia/Dubai"),
      morocco: fmt("Africa/Casablanca"),
      gmt: fmt("UTC"),
    };
  } catch (e) {
    return null;
  }
}

function MatchDescriptionCard({ match }) {
  const times = calculateRegionalTimes(match.kickoff_time_utc);
  const isLive = isLiveStatus(match.status);
  const isFin = match.status === "FINISHED";

  const home = match.home_team?.name_ar || match.home_team?.name_en || "الفريق الأول";
  const away = match.away_team?.name_ar || match.away_team?.name_en || "الفريق الثاني";
  const league = match.league?.name_ar || match.league?.name_en || "البطولة";
  const channel = match.channel || "beIN SPORTS";
  const commentator = match.commentator || "يحدد لاحقاً";
  const stadium = match.stadium || "ملعب المباراة";

  return (
    <article
      data-testid="match-description-card"
      dir="rtl"
      className="rounded-3xl border border-slate-200/70 bg-gradient-to-b from-white/90 to-slate-50/90 p-4 sm:p-5 shadow-sm dark:border-slate-800 dark:from-surface-dark dark:to-surface-dark-raised/80 space-y-4"
    >
      <div className="flex items-center gap-2 border-b border-slate-200/60 pb-3 dark:border-slate-800">
        <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand/10 text-brand text-base font-bold">
          📋
        </span>
        <div>
          <h2 className="text-xs sm:text-sm font-extrabold text-slate-800 dark:text-slate-100">
            تفاصيل وتغطية مباراة {home} ضد {away}
          </h2>
          <p className="text-[10px] text-slate-400">
            {league} {match.league?.round ? `• ${match.league.round}` : ""}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 text-[11px] sm:grid-cols-4 sm:text-xs">
        <div className="flex items-center gap-2 rounded-xl bg-slate-100/70 p-2.5 dark:bg-surface-dark-raised/60">
          <span className="text-base">📺</span>
          <div>
            <span className="text-[10px] text-slate-400 block">القناة الناقلة</span>
            <strong className="font-bold text-slate-700 dark:text-slate-200">{channel}</strong>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-xl bg-slate-100/70 p-2.5 dark:bg-surface-dark-raised/60">
          <span className="text-base">🎙️</span>
          <div>
            <span className="text-[10px] text-slate-400 block">المعلق الصوتي</span>
            <strong className="font-bold text-slate-700 dark:text-slate-200">{commentator}</strong>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-xl bg-slate-100/70 p-2.5 dark:bg-surface-dark-raised/60">
          <span className="text-base">🏟️</span>
          <div>
            <span className="text-[10px] text-slate-400 block">الملعب</span>
            <strong className="font-bold text-slate-700 dark:text-slate-200 truncate max-w-[120px] block" title={stadium}>
              {stadium}
            </strong>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-xl bg-slate-100/70 p-2.5 dark:bg-surface-dark-raised/60">
          <span className="text-base">🏆</span>
          <div>
            <span className="text-[10px] text-slate-400 block">البطولة</span>
            <strong className="font-bold text-slate-700 dark:text-slate-200 truncate max-w-[120px] block" title={league}>
              {league}
            </strong>
          </div>
        </div>
      </div>

      {times && (
        <div className="rounded-2xl border border-brand/20 bg-brand/5 p-3 dark:bg-brand/10">
          <div className="mb-2 flex items-center justify-between text-xs font-bold text-brand">
            <span className="flex items-center gap-1.5">
              <span>⏰</span> مواعيد انطلاق المباراة حسب العواصم العربية:
            </span>
            <span className="text-[10px] text-slate-400 font-normal">توقيت 24 ساعة</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-center sm:grid-cols-5">
            <div className="rounded-xl bg-white/70 py-1.5 px-2 dark:bg-surface-dark">
              <span className="text-[10px] text-slate-400 block">مكة المكرمة 🇸🇦</span>
              <span className="font-latin text-xs font-extrabold text-slate-800 dark:text-slate-100">{times.makkah}</span>
            </div>
            <div className="rounded-xl bg-white/70 py-1.5 px-2 dark:bg-surface-dark">
              <span className="text-[10px] text-slate-400 block">القاهرة 🇪🇬</span>
              <span className="font-latin text-xs font-extrabold text-slate-800 dark:text-slate-100">{times.cairo}</span>
            </div>
            <div className="rounded-xl bg-white/70 py-1.5 px-2 dark:bg-surface-dark">
              <span className="text-[10px] text-slate-400 block">أبوظبي 🇦🇪</span>
              <span className="font-latin text-xs font-extrabold text-slate-800 dark:text-slate-100">{times.uae}</span>
            </div>
            <div className="rounded-xl bg-white/70 py-1.5 px-2 dark:bg-surface-dark">
              <span className="text-[10px] text-slate-400 block">المغرب 🇲🇦</span>
              <span className="font-latin text-xs font-extrabold text-slate-800 dark:text-slate-100">{times.morocco}</span>
            </div>
            <div className="col-span-2 sm:col-span-1 rounded-xl bg-white/70 py-1.5 px-2 dark:bg-surface-dark">
              <span className="text-[10px] text-slate-400 block">غرينتش (UTC) 🌍</span>
              <span className="font-latin text-xs font-extrabold text-slate-800 dark:text-slate-100">{times.gmt}</span>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-2 text-xs sm:text-[13px] leading-relaxed text-slate-600 dark:text-slate-300">
        {isFin ? (
          <p>
            أسدل الستار على مواجهة <strong>{home}</strong> و<strong>{away}</strong> بنتيجة نهائية (<strong>{match.home_score} - {match.away_score}</strong>) في ختام منافسات الجولة ببطولة <strong>{league}</strong>، بعد مباراة شهدت أداءً تكتيكياً حماسياً وسرعة في تناقل الكرة عبر خطوط الميدان.
          </p>
        ) : isLive ? (
          <p>
            تتواصل الآن مجريات اللقاء المثير بين <strong>{home}</strong> و<strong>{away}</strong> وسط أجواء مشحونة بالحماس على أرضية <strong>{stadium}</strong>، حيث يسعى كلا الفريقين لفرض السيطرة واستغلال الفرص السانحة لحسم النقاط الثلاث في بطولة <strong>{league}</strong>.
          </p>
        ) : (
          <p>
            يلتقي فريق <strong>{home}</strong> بنظيره <strong>{away}</strong> في قمة كروية منتظرة ضمن مواجهات <strong>{league}</strong>. يدخل <strong>{home}</strong> اللقاء متسلحاً بعاملي الأرض والجمهور على أرضية <strong>{stadium}</strong> لتحقيق الفوز، في حين يسعى <strong>{away}</strong> لتأكيد تفوقه التكتيكي واقتناص نتيجة إيجابية خارج الديار في صراع حاسم لحصد النقاط وتعزيز الترتيب.
          </p>
        )}
        <p>
          يتم نقل مجريات اللقاء عبر شبكة قنوات <strong>{channel}</strong> مع تقديم تغطية شاملة واستوديو تحليلي يضم نخبة من المحللين الرياضيين لرصد التشكيلات والخطط التكتيكية، بصوت المعلق الرياضي <strong>{commentator}</strong>.
        </p>
      </div>
    </article>
  );
}

function LiveMatchesSwitcher({ matches = [], currentMatchId, onSelectMatch }) {
  const otherMatches = matches.filter((m) => String(m.id) !== String(currentMatchId));
  if (!otherMatches.length) return null;

  return (
    <nav aria-label="التبديل بين المباريات الحية" className="space-y-1.5 rounded-2xl bg-slate-900/40 p-2.5 border border-slate-800/80">
      <div className="flex items-center justify-between px-1 text-[11px] font-bold text-slate-400">
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
          مباريات أخرى جارية ومجدولة اليوم ({otherMatches.length})
        </span>
        <span className="text-[10px] text-slate-500">اضغط للتبديل الفوري بين المباريات</span>
      </div>
      <div className="no-scrollbar flex items-center gap-2 overflow-x-auto pb-1">
        {otherMatches.map((m) => {
          const isLive = isLiveStatus(m.status);
          const homeName = m.home_team?.name_ar || m.home_team?.name_en;
          const awayName = m.away_team?.name_ar || m.away_team?.name_en;

          return (
            <button
              key={m.id}
              type="button"
              onClick={() => {
                if (onSelectMatch) {
                  onSelectMatch(m.id);
                } else if (typeof window !== "undefined") {
                  window.location.href = `/match/${m.id}`;
                }
              }}
              className="flex shrink-0 items-center gap-2 rounded-xl border border-slate-700/60 bg-slate-800/90 px-3 py-1.5 text-xs text-white shadow-sm hover:border-brand/70 hover:bg-slate-700 transition"
            >
              <div className="flex items-center gap-1.5">
                <span className="font-semibold text-slate-200">{homeName}</span>
                {isLive ? (
                  <span className="rounded bg-red-500/20 px-1 font-mono text-[11px] font-extrabold text-red-400">
                    {m.home_score ?? 0} - {m.away_score ?? 0}
                  </span>
                ) : (
                  <span className="text-[10px] text-slate-400">vs</span>
                )}
                <span className="font-semibold text-slate-200">{awayName}</span>
              </div>
              <span
                className={`rounded-full px-2 py-0.5 text-[9px] font-bold ${
                  isLive ? "bg-red-500 text-white animate-pulse" : "bg-slate-700 text-slate-300"
                }`}
              >
                {isLive ? (m.live_minute_label || "مباشر") : (m.kickoff_time_local || "اليوم")}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}

function SmartLinksToolbar({ onTabChange }) {
  const [copied, setCopied] = useState(false);

  function copyMatchLink() {
    if (typeof window !== "undefined") {
      try {
        navigator.clipboard?.writeText(window.location.href);
        setCopied(true);
        setTimeout(() => setCopied(false), 2500);
      } catch (e) {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <a
        href="https://kora-live-to.blogspot.com"
        target="_blank"
        rel="noopener noreferrer"
        data-testid="detail-blogger-link"
        className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 text-xs font-bold text-emerald-600 hover:bg-emerald-500/20 dark:text-emerald-400 transition"
      >
        <span>🌐</span>
        جدول المباريات (Blogger) ↗
      </a>

      <button
        type="button"
        onClick={() => onTabChange("standings")}
        className="inline-flex items-center gap-1.5 rounded-full border border-sky-500/40 bg-sky-500/10 px-3 py-1 text-xs font-bold text-sky-400 hover:bg-sky-500/20 transition"
      >
        <span>📊</span>
        ترتيب البطولة
      </button>

      <button
        type="button"
        onClick={() => onTabChange("lineup")}
        className="inline-flex items-center gap-1.5 rounded-full border border-purple-500/40 bg-purple-500/10 px-3 py-1 text-xs font-bold text-purple-300 hover:bg-purple-500/20 transition"
      >
        <span>⚔️</span>
        التشكيلة والتكتيك
      </button>

      <button
        type="button"
        onClick={copyMatchLink}
        className="inline-flex items-center gap-1.5 rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-xs font-bold text-amber-300 hover:bg-amber-500/20 transition"
      >
        <span>{copied ? "✓" : "📢"}</span>
        {copied ? "تم نسخ الرابط!" : "مشاركة البث"}
      </button>
    </div>
  );
}

export default function MatchDetailHybrid({
  detail,
  onBack,
  onSelectMatch,
  todayMatches = [],
}) {
  const [activeTab, setActiveTab] = useState("summary");
  const [liveSlate, setLiveSlate] = useState(todayMatches);

  const {
    match,
    servers,
    home_lineup,
    away_lineup,
    home_formation,
    away_formation,
    events,
    stats,
    standings,
  } = detail;

  useEffect(() => {
    if (todayMatches && todayMatches.length > 0) {
      setLiveSlate(todayMatches);
      return;
    }
    let isMounted = true;
    fetchTodayMatches({ date: localDateForOffset(0) })
      .then((res) => {
        if (isMounted && res?.matches) {
          setLiveSlate(res.matches);
        }
      })
      .catch(() => {});
    return () => {
      isMounted = false;
    };
  }, [todayMatches, match.id]);

  function handleBack() {
    if (typeof document !== "undefined" && document.referrer && document.referrer.includes("blogspot.com")) {
      window.location.href = document.referrer;
      return;
    }
    onBack();
  }

  function handleSmartTabChange(tabId) {
    setActiveTab(tabId);
    const tabsEl = document.getElementById("match-tabs-section");
    if (tabsEl) {
      tabsEl.scrollIntoView({ behavior: "smooth" });
    }
  }

  return (
    <div dir="rtl" data-testid="match-detail" className="space-y-4">
      {/* 1. Navigation & Smart Links Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <button
          type="button"
          onClick={handleBack}
          data-testid="back-button"
          className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3.5 py-1.5 text-xs font-bold text-slate-600 transition hover:border-brand/50 hover:text-brand dark:border-slate-700 dark:bg-surface-dark dark:text-slate-300"
        >
          <span aria-hidden="true">→</span>
          العودة إلى جدول المباريات
        </button>

        <SmartLinksToolbar onTabChange={handleSmartTabChange} />
      </div>

      {/* 2. Live Matches Quick Switcher Bar */}
      <LiveMatchesSwitcher
        matches={liveSlate}
        currentMatchId={match.id}
        onSelectMatch={onSelectMatch}
      />

      {/* 3. Match Header Card */}
      <header className="overflow-hidden rounded-3xl border border-slate-800/60 bg-gradient-to-br from-slate-900 via-slate-900 to-brand/30 p-4 shadow-player sm:p-6">
        <p className="mb-3 text-center text-[11px] font-semibold text-slate-300 sm:text-xs">
          {match.league?.name_ar}
          {match.league?.round ? ` • ${match.league.round}` : ""}
        </p>
        <div className="flex items-center gap-2 sm:gap-6">
          <TeamBlock team={match.home_team} />
          <div className="shrink-0">
            <HeaderStatus match={match} />
          </div>
          <TeamBlock team={match.away_team} />
        </div>
        <p className="mt-3 text-center text-[11px] text-slate-400">
          {match.competition_subtitle}
          {match.kickoff_date_local ? ` • ${match.kickoff_time_local}` : ""}
          {match.channel ? ` • 📺 ${match.channel}` : ""}
        </p>
      </header>

      {match.status === "SCHEDULED" && (
        <div className="flex items-center justify-between rounded-2xl border border-sky-500/30 bg-sky-500/10 px-4 py-2.5 text-xs text-sky-200">
          <div className="flex items-center gap-2">
            <span className="text-base">📺</span>
            <span className="font-bold">
              البث المباشر المخصص للمباراة سيبدأ قبل صافرة البداية بـ 30 دقيقة • يعرض المشغل حالياً تغطية القناة الناقلة
            </span>
          </div>
          <span className="hidden font-mono text-[11px] text-sky-300 sm:inline">
            {match.channel || "beIN SPORTS"}
          </span>
        </div>
      )}

      {/* 4. Stream Player */}
      <StreamPlayerContainer
        servers={servers}
        channel={match.channel}
        commentator={match.commentator}
      />

      {/* 5. Match Description & Broadcast Details */}
      <MatchDescriptionCard match={match} />

      {(match.stadium || match.referee) && (
        <div className="flex flex-wrap items-center gap-2 text-[11px] font-semibold text-slate-500 dark:text-slate-400">
          {match.stadium && (
            <span className="rounded-full bg-slate-100 px-3 py-1 dark:bg-surface-dark-raised">
              الملعب: {match.stadium}
            </span>
          )}
          {match.referee && (
            <span className="rounded-full bg-slate-100 px-3 py-1 dark:bg-surface-dark-raised">
              الحكم: {match.referee}
            </span>
          )}
        </div>
      )}

      {/* 6. Center Tabs Section */}
      <section id="match-tabs-section" className="glass-card overflow-hidden rounded-3xl">
        <div
          role="tablist"
          aria-label="مركز المباراة"
          className="no-scrollbar flex items-center gap-1 overflow-x-auto border-b border-slate-200/70 p-2 dark:border-slate-700/60"
        >
          {TABS.map((tab) => {
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={active}
                data-testid={`tab-${tab.id}`}
                onClick={() => setActiveTab(tab.id)}
                className={[
                  "whitespace-nowrap rounded-xl px-4 py-2 text-xs font-bold transition sm:text-sm",
                  active
                    ? "bg-brand text-white shadow-sm shadow-brand/30"
                    : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-surface-dark-raised",
                ].join(" ")}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        <div className="p-3 sm:p-4" role="tabpanel">
          {activeTab === "summary" && <Timeline events={events} />}
          {activeTab === "lineup" && (
            <TacticalPitchView
              homeLineup={home_lineup}
              awayLineup={away_lineup}
              homeTeamName={match.home_team?.name_ar}
              awayTeamName={match.away_team?.name_ar}
              homeFormation={home_formation}
              awayFormation={away_formation}
            />
          )}
          {activeTab === "stats" && <StatsPanel stats={stats} />}
          {activeTab === "standings" && <StandingsTable rows={standings} />}
        </div>
      </section>
    </div>
  );
}
