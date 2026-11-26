const API_BASE = (import.meta.env?.VITE_API_BASE_URL || "").replace(/\/$/, "");

/** The schedule is always presented in Mecca time, matching the API default. */
export const DISPLAY_TIMEZONE = "Asia/Riyadh";

export const SUPPORTED_TIMEZONES = [
  { id: "Asia/Riyadh", labelAr: "مكة المكرمة (GMT+3)" },
  { id: "Africa/Cairo", labelAr: "القاهرة (GMT+2)" },
  { id: "Africa/Casablanca", labelAr: "المغرب (GMT+1)" },
  { id: "Asia/Dubai", labelAr: "الإمارات (GMT+4)" },
  { id: "Europe/London", labelAr: "لندن (GMT+0)" },
  { id: "UTC", labelAr: "التوقيت العالمي (UTC)" },
];

const TIMEZONE_LABELS_AR = {
  "Asia/Riyadh": "بتوقيت مكة المكرمة",
  "Africa/Casablanca": "بتوقيت المغرب",
  "Africa/Cairo": "بتوقيت القاهرة",
  "Asia/Dubai": "بتوقيت الإمارات",
  "Europe/London": "بتوقيت لندن",
  UTC: "بالتوقيت العالمي",
};

async function getJson(path, signal) {
  const response = await fetch(`${API_BASE}${path}`, {
    signal,
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const payload = await response.json();
      if (payload?.detail) message = payload.detail;
    } catch {
      // Keep the status-based message.
    }
    throw new Error(message);
  }

  return response.json();
}

async function fetchStaticMatchesPayload(signal) {
  try {
    const response = await fetch("/data/matches.json", {
      signal,
      headers: { Accept: "application/json" },
    });
    if (!response.ok) return null;
    const payload = await response.json();
    return Array.isArray(payload?.matches) ? payload : null;
  } catch (error) {
    if (error?.name === "AbortError" || signal?.aborted) {
      throw error;
    }
    return null;
  }
}

function formatMatchForTimezone(match, tz) {
  if (!tz || !match?.kickoff_time_utc) return match;
  const parsed = new Date(match.kickoff_time_utc);
  if (Number.isNaN(parsed.getTime())) return match;
  try {
    const localDate = localDateForOffset(0, { timeZone: tz, now: parsed });
    const localTime = new Intl.DateTimeFormat("en-US", {
      timeZone: tz,
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    }).format(parsed);
    return {
      ...match,
      kickoff_date_local: localDate,
      kickoff_time_local: localTime,
    };
  } catch {
    return match;
  }
}

function normalizeStaticSlate(payload, { date, tz } = {}) {
  const rawMatches = Array.isArray(payload?.matches) ? payload.matches : [];
  const localized = tz ? rawMatches.map((match) => formatMatchForTimezone(match, tz)) : rawMatches;

  let filtered = localized;
  if (date) {
    const hasDateMetadata = localized.some((match) => Boolean(match?.kickoff_date_local));
    if (hasDateMetadata) {
      const matched = localized.filter(
        (match) => !match?.kickoff_date_local || match.kickoff_date_local === date,
      );
      if (matched.length > 0) {
        filtered = matched;
      } else if (payload?.date) {
        const diffMs = Math.abs(Date.parse(date) - Date.parse(payload.date));
        // Within a 2-day window around the static snapshot date, 0 matches means an empty day slate.
        if (!Number.isNaN(diffMs) && diffMs <= 2 * 86_400_000) {
          filtered = [];
        }
      }
    }
  }

  return {
    ...payload,
    date: date || payload?.date || null,
    timezone: tz || payload?.timezone || DISPLAY_TIMEZONE,
    timezone_label_ar:
      (tz && TIMEZONE_LABELS_AR[tz]) ||
      payload?.timezone_label_ar ||
      TIMEZONE_LABELS_AR[DISPLAY_TIMEZONE],
    matches: filtered,
  };
}

export async function fetchTodayMatches({ date, tz, signal } = {}) {
  const staticPayload = await fetchStaticMatchesPayload(signal);
  if (staticPayload) {
    return normalizeStaticSlate(staticPayload, { date, tz });
  }

  const params = new URLSearchParams();
  if (date) params.set("date", date);
  if (tz) params.set("tz", tz);
  const query = params.toString();
  return getJson(`/api/v1/matches/today${query ? `?${query}` : ""}`, signal);
}

export async function fetchMatchDetail(matchId, { tz, signal } = {}) {
  const staticPayload = await fetchStaticMatchesPayload(signal);
  if (staticPayload) {
    const found = staticPayload.matches.find((item) => String(item?.id) === String(matchId));
    if (found && Array.isArray(found.servers)) {
      return {
        match: formatMatchForTimezone(found, tz),
        servers: found.servers || [],
        home_lineup: found.home_lineup || [],
        away_lineup: found.away_lineup || [],
        home_formation: found.home_formation || "—",
        away_formation: found.away_formation || "—",
        events: found.events || [],
        stats: found.stats || [],
        standings: found.standings || [],
      };
    }
  }

  const params = new URLSearchParams();
  if (tz) params.set("tz", tz);
  const query = params.toString();
  return getJson(`/api/v1/matches/${encodeURIComponent(matchId)}${query ? `?${query}` : ""}`, signal);
}

