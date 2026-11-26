export const LIVE_STATUSES = new Set([
  "IN_PLAY",
  "HALFTIME",
  "EXTRA_TIME",
  "PENALTIES",
]);

export function isLiveStatus(status) {
  return LIVE_STATUSES.has(status);
}

export function teamInitial(name) {
  const clean = (name || "").trim();
  return clean ? clean[0] : "؟";
}

export function formatCountdown(seconds) {
  if (seconds === null || seconds === undefined || Number.isNaN(Number(seconds))) {
    return null;
  }
  const total = Math.max(0, Math.floor(Number(seconds)));
  const hours = String(Math.floor(total / 3600)).padStart(2, "0");
  const minutes = String(Math.floor((total % 3600) / 60)).padStart(2, "0");
  const secs = String(total % 60).padStart(2, "0");
  return `${hours}:${minutes}:${secs}`;
}

export function liveMinuteLabel(match) {
  if (!isLiveStatus(match?.status)) return null;
  if (match.live_minute_label) return match.live_minute_label;
  if (match.status === "HALFTIME") return "استراحة";
  if (match.status === "PENALTIES") return "ركلات الترجيح";
  return match.elapsed_time != null ? `${match.elapsed_time}'` : "مباشر";
}

export function deriveFormation(players = []) {
  const count = (position) =>
    players.filter((player) => player.position === position).length;
  const parts = [count("DF"), count("MF"), count("FW")].filter((value) => value > 0);
  return parts.length ? parts.join("-") : "—";
}
