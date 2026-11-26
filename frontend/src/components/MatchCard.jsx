import { formatCountdown, isLiveStatus, liveMinuteLabel, teamInitial } from "../lib/format";
import { useCountdown } from "../lib/useCountdown";

function TeamSide({ team, testId }) {
  return (
    <div
      data-testid={testId}
      className="flex flex-1 flex-col items-center gap-1.5 text-center"
    >
      {team.logo_url ? (
        <img
          src={team.logo_url}
          alt=""
          className="h-11 w-11 rounded-full object-contain"
          loading="lazy"
          onError={(e) => {
            e.currentTarget.onerror = null;
            e.currentTarget.src = "https://cdn-icons-png.flaticon.com/512/53/53283.png";
          }}
        />
      ) : (
        <span
          aria-hidden="true"
          className="flex h-11 w-11 items-center justify-center rounded-full bg-slate-100 text-base font-extrabold text-slate-600 dark:bg-surface-dark-raised dark:text-slate-200"
        >
          {teamInitial(team.name_ar)}
        </span>
      )}
      <span className="line-clamp-2 text-xs font-bold leading-5 text-slate-800 dark:text-slate-100 sm:text-sm">
        {team.name_ar}
      </span>
    </div>
  );
}

function Score({ match }) {
  return (
    <div
      data-testid="score"
      dir="ltr"
      className="flex items-center gap-2 font-latin text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white sm:text-[28px]"
    >
      <span>{match.home_score ?? 0}</span>
      <span className="text-slate-300 dark:text-slate-600">-</span>
      <span>{match.away_score ?? 0}</span>
    </div>
  );
}

export default function MatchCard({ match, onSelect }) {
  const live = isLiveStatus(match.status);
  const halftime = match.status === "HALFTIME";
  const scheduled = match.status === "SCHEDULED";
  const finished = match.status === "FINISHED";
  const postponed = match.status === "POSTPONED";
  const minute = liveMinuteLabel(match);
  const remainingSeconds = useCountdown(match.countdown_seconds);
  const countdown = formatCountdown(remainingSeconds);

  function select() {
    if (typeof onSelect === "function") onSelect(match);
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      select();
    }
  }

  return (
    <article
      dir="rtl"
      role="button"
      tabIndex={0}
      aria-label={`${match.home_team.name_ar} ضد ${match.away_team.name_ar}`}
      data-testid={`match-card-${match.id}`}
      data-status={match.status}
      onClick={select}
      onKeyDown={handleKeyDown}
      className="group w-full cursor-pointer rounded-2xl border border-slate-200/80 bg-white/95 p-3 shadow-card outline-none transition duration-200 hover:-translate-y-0.5 hover:border-brand/40 hover:shadow-card-hover focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-transparent dark:border-slate-700/60 dark:bg-surface-dark/95 sm:p-4"
    >
      <div className="flex items-center gap-2 sm:gap-4">
        <TeamSide team={match.home_team} testId="home-team" />

        <div
          data-testid="match-center"
          className="flex min-w-[140px] flex-1 flex-col items-center justify-center gap-1.5"
        >
          {live && (
            <>
              <Score match={match} />
              {halftime ? (
                <span
                  data-testid="halftime-badge"
                  className="inline-flex items-center gap-1.5 rounded-full bg-amber-500 px-2.5 py-1 text-[11px] font-bold text-white shadow-sm sm:text-xs"
                >
                  استراحة
                </span>
              ) : (
                <span
                  data-testid="live-badge"
                  className="animate-live-pulse inline-flex items-center gap-1.5 rounded-full bg-live px-2.5 py-1 text-[11px] font-bold text-white shadow-sm sm:text-xs"
                >
                  <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-white" />
                  مباشر الآن {minute ? `(${minute})` : ""}
                </span>
              )}
            </>
          )}

          {scheduled && (
            <>
              <span
                dir="ltr"
                className="font-latin text-xl font-extrabold text-slate-900 dark:text-white sm:text-2xl"
              >
                {match.kickoff_time_local}
              </span>
              {countdown && (
                <span
                  data-testid="countdown-badge"
                  className="rounded-full bg-countdown-soft px-2.5 py-1 text-[11px] font-bold text-countdown sm:text-xs"
                >
                  تبدأ بعد: <span dir="ltr" className="font-latin">{countdown}</span>
                </span>
              )}
            </>
          )}

          {finished && (
            <>
              <Score match={match} />
              <span
                data-testid="finished-badge"
                className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-bold text-slate-600 dark:bg-surface-dark-raised dark:text-slate-300 sm:text-xs"
              >
                انتهت
              </span>
            </>
          )}

          {postponed && (
            <span
              data-testid="postponed-badge"
              className="rounded-full bg-amber-100 px-2.5 py-1 text-[11px] font-bold text-amber-700 dark:bg-amber-500/15 dark:text-amber-300 sm:text-xs"
            >
              مؤجلة
            </span>
          )}

          <div className="flex flex-wrap items-center justify-center gap-1.5 text-center text-[10px] font-medium leading-4 text-slate-500 dark:text-slate-400 sm:text-xs">
            <span>{match.competition_subtitle}</span>
            {match.channel && (
              <>
                <span className="text-slate-300 dark:text-slate-600" aria-hidden="true">•</span>
                <span
                  data-testid="match-channel"
                  className="inline-flex items-center gap-1 font-semibold text-slate-700 dark:text-slate-300"
                >
                  <span aria-hidden="true">📺</span>
                  <span>{match.channel}</span>
                </span>
              </>
            )}
          </div>

          {!finished && !postponed && (
            <div className="pt-0.5">
              {match.has_stream ? (
                <span
                  data-testid="stream-status"
                  className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[9px] font-bold text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300"
                >
                  <span aria-hidden="true">🟢</span>
                  <span>البث المباشر متاح</span>
                </span>
              ) : (
                <span
                  data-testid="stream-status"
                  className="inline-flex items-center gap-1 text-[9px] font-medium text-slate-400 dark:text-slate-500"
                >
                  <span aria-hidden="true">⏳</span>
                  <span>سيتم تحديث روابط البث قبل انطلاق المباراة</span>
                </span>
              )}
            </div>
          )}

          {match.is_admin_override && (
            <span className="text-[10px] font-semibold text-brand">
              تعديل إداري
            </span>
          )}
        </div>

        <TeamSide team={match.away_team} testId="away-team" />
      </div>
    </article>
  );
}