export function localDateForOffset(
  offsetDays = 0,
  { timeZone = DISPLAY_TIMEZONE, now = new Date() } = {},
) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(now);
  const get = (type) => Number(parts.find((part) => part.type === type)?.value);

  // Shift the calendar date in UTC so DST transitions cannot skew the result.
  const shifted = new Date(Date.UTC(get("year"), get("month") - 1, get("day") + offsetDays));
  return shifted.toISOString().slice(0, 10);
}

// ---------------------------------------------------------------------------
// Admin CMS API helpers
// ---------------------------------------------------------------------------

async function sendAdminJson(path, token, method = "POST", body = null) {
  const headers = {
    Accept: "application/json",
    "X-Admin-Token": token,
  };
  const options = { method, headers };
  if (body) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const payload = await response.json();
      if (payload?.detail) message = payload.detail;
    } catch {
      // Keep the status-based message.
    }
    throw new Error(message);
  }
  return response.json();
}

export async function fetchAdminMatches(token, { date, tz, q, signal } = {}) {
  const params = new URLSearchParams();
  if (date) params.set("date", date);
  if (tz) params.set("tz", tz);
  if (q) params.set("q", q);
  const query = params.toString();
  const response = await fetch(`${API_BASE}/api/v1/admin/matches${query ? `?${query}` : ""}`, {
    signal,
    headers: {
      Accept: "application/json",
      "X-Admin-Token": token,
    },
  });
  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const payload = await response.json();
      if (payload?.detail) message = payload.detail;
    } catch {
      // Keep the status-based message.
    }
    throw new Error(message);
  }
  return response.json();
}

export function saveAdminOverride(token, matchId, override) {
  return sendAdminJson(`/api/v1/admin/matches/${encodeURIComponent(matchId)}/override`, token, "POST", override);
}

export function clearAdminOverride(token, matchId) {
  return sendAdminJson(`/api/v1/admin/matches/${encodeURIComponent(matchId)}/override`, token, "DELETE");
}

export function upsertAdminStream(token, matchId, stream) {
  return sendAdminJson(`/api/v1/admin/matches/${encodeURIComponent(matchId)}/streams`, token, "POST", stream);
}

export function deleteAdminStream(token, matchId, serverId) {
  return sendAdminJson(
    `/api/v1/admin/matches/${encodeURIComponent(matchId)}/streams/${encodeURIComponent(serverId)}`,
    token,
    "DELETE",
  );
}

// ---------------------------------------------------------------------------
// Ads API helpers (Public & Admin)
// ---------------------------------------------------------------------------

export function fetchActiveAds({ position, device, signal } = {}) {
  const params = new URLSearchParams();
  if (position) params.set("position", position);
  if (device) params.set("device", device);
  const query = params.toString();
  return getJson(`/api/v1/ads${query ? `?${query}` : ""}`, signal);
}

export async function fetchAdminAds(token, { position, signal } = {}) {
  const params = new URLSearchParams();
  if (position) params.set("position", position);
  const query = params.toString();
  const response = await fetch(`${API_BASE}/api/v1/admin/ads${query ? `?${query}` : ""}`, {
    signal,
    headers: {
      Accept: "application/json",
      "X-Admin-Token": token,
    },
  });
  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const payload = await response.json();
      if (payload?.detail) message = payload.detail;
    } catch {
      // Keep status-based message
    }
    throw new Error(message);
  }
  return response.json();
}

export function createAdminAd(token, payload) {
  return sendAdminJson("/api/v1/admin/ads", token, "POST", payload);
}

export function updateAdminAd(token, adId, payload) {
  return sendAdminJson(`/api/v1/admin/ads/${encodeURIComponent(adId)}`, token, "PUT", payload);
}

export function toggleAdminAd(token, adId) {
  return sendAdminJson(`/api/v1/admin/ads/${encodeURIComponent(adId)}/toggle`, token, "PATCH");
}

export function deleteAdminAd(token, adId) {
  return sendAdminJson(`/api/v1/admin/ads/${encodeURIComponent(adId)}`, token, "DELETE");
}

// ---------------------------------------------------------------------------
// Site Analytics & Statistics helpers (Public Tracking & Admin Stats)
// ---------------------------------------------------------------------------

export async function trackSiteVisit(payload = {}) {
  try {
    await fetch(`${API_BASE}/api/v1/analytics/track`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
  } catch {
    // Non-blocking telemetry
  }
}

export async function fetchAdminAnalytics(token, { period = "week", signal } = {}) {
  const response = await fetch(
    `${API_BASE}/api/v1/admin/analytics/stats?period=${encodeURIComponent(period)}`,
    {
      signal,
      headers: {
        Accept: "application/json",
        "X-Admin-Token": token,
      },
    },
  );
  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const payload = await response.json();
      if (payload?.detail) message = payload.detail;
    } catch {
      // Keep status-based message
    }
    throw new Error(message);
  }
  return response.json();
}

export async function fetchAdminMatchArticle(token, matchId, baseUrl = "") {
  const query = baseUrl ? `?base_url=${encodeURIComponent(baseUrl)}` : "";
  const response = await fetch(
    `${API_BASE}/api/v1/admin/matches/${encodeURIComponent(matchId)}/article${query}`,
    {
      headers: {
        Accept: "application/json",
        "X-Admin-Token": token,
      },
    },
  );
  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const payload = await response.json();
      if (payload?.detail) message = payload.detail;
    } catch {}
    throw new Error(message);
  }
  return response.json();
}

export { API_BASE };
