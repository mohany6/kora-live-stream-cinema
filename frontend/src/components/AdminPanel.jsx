import { useEffect, useState } from "react";

import {
  clearAdminOverride,
  createAdminAd,
  deleteAdminAd,
  deleteAdminStream,
  fetchAdminAds,
  fetchAdminAnalytics,
  fetchAdminMatchArticle,
  fetchAdminMatches,
  localDateForOffset,
  saveAdminOverride,
  toggleAdminAd,
  updateAdminAd,
  upsertAdminStream,
} from "../lib/api";

const TOKEN_STORAGE_KEY = "kora-admin-token";

const STATUS_OPTIONS = [
  { value: "SCHEDULED", label: "لم تبدأ (SCHEDULED)" },
  { value: "IN_PLAY", label: "مباشر الآن (IN_PLAY)" },
  { value: "HALFTIME", label: "استراحة بين الشوطين (HALFTIME)" },
  { value: "EXTRA_TIME", label: "شوط إضافي (EXTRA_TIME)" },
  { value: "PENALTIES", label: "ركلات الترجيح (PENALTIES)" },
  { value: "FINISHED", label: "انتهت (FINISHED)" },
  { value: "POSTPONED", label: "مؤجلة (POSTPONED)" },
];

const AD_POSITIONS = [
  { id: "all", label: "الكل" },
  { id: "header_top", label: "ليدربورد علوي" },
  { id: "in_feed", label: "بين المباريات" },
  { id: "player_top", label: "أعلى المشغل" },
  { id: "player_bottom", label: "أسفل المشغل" },
  { id: "sticky_bottom", label: "شريط عائم سفلي" },
];

export default function AdminPanel({ onClose, timezone = "Asia/Riyadh", onMatchUpdated }) {
  const [token, setToken] = useState(() => {
    return typeof window !== "undefined"
      ? window.sessionStorage.getItem(TOKEN_STORAGE_KEY) || ""
      : "";
  });
  const [tokenInput, setTokenInput] = useState("");
  const [authError, setAuthError] = useState(null);

  // Cockpit Navigation Tab
  const [adminTab, setAdminTab] = useState("matches"); // "matches" | "ads" | "overview"

  // Matches State
  const [dateFilter, setDateFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState(null);

  const [selectedMatchId, setSelectedMatchId] = useState(null);
  const [actionSuccess, setActionSuccess] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [copyingArticle, setCopyingArticle] = useState(false);

  // Override form state
  const [overrideHomeScore, setOverrideHomeScore] = useState("");
  const [overrideAwayScore, setOverrideAwayScore] = useState("");
  const [overrideStatus, setOverrideStatus] = useState("IN_PLAY");
  const [overrideElapsed, setOverrideElapsed] = useState("");
  const [overrideChannel, setOverrideChannel] = useState("");
  const [overrideCommentator, setOverrideCommentator] = useState("");
  const [overrideStadium, setOverrideStadium] = useState("");
  const [overrideReferee, setOverrideReferee] = useState("");

  // Stream form state
  const [streamName, setStreamName] = useState("");
  const [streamUrl, setStreamUrl] = useState("");
  const [streamType, setStreamType] = useState("iframe");
  const [streamQuality, setStreamQuality] = useState("");
  const [streamActive, setStreamActive] = useState(true);

  // Ads CMS State
  const [ads, setAds] = useState([]);
  const [adsLoading, setAdsLoading] = useState(false);
  const [adsError, setAdsError] = useState(null);
  const [adPositionFilter, setAdPositionFilter] = useState("all");
  const [showAdModal, setShowAdModal] = useState(false);
  const [editingAdId, setEditingAdId] = useState(null);
  const [adSuccessMsg, setAdSuccessMsg] = useState(null);
  const [adErrorMsg, setAdErrorMsg] = useState(null);

  // Ad Form State
  const [adFormTitle, setAdFormTitle] = useState("");
  const [adFormPosition, setAdFormPosition] = useState("header_top");
  const [adFormType, setAdFormType] = useState("image_banner");
  const [adFormImageUrl, setAdFormImageUrl] = useState("");
  const [adFormLinkUrl, setAdFormLinkUrl] = useState("");
  const [adFormHtmlCode, setAdFormHtmlCode] = useState("");
  const [adFormTargetDevice, setAdFormTargetDevice] = useState("all");
  const [adFormIsActive, setAdFormIsActive] = useState(true);
  const [adFormPriority, setAdFormPriority] = useState(0);

  // Analytics State
  const [analyticsPeriod, setAnalyticsPeriod] = useState("week"); // "day" | "week" | "month" | "year"
  const [analyticsData, setAnalyticsData] = useState(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analyticsError, setAnalyticsError] = useState(null);

  const selectedItem = matches.find((m) => m.match.id === selectedMatchId) || null;

  function loadMatches(activeToken = token) {
    if (!activeToken) return;
    setLoading(true);
    setLoadError(null);

    let dateParam = null;
    if (dateFilter === "today") dateParam = localDateForOffset(0, { timeZone: timezone });
    else if (dateFilter === "yesterday") dateParam = localDateForOffset(-1, { timeZone: timezone });
    else if (dateFilter === "tomorrow") dateParam = localDateForOffset(1, { timeZone: timezone });

    fetchAdminMatches(activeToken, {
      date: dateParam,
      tz: timezone,
      q: searchQuery || undefined,
    })
      .then((data) => {
        setMatches(data.matches || []);
        setAuthError(null);
      })
      .catch((err) => {
        if (err.message && err.message.includes("401")) {
          setAuthError("رمز الإدارة غير صحيح أو منتهي الصلاحية");
          setToken("");
          window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);
        } else {
          setLoadError(err.message || "تعذر تحميل قائمة المباريات");
        }
      })
      .finally(() => setLoading(false));
  }

  function loadAds(activeToken = token) {
    if (!activeToken) return;
    setAdsLoading(true);
    setAdsError(null);

    const posParam = adPositionFilter !== "all" ? adPositionFilter : undefined;
    fetchAdminAds(activeToken, { position: posParam })
      .then((data) => {
        setAds(data.ads || []);
      })
      .catch((err) => {
        setAdsError(err.message || "تعذر تحميل الإعلانات");
      })
      .finally(() => setAdsLoading(false));
  }

  function loadAnalytics(activeToken = token, period = analyticsPeriod) {
    if (!activeToken) return;
    setAnalyticsLoading(true);
    setAnalyticsError(null);

    fetchAdminAnalytics(activeToken, { period })
      .then((data) => {
        setAnalyticsData(data);
      })
      .catch((err) => {
        setAnalyticsError(err.message || "تعذر تحميل إحصائيات المنصة");
      })
      .finally(() => setAnalyticsLoading(false));
  }

  useEffect(() => {
    if (token) {
      loadMatches(token);
      loadAds(token);
      loadAnalytics(token, analyticsPeriod);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, dateFilter, searchQuery, timezone, adPositionFilter, analyticsPeriod]);

  // Sync override form fields when selected match changes
  useEffect(() => {
    if (selectedItem) {
      const match = selectedItem.match;
      const ov = selectedItem.override || {};
      setOverrideHomeScore(
        ov.home_score !== undefined ? String(ov.home_score) : String(match.home_score ?? 0),
      );
      setOverrideAwayScore(
        ov.away_score !== undefined ? String(ov.away_score) : String(match.away_score ?? 0),
      );
      setOverrideStatus(ov.status || match.status || "IN_PLAY");
      setOverrideElapsed(
        ov.elapsed_time !== undefined
          ? String(ov.elapsed_time)
          : match.elapsed_time != null
            ? String(match.elapsed_time)
            : "",
      );
      setOverrideChannel(ov.channel ?? match.channel ?? "");
      setOverrideCommentator(ov.commentator ?? match.commentator ?? "");
      setOverrideStadium(ov.stadium ?? match.stadium ?? "");
      setOverrideReferee(ov.referee ?? match.referee ?? "");
      setActionSuccess(null);
      setActionError(null);
    }
  }, [selectedMatchId, selectedItem]);

  function handleLogin(e) {
    e?.preventDefault();
    if (!tokenInput.trim()) return;
    setAuthError(null);
    setLoading(true);

    fetchAdminMatches(tokenInput.trim(), { tz: timezone })
      .then((data) => {
        const clean = tokenInput.trim();
        setToken(clean);
        window.sessionStorage.setItem(TOKEN_STORAGE_KEY, clean);
        setMatches(data.matches || []);
        loadAds(clean);
        loadAnalytics(clean, analyticsPeriod);
      })
      .catch(() => {
        setAuthError("رمز الإدارة غير صالح (401)");
      })
      .finally(() => setLoading(false));
  }

  function handleLogout() {
    setToken("");
    window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    setMatches([]);
    setAds([]);
    setAnalyticsData(null);
    setSelectedMatchId(null);
  }

  async function handleCopyArticle(matchId) {
    if (!matchId) return;
    setCopyingArticle(true);
    setActionSuccess(null);
    setActionError(null);
    try {
      const currentOrigin = typeof window !== "undefined" ? window.location.origin : "";
      const data = await fetchAdminMatchArticle(token, matchId, currentOrigin);
      if (data?.content) {
        let copied = false;
        if (navigator.clipboard?.writeText) {
          try {
            await navigator.clipboard.writeText(data.content);
            copied = true;
          } catch {
            // Fall through to textarea execCommand fallback
          }
        }
        if (!copied) {
          const textArea = document.createElement("textarea");
          textArea.value = data.content;
          textArea.style.position = "fixed";
          textArea.style.left = "-9999px";
          document.body.appendChild(textArea);
          textArea.focus();
          textArea.select();
          copied = document.execCommand("copy");
          document.body.removeChild(textArea);
        }
        setActionSuccess("تم نسخ مقال Blogger بتنسيق Schema.org والأزرار بنجاح! الصقه في محرر التدوينة.");
      } else {
        setActionError("تعذر استخراج مقال المباراة.");
      }
    } catch (err) {
      setActionError(err.message || "فشل توليد مقال المباراة.");
    } finally {
      setCopyingArticle(false);
    }
  }

  async function handleSaveOverride(e) {
    e?.preventDefault();
    if (!selectedItem) return;
    setActionError(null);
    setActionSuccess(null);

    const payload = {};
    if (overrideHomeScore !== "") payload.home_score = parseInt(overrideHomeScore, 10);
    if (overrideAwayScore !== "") payload.away_score = parseInt(overrideAwayScore, 10);
    if (overrideStatus) payload.status = overrideStatus;
    if (overrideElapsed !== "") payload.elapsed_time = parseInt(overrideElapsed, 10);
    if (overrideChannel !== "") payload.channel = overrideChannel;
    if (overrideCommentator !== "") payload.commentator = overrideCommentator;
    if (overrideStadium !== "") payload.stadium = overrideStadium;
    if (overrideReferee !== "") payload.referee = overrideReferee;

    try {
      await saveAdminOverride(token, selectedItem.match.id, payload);
      setActionSuccess("تم حفظ التعديل اليدوي بنجاح!");
      loadMatches();
      if (typeof onMatchUpdated === "function") onMatchUpdated();
    } catch (err) {
      setActionError(err.message || "تعذر حفظ التعديل");
    }
  }

  async function handleClearOverride() {
    if (!selectedItem) return;
    setActionError(null);
    setActionSuccess(null);

    try {
      await clearAdminOverride(token, selectedItem.match.id);
      setActionSuccess("تم إلغاء التعديل اليدوي واستعادة بيانات المصدر!");
      loadMatches();
      if (typeof onMatchUpdated === "function") onMatchUpdated();
    } catch (err) {
      setActionError(err.message || "تعذر إلغاء التعديل");
    }
  }

  async function handleAddStream(e) {
    e?.preventDefault();
    if (!selectedItem || !streamUrl.trim() || !streamName.trim()) return;
    setActionError(null);
    setActionSuccess(null);

    const payload = {
      server_name: streamName.trim(),
      url: streamUrl.trim(),
      type: streamType,
      quality: streamQuality.trim() || null,
      is_active: streamActive,
    };

    try {
      await upsertAdminStream(token, selectedItem.match.id, payload);
      setActionSuccess("تمت إضافة سيرفر البث بنجاح!");
      setStreamName("");
      setStreamUrl("");
      setStreamQuality("");
      loadMatches();
      if (typeof onMatchUpdated === "function") onMatchUpdated();
    } catch (err) {
      setActionError(err.message || "تعذر إضافة سيرفر البث");
    }
  }

  async function handleDeleteStream(serverId) {
    if (!selectedItem) return;
    setActionError(null);
    setActionSuccess(null);

    try {
      await deleteAdminStream(token, selectedItem.match.id, serverId);
      setActionSuccess("تم حذف سيرفر البث بنجاح!");
      loadMatches();
      if (typeof onMatchUpdated === "function") onMatchUpdated();
    } catch (err) {
      setActionError(err.message || "تعذر حذف السيرفر");
    }
  }

  // --- Ads CMS Actions ---

  function resetAdForm() {
    setAdFormTitle("");
    setAdFormPosition("header_top");
    setAdFormType("image_banner");
    setAdFormImageUrl("");
    setAdFormLinkUrl("");
    setAdFormHtmlCode("");
    setAdFormTargetDevice("all");
    setAdFormIsActive(true);
    setAdFormPriority(0);
    setEditingAdId(null);
  }

  function handleOpenCreateAd() {
    resetAdForm();
    setAdSuccessMsg(null);
    setAdErrorMsg(null);
    setShowAdModal(true);
  }

  function handleOpenEditAd(ad) {
    setEditingAdId(ad.id);
    setAdFormTitle(ad.title || "");
    setAdFormPosition(ad.position || "header_top");
    setAdFormType(ad.ad_type || "image_banner");
    setAdFormImageUrl(ad.image_url || "");
    setAdFormLinkUrl(ad.link_url || "");
    setAdFormHtmlCode(ad.html_code || "");
    setAdFormTargetDevice(ad.target_device || "all");
    setAdFormIsActive(Boolean(ad.is_active));
    setAdFormPriority(Number(ad.priority || 0));
    setAdSuccessMsg(null);
    setAdErrorMsg(null);
    setShowAdModal(true);
  }

  async function handleToggleAd(adId) {
    try {
      await toggleAdminAd(token, adId);
      loadAds();
    } catch (err) {
      setAdErrorMsg(err.message || "تعذر تبديل حالة الإعلان");
    }
  }

  async function handleDeleteAd(adId) {
    if (!window.confirm("هل أنت متأكد من رغبتك في حذف هذا الإعلان نهائياً؟")) return;
    try {
      await deleteAdminAd(token, adId);
      loadAds();
    } catch (err) {
      setAdErrorMsg(err.message || "تعذر حذف الإعلان");
    }
  }

  async function handleSaveAd(e) {
    e?.preventDefault();
    if (!adFormTitle.trim()) {
      setAdErrorMsg("عنوان الإعلان مطلوب");
      return;
    }

    const payload = {
      title: adFormTitle.trim(),
      position: adFormPosition,
      ad_type: adFormType,
      image_url: adFormImageUrl.trim(),
      link_url: adFormLinkUrl.trim(),
      html_code: adFormHtmlCode,
      target_device: adFormTargetDevice,
      is_active: adFormIsActive,
      priority: parseInt(adFormPriority, 10) || 0,
    };

    try {
      if (editingAdId) {
        await updateAdminAd(token, editingAdId, payload);
        setAdSuccessMsg("تم تحديث الإعلان بنجاح!");
      } else {
        await createAdminAd(token, payload);
        setAdSuccessMsg("تم إنشاء الإعلان بنجاح!");
      }
      setShowAdModal(false);
      resetAdForm();
      loadAds();
    } catch (err) {
      setAdErrorMsg(err.message || "تعذر حفظ بيانات الإعلان");
    }
  }

  // Calculate Cockpit Summary Metrics
  const totalMatchesCount = matches.length;
  const matchesWithStreamsCount = matches.filter((m) => m.servers && m.servers.length > 0).length;
  const streamCoveragePct = totalMatchesCount > 0 ? Math.round((matchesWithStreamsCount / totalMatchesCount) * 100) : 0;
  const activeAdsCount = ads.filter((a) => a.is_active).length;

  // Unauthenticated view
  if (!token) {
    return (
      <div dir="rtl" className="app-shell py-8">
        <div className="mx-auto max-w-md rounded-3xl border border-slate-200/80 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-surface-dark sm:p-8">
          <div className="mb-6 text-center">
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-brand/10 text-brand">
              <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0110 0v4" />
              </svg>
            </div>
            <h2 className="text-xl font-extrabold text-slate-900 dark:text-white">
              تسجيل الدخول إلى مركز القيادة
            </h2>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              أدخل رمز المشرف (X-Admin-Token) للوصول إلى إدارة المباريات والإعلانات
            </p>
          </div>

          {authError && (
            <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-3 text-xs font-bold text-red-600 dark:border-red-900/50 dark:bg-red-500/10 dark:text-red-300">
              {authError}
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label
                htmlFor="admin-token"
                className="mb-1 block text-xs font-bold text-slate-700 dark:text-slate-300"
              >
                رمز المشرف
              </label>
              <input
                id="admin-token"
                data-testid="admin-token-input"
                type="password"
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                placeholder="أدخل رمز المشرف هنا..."
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none transition focus:border-brand focus:bg-white dark:border-slate-700 dark:bg-surface-dark-raised dark:text-white dark:focus:border-brand"
                autoFocus
              />
            </div>

            <div className="flex items-center gap-2 pt-2">
              <button
                type="submit"
                disabled={loading}
                className="flex-1 rounded-xl bg-brand py-2.5 text-xs font-bold text-white transition hover:bg-brand-hover disabled:opacity-50 shadow-md shadow-brand/20"
              >
                {loading ? "جارٍ التحقق…" : "تسجيل الدخول"}
              </button>
              <button
                type="button"
                onClick={onClose}
                className="rounded-xl border border-slate-200 px-4 py-2.5 text-xs font-bold text-slate-600 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                إلغاء
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div dir="rtl" className="space-y-6">
      {/* Cockpit Top Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200/80 pb-4 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand text-white shadow-sm">
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 2a14.5 14.5 0 000 20 14.5 14.5 0 000-20M2 12h20" />
              </svg>
            </span>
            <h2 className="text-lg font-extrabold text-slate-900 dark:text-white sm:text-xl">
              مركز القيادة الموحد (Cockpit CMS)
            </h2>
          </div>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            إدارة مباشرة وفورية للمباريات، سيرفرات البث، وشبكة الإعلانات الذكية
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleLogout}
            className="rounded-full border border-red-200 px-3 py-1.5 text-xs font-bold text-red-600 transition hover:bg-red-50 dark:border-red-900/50 dark:text-red-400 dark:hover:bg-red-950/30"
          >
            تسجيل الخروج
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full bg-slate-200 px-4 py-1.5 text-xs font-bold text-slate-800 transition hover:bg-slate-300 dark:bg-surface-dark-raised dark:text-slate-200 dark:hover:bg-slate-700"
          >
            العودة للمباريات
          </button>
        </div>
      </div>

      {/* Cockpit Metrics Strip */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-2xl border border-slate-200/70 bg-white/70 p-3.5 backdrop-blur shadow-sm dark:border-slate-800 dark:bg-surface-dark/70">
          <div className="text-[11px] font-bold text-slate-500 dark:text-slate-400">مباريات اليوم</div>
          <div className="mt-1 flex items-baseline justify-between">
            <span className="font-latin text-2xl font-black text-slate-900 dark:text-white">{totalMatchesCount}</span>
            <span className="text-[10px] text-slate-400">مباراة مجدولة</span>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200/70 bg-white/70 p-3.5 backdrop-blur shadow-sm dark:border-slate-800 dark:bg-surface-dark/70">
          <div className="text-[11px] font-bold text-slate-500 dark:text-slate-400">تغطية البث المباشر</div>
          <div className="mt-1 flex items-baseline justify-between">
            <span className="font-latin text-2xl font-black text-emerald-600 dark:text-emerald-400">%{streamCoveragePct}</span>
            <span className="text-[10px] text-slate-400">{matchesWithStreamsCount} بسيرفرات</span>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200/70 bg-white/70 p-3.5 backdrop-blur shadow-sm dark:border-slate-800 dark:bg-surface-dark/70">
          <div className="text-[11px] font-bold text-slate-500 dark:text-slate-400">الإعلانات النشطة</div>
          <div className="mt-1 flex items-baseline justify-between">
            <span className="font-latin text-2xl font-black text-brand dark:text-brand-light">{activeAdsCount}</span>
            <span className="text-[10px] text-slate-400">من {ads.length} حملة</span>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200/70 bg-white/70 p-3.5 backdrop-blur shadow-sm dark:border-slate-800 dark:bg-surface-dark/70">
          <div className="text-[11px] font-bold text-slate-500 dark:text-slate-400">حالة النظام اللحظي</div>
          <div className="mt-1 flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-sm font-black text-slate-800 dark:text-slate-100">نشط ومتصل</span>
          </div>
        </div>
      </div>

      {/* Cockpit 3-Tab Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-200/80 pb-2 dark:border-slate-800" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={adminTab === "matches"}
          onClick={() => setAdminTab("matches")}
          className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition sm:text-sm ${
            adminTab === "matches"
              ? "bg-brand text-white shadow-md shadow-brand/20"
              : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
          }`}
        >
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 2a14.5 14.5 0 000 20" />
          </svg>
          المباريات والبث المباشر
          <span className="rounded-full bg-white/20 px-1.5 py-0.2 text-[10px]">{matches.length}</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={adminTab === "ads"}
          onClick={() => {
            setAdminTab("ads");
            loadAds();
          }}
          className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition sm:text-sm ${
            adminTab === "ads"
              ? "bg-brand text-white shadow-md shadow-brand/20"
              : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
          }`}
        >
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="2" y="4" width="20" height="16" rx="2" />
            <path d="M7 15h0M2 9.5h20" />
          </svg>
          إدارة الإعلانات
          <span className="rounded-full bg-white/20 px-1.5 py-0.2 text-[10px]">{ads.length}</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={adminTab === "analytics"}
          onClick={() => {
            setAdminTab("analytics");
            loadAnalytics(token, analyticsPeriod);
          }}
          className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition sm:text-sm ${
            adminTab === "analytics"
              ? "bg-brand text-white shadow-md shadow-brand/20"
              : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
          }`}
        >
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 20V10M12 20V4M6 20v-6" />
          </svg>
          إحصائيات الزوار
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={adminTab === "overview"}
          onClick={() => setAdminTab("overview")}
          className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition sm:text-sm ${
            adminTab === "overview"
              ? "bg-brand text-white shadow-md shadow-brand/20"
              : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
          }`}
        >
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
          </svg>
          نظرة عامة على النظام
        </button>
      </div>

      {/* =========================================================================
          TAB 1: MATCHES & STREAMS HUB
         ========================================================================= */}
      {adminTab === "matches" && (
        <div className="space-y-6">
          {/* Matches Filters */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => setDateFilter("all")}
                className={`rounded-full px-3 py-1 text-xs font-bold transition ${
                  dateFilter === "all"
                    ? "bg-brand text-white shadow-sm"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-surface-dark-raised dark:text-slate-300 dark:hover:bg-slate-700"
                }`}
              >
                الكل
              </button>
              <button
                type="button"
                onClick={() => setDateFilter("yesterday")}
                className={`rounded-full px-3 py-1 text-xs font-bold transition ${
                  dateFilter === "yesterday"
                    ? "bg-brand text-white shadow-sm"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-surface-dark-raised dark:text-slate-300 dark:hover:bg-slate-700"
                }`}
              >
                الأمس
              </button>
              <button
                type="button"
                onClick={() => setDateFilter("today")}
                className={`rounded-full px-3 py-1 text-xs font-bold transition ${
                  dateFilter === "today"
                    ? "bg-brand text-white shadow-sm"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-surface-dark-raised dark:text-slate-300 dark:hover:bg-slate-700"
                }`}
              >
                اليوم
              </button>
              <button
                type="button"
                onClick={() => setDateFilter("tomorrow")}
                className={`rounded-full px-3 py-1 text-xs font-bold transition ${
                  dateFilter === "tomorrow"
                    ? "bg-brand text-white shadow-sm"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-surface-dark-raised dark:text-slate-300 dark:hover:bg-slate-700"
                }`}
              >
                الغد
              </button>
            </div>

            <div className="w-full sm:w-64">
              <input
                type="search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="البحث عن فريق أو بطولة…"
                className="w-full rounded-full border border-slate-200 bg-white px-4 py-1.5 text-xs outline-none focus:border-brand dark:border-slate-700 dark:bg-surface-dark dark:text-white"
              />
            </div>
          </div>

          {loadError && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs font-bold text-red-600 dark:border-red-900/50 dark:bg-red-500/10 dark:text-red-300">
              {loadError}
            </div>
          )}

          {/* Main 2-column layout */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
            {/* Matches List */}
            <div className="space-y-3 lg:col-span-5">
              <h3 className="text-sm font-extrabold text-slate-700 dark:text-slate-300">
                قائمة المباريات ({matches.length})
              </h3>

              {loading && (
                <div className="space-y-2">
                  {[1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className="h-20 animate-pulse rounded-2xl border border-slate-200 bg-slate-100 dark:border-slate-800 dark:bg-surface-dark-raised"
                    />
                  ))}
                </div>
              )}

              {!loading && matches.length === 0 && (
                <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-xs text-slate-400 dark:border-slate-800">
                  لا توجد مباريات تطابق هذا البحث
                </div>
              )}

              <div className="max-h-[640px] space-y-2.5 overflow-y-auto pr-1">
                {matches.map((item) => {
                  const m = item.match;
                  const isSelected = m.id === selectedMatchId;
                  const hasOverride = item.override !== null;
                  const adminStreamCount = item.admin_server_ids.length;

                  return (
                    <div
                      key={m.id}
                      role="button"
                      tabIndex={0}
                      onClick={() => setSelectedMatchId(m.id)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") setSelectedMatchId(m.id);
                      }}
                      className={`cursor-pointer rounded-2xl border p-3.5 transition ${
                        isSelected
                          ? "border-brand bg-brand/5 dark:border-brand dark:bg-brand/10 shadow-sm"
                          : "border-slate-200 bg-white hover:border-slate-300 dark:border-slate-800 dark:bg-surface-dark dark:hover:border-slate-700"
                      }`}
                    >
                      <div className="flex items-center justify-between text-[11px] text-slate-400">
                        <span>{m.league.name_ar}</span>
                        <span dir="ltr">{m.kickoff_time_local}</span>
                      </div>

                      <div className="my-2 flex items-center justify-between">
                        <span className="text-xs font-extrabold text-slate-800 dark:text-slate-100 sm:text-sm">
                          {m.home_team.name_ar}
                        </span>
                        <span dir="ltr" className="font-latin text-sm font-black text-slate-900 dark:text-white">
                          {m.home_score} - {m.away_score}
                        </span>
                        <span className="text-xs font-extrabold text-slate-800 dark:text-slate-100 sm:text-sm">
                          {m.away_team.name_ar}
                        </span>
                      </div>

                      <div className="flex items-center justify-between pt-1 text-[10px]">
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 font-bold text-slate-600 dark:bg-surface-dark-raised dark:text-slate-300">
                          {m.status_label_ar}
                        </span>

                        <div className="flex items-center gap-1.5">
                          {item.servers.length > 0 && (
                            <span className="rounded-full bg-emerald-100 px-2 py-0.5 font-bold text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300">
                              بث متاح ({item.servers.length})
                            </span>
                          )}
                          {adminStreamCount > 0 && (
                            <span className="rounded-full bg-blue-100 px-2 py-0.5 font-bold text-blue-700 dark:bg-blue-500/15 dark:text-blue-300">
                              {adminStreamCount} سيرفر إدارة
                            </span>
                          )}
                          {hasOverride && (
                            <span className="rounded-full bg-amber-100 px-2 py-0.5 font-bold text-amber-700 dark:bg-amber-500/15 dark:text-amber-300">
                              تعديل يدوي
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Selected Match Editor */}
            <div className="space-y-6 lg:col-span-7">
              {!selectedItem ? (
                <div className="flex h-64 flex-col items-center justify-center rounded-3xl border border-dashed border-slate-300 p-8 text-center dark:border-slate-800">
                  <div className="mb-2 text-brand">
                    <svg className="h-8 w-8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M15 18l-6-6 6-6" />
                    </svg>
                  </div>
                  <p className="text-sm font-bold text-slate-500 dark:text-slate-400">
                    اختر مباراة من القائمة لتعديل نتيجتها أو إدارة سيرفرات البث
                  </p>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Status Banner */}
                  {actionSuccess && (
                    <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-3.5 text-xs font-bold text-emerald-700 dark:border-emerald-900/50 dark:bg-emerald-500/10 dark:text-emerald-300">
                      {actionSuccess}
                    </div>
                  )}
                  {actionError && (
                    <div className="rounded-2xl border border-red-200 bg-red-50 p-3.5 text-xs font-bold text-red-600 dark:border-red-900/50 dark:bg-red-500/10 dark:text-red-300">
                      {actionError}
                    </div>
                  )}

                  {/* Header of selected match */}
                  <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-surface-dark sm:p-5">
                    <div className="text-[11px] font-bold text-slate-400">
                      {selectedItem.match.league.name_ar} • {selectedItem.match.competition_subtitle}
                    </div>
                    <div className="my-3 flex items-center justify-between text-base font-black text-slate-900 dark:text-white sm:text-lg">
                      <span>{selectedItem.match.home_team.name_ar}</span>
                      <span dir="ltr" className="rounded-xl bg-slate-100 px-3 py-1 font-latin text-brand dark:bg-surface-dark-raised">
                        {selectedItem.match.home_score} - {selectedItem.match.away_score}
                      </span>
                      <span>{selectedItem.match.away_team.name_ar}</span>
                    </div>
                    <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400">
                      <div className="flex flex-wrap items-center gap-2">
                        <span>الحالة: {selectedItem.match.status_label_ar}</span>
                        {selectedItem.match.channel && <span>• القناة: {selectedItem.match.channel}</span>}
                        {selectedItem.match.commentator && <span>• المعلق: {selectedItem.match.commentator}</span>}
                      </div>

                      <button
                        type="button"
                        data-testid="copy-article-btn"
                        onClick={() => handleCopyArticle(selectedItem.match.id)}
                        disabled={copyingArticle}
                        className="inline-flex items-center gap-1.5 rounded-xl border border-brand/30 bg-brand/10 px-3 py-1.5 text-xs font-bold text-brand transition hover:bg-brand/20 active:scale-95 disabled:opacity-50 dark:border-brand/40 dark:bg-brand/20 dark:text-brand-light"
                        title="نسخ كود المقال المتوافق مع Google SEO ولصقه في Blogger"
                      >
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" />
                        </svg>
                        <span>{copyingArticle ? "جاري النسخ..." : "نسخ مقال التدوينة 📝"}</span>
                      </button>
                    </div>
                  </div>

                  {/* Manual Score / Status Override Section */}
                  <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-surface-dark">
                    <div className="mb-4 flex items-center justify-between">
                      <h4 className="text-sm font-black text-slate-800 dark:text-slate-100">
                        التعديل اليدوي للنتيجة والمباراة
                      </h4>
                      {selectedItem.override && (
                        <button
                          type="button"
                          onClick={handleClearOverride}
                          className="rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-xs font-bold text-amber-700 transition hover:bg-amber-100 dark:border-amber-900 dark:bg-amber-500/10 dark:text-amber-300"
                        >
                          إلغاء التعديل
                        </button>
                      )}
                    </div>

                    <form onSubmit={handleSaveOverride} className="space-y-4">
                      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                        <div>
                          <label className="mb-1 block text-[11px] font-bold text-slate-600 dark:text-slate-300">
                            أهداف {selectedItem.match.home_team.name_ar}
                          </label>
                          <input
                            type="number"
                            min="0"
                            max="99"
                            data-testid="override-home-score"
                            value={overrideHomeScore}
                            onChange={(e) => setOverrideHomeScore(e.target.value)}
                            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-center font-latin text-sm font-bold outline-none focus:border-brand dark:border-slate-700 dark:bg-surface-dark-raised dark:text-white"
                          />
                        </div>

                        <div>
                          <label className="mb-1 block text-[11px] font-bold text-slate-600 dark:text-slate-300">
                            أهداف {selectedItem.match.away_team.name_ar}
                          </label>
                          <input
                            type="number"
                            min="0"
                            max="99"
                            value={overrideAwayScore}
                            onChange={(e) => setOverrideAwayScore(e.target.value)}
                            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-center font-latin text-sm font-bold outline-none focus:border-brand dark:border-slate-700 dark:bg-surface-dark-raised dark:text-white"
                          />
                        </div>

                        <div>
                          <label className="mb-1 block text-[11px] font-bold text-slate-600 dark:text-slate-300">
                            الدقيقة الحالية
                          </label>
                          <input
                            type="number"
                            min="0"
                            max="130"
                            placeholder="مثال: 65"
                            value={overrideElapsed}
                            onChange={(e) => setOverrideElapsed(e.target.value)}
                            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-center font-latin text-sm font-bold outline-none focus:border-brand dark:border-slate-700 dark:bg-surface-dark-raised dark:text-white"
                          />
                        </div>

                        <div>
                          <label className="mb-1 block text-[11px] font-bold text-slate-600 dark:text-slate-300">
                            حالة المباراة
                          </label>
                          <select
                            value={overrideStatus}
                            onChange={(e) => setOverrideStatus(e.target.value)}
                            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-2 py-1.5 text-xs font-bold outline-none focus:border-brand dark:border-slate-700 dark:bg-surface-dark-raised dark:text-white"
                          >
                            {STATUS_OPTIONS.map((opt) => (
                              <option key={opt.value} value={opt.value}>
                                {opt.label}
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                        <div>
                          <label className="mb-1 block text-[11px] font-bold text-slate-600 dark:text-slate-300">
                            القناة الناقلة
                          </label>
                          <input
                            type="text"
                            placeholder="مثال: beIN SPORTS 1 HD"
                            value={overrideChannel}
                            onChange={(e) => setOverrideChannel(e.target.value)}
                            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs outline-none focus:border-brand dark:border-slate-700 dark:bg-surface-dark-raised dark:text-white"
                          />
                        </div>

                        <div>
                          <label className="mb-1 block text-[11px] font-bold text-slate-600 dark:text-slate-300">
                            المعلق
                          </label>
                          <input
                            type="text"
                            placeholder="مثال: عصام الشوالي"
                            value={overrideCommentator}
                            onChange={(e) => setOverrideCommentator(e.target.value)}
                            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs outline-none focus:border-brand dark:border-slate-700 dark:bg-surface-dark-raised dark:text-white"
                          />
                        </div>
                      </div>

                      <div className="flex items-center justify-end gap-2 pt-2">
                        <button
                          type="button"
                          onClick={handleClearOverride}
                          className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-2 text-xs font-bold text-amber-700 transition hover:bg-amber-100 dark:border-amber-900 dark:bg-amber-500/10 dark:text-amber-300"
                        >
                          إلغاء التعديل
                        </button>
                        <button
                          type="submit"
                          className="rounded-xl bg-brand px-5 py-2 text-xs font-bold text-white transition hover:bg-brand-hover shadow-md shadow-brand/20"
                        >
                          حفظ التعديل
                        </button>
                      </div>
                    </form>
                  </div>

                  {/* Stream Servers Management Section */}
                  <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-surface-dark">
                    <h4 className="mb-3 text-sm font-black text-slate-800 dark:text-slate-100">
                      سيرفرات البث المباشر ({selectedItem.servers.length})
                    </h4>

                    {/* Current Servers List */}
                    <div className="mb-5 space-y-2">
                      {selectedItem.servers.length === 0 ? (
                        <p className="rounded-xl border border-dashed border-slate-200 p-4 text-center text-xs text-slate-400 dark:border-slate-800">
                          لا توجد سيرفرات بث مضافة لهذه المباراة
                        </p>
                      ) : (
                        selectedItem.servers.map((srv) => {
                          const isAdminServer = selectedItem.admin_server_ids.includes(srv.id);
                          return (
                            <div
                              key={srv.id}
                              className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs dark:border-slate-700 dark:bg-surface-dark-raised"
                            >
                              <div className="min-w-0 flex-1">
                                <div className="flex items-center gap-2">
                                  <span className="font-bold text-slate-800 dark:text-slate-200">
                                    {srv.server_name}
                                  </span>
                                  {isAdminServer && (
                                    <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-bold text-blue-700 dark:bg-blue-500/15 dark:text-blue-300">
                                      سيرفر إدارة
                                    </span>
                                  )}
                                  <span className="rounded-full bg-slate-200 px-2 py-0.5 font-latin text-[10px] text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                                    {srv.type}
                                  </span>
                                </div>
                                <p className="mt-1 truncate font-latin text-[11px] text-slate-400" dir="ltr">
                                  {srv.url}
                                </p>
                              </div>

                              {isAdminServer && (
                                <button
                                  type="button"
                                  data-testid={`delete-stream-${srv.id}`}
                                  onClick={() => handleDeleteStream(srv.id)}
                                  className="mr-3 rounded-lg border border-red-200 px-2.5 py-1 text-xs font-bold text-red-600 transition hover:bg-red-50 dark:border-red-900/40 dark:text-red-400 dark:hover:bg-red-950/30"
                                >
                                  حذف
                                </button>
                              )}
                            </div>
                          );
                        })
                      )}
                    </div>

                    {/* Add New Stream Form */}
                    <form onSubmit={handleAddStream} className="space-y-3 rounded-2xl border border-slate-200 bg-slate-50/60 p-4 dark:border-slate-800 dark:bg-surface-dark-raised/50">
                      <div className="text-xs font-bold text-slate-700 dark:text-slate-200">
                        إضافة سيرفر بث جديد
                      </div>

                      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                        <div>
                          <label className="mb-1 block text-[11px] font-bold text-slate-600 dark:text-slate-300">
                            اسم السيرفر
                          </label>
                          <input
                            type="text"
                            data-testid="stream-name-input"
                            placeholder="مثال: سيرفر 1 (متعدد الجودات)"
                            value={streamName}
                            onChange={(e) => setStreamName(e.target.value)}
                            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs outline-none focus:border-brand dark:border-slate-700 dark:bg-surface-dark dark:text-white"
                          />
                        </div>

                        <div>
                          <label className="mb-1 block text-[11px] font-bold text-slate-600 dark:text-slate-300">
                            نوع البث
                          </label>
                          <select
                            value={streamType}
                            onChange={(e) => setStreamType(e.target.value)}
                            className="w-full rounded-xl border border-slate-200 bg-white px-2 py-1.5 text-xs font-bold outline-none focus:border-brand dark:border-slate-700 dark:bg-surface-dark dark:text-white"
                          >
                            <option value="iframe">iframe (تضمين خارجي)</option>
                            <option value="m3u8">m3u8 / HLS (مشغل فيديو مباشر)</option>
                          </select>
                        </div>
                      </div>

                      <div>
                        <label className="mb-1 block text-[11px] font-bold text-slate-600 dark:text-slate-300">
                          رابط البث المباشر (URL)
                        </label>
                        <input
                          type="url"
                          data-testid="stream-url-input"
                          placeholder="https://shoots-yalla.com/albaplayer/... أو https://example.com/stream.m3u8"
                          value={streamUrl}
                          onChange={(e) => setStreamUrl(e.target.value)}
                          className="w-full rounded-xl border border-slate-200 bg-white px-3 py-1.5 font-latin text-xs outline-none focus:border-brand dark:border-slate-700 dark:bg-surface-dark dark:text-white"
                          dir="ltr"
                        />
                        <p className="mt-1 text-[10px] text-slate-400">
                          ملاحظة: إذا وضعت رابط مقال بلوجر أو صفحة مغلفة، سيقوم النظام تلقائياً باستخراج مشغل الفيديو المباشر المستقل وتوسيطه بدون إعلانات مدونة.
                        </p>
                      </div>

                      <div className="flex justify-end pt-1">
                        <button
                          type="submit"
                          className="rounded-xl bg-brand px-4 py-2 text-xs font-bold text-white transition hover:bg-brand-hover shadow-md shadow-brand/20"
                        >
                          إضافة سيرفر
                        </button>
                      </div>
                    </form>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          TAB 2: DEDICATED ADS CMS ENGINE
         ========================================================================= */}
      {adminTab === "ads" && (
        <div className="space-y-6">
          {/* Top Actions & Position Filter Pills */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 no-scrollbar">
              {AD_POSITIONS.map((pos) => (
                <button
                  key={pos.id}
                  type="button"
                  onClick={() => setAdPositionFilter(pos.id)}
                  className={`whitespace-nowrap rounded-full px-3.5 py-1 text-xs font-bold transition ${
                    adPositionFilter === pos.id
                      ? "bg-brand text-white shadow-sm"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-surface-dark-raised dark:text-slate-300 dark:hover:bg-slate-700"
                  }`}
                >
                  {pos.label}
                  {pos.id !== "all" && (
                    <span className="mr-1.5 opacity-80">
                      ({ads.filter((a) => a.position === pos.id).length})
                    </span>
                  )}
                </button>
              ))}
            </div>

            <button
              type="button"
              onClick={handleOpenCreateAd}
              className="flex items-center gap-1.5 rounded-full bg-brand px-4 py-2 text-xs font-bold text-white transition hover:bg-brand-hover shadow-md shadow-brand/20"
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M12 5v14M5 12h14" />
              </svg>
              إضافة إعلان جديد
            </button>
          </div>

          {adSuccessMsg && (
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-3 text-xs font-bold text-emerald-700 dark:border-emerald-900/50 dark:bg-emerald-500/10 dark:text-emerald-300">
              {adSuccessMsg}
            </div>
          )}
          {adErrorMsg && (
            <div className="rounded-2xl border border-red-200 bg-red-50 p-3 text-xs font-bold text-red-600 dark:border-red-900/50 dark:bg-red-500/10 dark:text-red-300">
              {adErrorMsg}
            </div>
          )}

          {adsLoading && (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="h-24 animate-pulse rounded-2xl border border-slate-200 bg-slate-100 dark:border-slate-800 dark:bg-surface-dark-raised"
                />
              ))}
            </div>
          )}

          {!adsLoading && ads.length === 0 && (
            <div className="rounded-3xl border border-dashed border-slate-300 p-12 text-center dark:border-slate-800">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-slate-400 dark:bg-surface-dark-raised">
                <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="2" y="4" width="20" height="16" rx="2" />
                  <path d="M7 15h0M2 9.5h20" />
                </svg>
              </div>
              <h4 className="text-sm font-bold text-slate-700 dark:text-slate-300">لا توجد إعلانات مضافة بعد</h4>
              <p className="mt-1 text-xs text-slate-400">
                اضغط على زر "إضافة إعلان جديد" لتثبيت بانر رعاة أو كود جوجل أدسنس في أي موضع من مواضع الموقع
              </p>
              <button
                type="button"
                onClick={handleOpenCreateAd}
                className="mt-4 rounded-full bg-brand px-4 py-1.5 text-xs font-bold text-white transition hover:bg-brand-hover"
              >
                إضافة إعلان الآن
              </button>
            </div>
          )}

          {/* Ad Cards Grid */}
          {!adsLoading && ads.length > 0 && (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {ads.map((ad) => {
                const posMeta = AD_POSITIONS.find((p) => p.id === ad.position) || { label: ad.position };
                const deviceLabel =
                  ad.target_device === "mobile"
                    ? "جوال فقط"
                    : ad.target_device === "desktop"
                    ? "كمبيوتر فقط"
                    : "جميع الأجهزة";

                return (
                  <div
                    key={ad.id}
                    className={`flex flex-col justify-between rounded-2xl border p-4.5 transition backdrop-blur shadow-sm ${
                      ad.is_active
                        ? "border-slate-200/90 bg-white/80 dark:border-slate-800 dark:bg-surface-dark/90"
                        : "border-slate-200/40 bg-slate-50/50 opacity-60 dark:border-slate-800/40 dark:bg-surface-dark/40"
                    }`}
                  >
                    <div>
                      {/* Top Badges & Toggle */}
                      <div className="flex items-center justify-between border-b border-slate-100 pb-2.5 dark:border-slate-800">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="rounded-full bg-brand/10 px-2.5 py-0.5 text-[11px] font-bold text-brand dark:bg-brand/20 dark:text-brand-light">
                            {posMeta.label}
                          </span>
                          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600 dark:bg-surface-dark-raised dark:text-slate-300">
                            {deviceLabel}
                          </span>
                          <span className="rounded-full bg-slate-100 px-2 py-0.5 font-latin text-[10px] font-semibold text-slate-500 dark:bg-surface-dark-raised">
                            P: {ad.priority}
                          </span>
                        </div>

                        {/* Active Toggle Switch */}
                        <button
                          type="button"
                          data-testid={`toggle-ad-${ad.id}`}
                          onClick={() => handleToggleAd(ad.id)}
                          className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                            ad.is_active ? "bg-emerald-500" : "bg-slate-300 dark:bg-slate-700"
                          }`}
                          aria-label={ad.is_active ? "تعطيل الإعلان" : "تفعيل الإعلان"}
                        >
                          <span
                            className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                              ad.is_active ? "translate-x-4" : "translate-x-0"
                            }`}
                          />
                        </button>
                      </div>

                      {/* Content Preview */}
                      <div className="my-3">
                        <h4 className="text-sm font-extrabold text-slate-900 dark:text-white">
                          {ad.title}
                        </h4>

                        {ad.ad_type === "image_banner" ? (
                          <div className="mt-2 flex items-center gap-3">
                            {ad.image_url ? (
                              <img
                                src={ad.image_url}
                                alt={ad.title}
                                className="h-16 w-32 rounded-lg border border-slate-200 object-cover dark:border-slate-700"
                              />
                            ) : (
                              <div className="flex h-16 w-32 items-center justify-center rounded-lg bg-slate-100 text-[10px] text-slate-400 dark:bg-surface-dark-raised">
                                لا توجد صورة
                              </div>
                            )}
                            <div className="min-w-0 flex-1">
                              <span className="block text-[10px] font-bold text-slate-400">رابط التوجيه:</span>
                              <a
                                href={ad.link_url || "#"}
                                target="_blank"
                                rel="noreferrer"
                                className="block truncate font-latin text-[11px] text-brand hover:underline"
                                dir="ltr"
                              >
                                {ad.link_url || "لا يوجد رابط"}
                              </a>
                            </div>
                          </div>
                        ) : (
                          <div className="mt-2 rounded-lg bg-slate-900 p-2 text-[11px] font-mono text-emerald-400 dark:bg-black">
                            <span className="text-[10px] text-slate-500 block mb-1">كود مخصص / أدسنس:</span>
                            <p className="truncate line-clamp-2" dir="ltr">
                              {ad.html_code || "كود HTML فارغ"}
                            </p>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Bottom Actions */}
                    <div className="flex items-center justify-between border-t border-slate-100 pt-2.5 dark:border-slate-800">
                      <span className="text-[10px] text-slate-400">
                        {ad.is_active ? "🟢 الإعلان نشط حالياً" : "⚪ الإعلان معطل"}
                      </span>

                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => handleOpenEditAd(ad)}
                          className="rounded-lg border border-slate-200 px-3 py-1 text-xs font-bold text-slate-600 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                        >
                          تعديل
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteAd(ad.id)}
                          className="rounded-lg border border-red-200 px-3 py-1 text-xs font-bold text-red-600 transition hover:bg-red-50 dark:border-red-900/40 dark:text-red-400 dark:hover:bg-red-950/30"
                        >
                          حذف
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Ad Create / Edit Modal */}
          {showAdModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
              <div
                dir="rtl"
                className="w-full max-w-xl max-h-[90vh] overflow-y-auto rounded-3xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-800 dark:bg-surface-dark"
              >
                <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
                  <h3 className="text-base font-extrabold text-slate-900 dark:text-white">
                    {editingAdId ? "تعديل الإعلان" : "إضافة إعلان جديد"}
                  </h3>
                  <button
                    type="button"
                    onClick={() => setShowAdModal(false)}
                    className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-white"
                  >
                    <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M18 6L6 18M6 6l12 12" />
                    </svg>
                  </button>
                </div>

                <form onSubmit={handleSaveAd} className="mt-4 space-y-4">
                  <div>
                    <label className="mb-1 block text-xs font-bold text-slate-700 dark:text-slate-300">
                      عنوان الإعلان (داخلي للتعرف عليه)
                    </label>
                    <input
                      type="text"
                      data-testid="ad-title-input"
                      placeholder="مثال: بانر راعي رئيسي - ليدربورد"
                      value={adFormTitle}
                      onChange={(e) => setAdFormTitle(e.target.value)}
                      className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs outline-none focus:border-brand dark:border-slate-700 dark:bg-surface-dark-raised dark:text-white"
                      required
                    />
                  </div>

                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <div>
                      <label className="mb-1 block text-xs font-bold text-slate-700 dark:text-slate-300">
                        موضع الإعلان في الموقع
                      </label>
                      <select
                        value={adFormPosition}
                        onChange={(e) => setAdFormPosition(e.target.value)}
                        className="w-full rounded-xl border border-slate-200 bg-slate-50 px-2 py-2 text-xs font-bold outline-none focus:border-brand dark:border-slate-700 dark:bg-surface-dark-raised dark:text-white"
                      >
                        <option value="header_top">ليدربورد علوي (أعلى الصفحة)</option>
                        <option value="in_feed">بين المباريات (In-feed)</option>
                        <option value="player_top">أعلى مشغل الفيديو (Player Top)</option>
                        <option value="player_bottom">أسفل مشغل الفيديو (Player Bottom)</option>
                        <option value="sticky_bottom">شريط عائم سفلي (Sticky Footer)</option>
                      </select>
                    </div>

                    <div>
                      <label className="mb-1 block text-xs font-bold text-slate-700 dark:text-slate-300">
                        نوع الإعلان
                      </label>
                      <select
                        value={adFormType}
                        onChange={(e) => setAdFormType(e.target.value)}
                        className="w-full rounded-xl border border-slate-200 bg-slate-50 px-2 py-2 text-xs font-bold outline-none focus:border-brand dark:border-slate-700 dark:bg-surface-dark-raised dark:text-white"
                      >
                        <option value="image_banner">بانر صورة مع رابط توجيه</option>
                        <option value="custom_html">كود مخصص / Google AdSense</option>
                      </select>
                    </div>
                  </div>

                  {adFormType === "image_banner" ? (
                    <>
                      <div>
                        <label className="mb-1 block text-xs font-bold text-slate-700 dark:text-slate-300">
                          رابط الصورة (Image URL)
                        </label>
                        <input
                          type="url"
                          data-testid="ad-image-url-input"
                          placeholder="https://example.com/banner.png"
                          value={adFormImageUrl}
                          onChange={(e) => setAdFormImageUrl(e.target.value)}
                          className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 font-latin text-xs outline-none focus:border-brand dark:border-slate-700 dark:bg-surface-dark-raised dark:text-white"
                          dir="ltr"
                        />
                      </div>

                      <div>
                        <label className="mb-1 block text-xs font-bold text-slate-700 dark:text-slate-300">
                          رابط التوجيه عند النقر (Click URL)
                        </label>
                        <input
                          type="url"
                          placeholder="https://sponsor.com"
                          value={adFormLinkUrl}
                          onChange={(e) => setAdFormLinkUrl(e.target.value)}
                          className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 font-latin text-xs outline-none focus:border-brand dark:border-slate-700 dark:bg-surface-dark-raised dark:text-white"
                          dir="ltr"
                        />
                      </div>

                      {adFormImageUrl && (
                        <div>
                          <span className="mb-1 block text-[11px] font-bold text-slate-400">معاينة البانر:</span>
                          <div className="rounded-xl border border-slate-200 p-2 text-center dark:border-slate-700">
                            <img
                              src={adFormImageUrl}
                              alt="معاينة"
                              className="mx-auto max-h-36 rounded-lg object-contain"
                              onError={(e) => {
                                e.target.style.display = "none";
                              }}
                            />
                          </div>
                        </div>
                      )}
                    </>
                  ) : (
                    <div>
                      <label className="mb-1 block text-xs font-bold text-slate-700 dark:text-slate-300">
                        كود HTML / JavaScript / AdSense
                      </label>
                      <textarea
                        rows={5}
                        placeholder="<ins class='adsbygoogle' ...></ins><script>(adsbygoogle = window.adsbygoogle || []).push({});</script>"
                        value={adFormHtmlCode}
                        onChange={(e) => setAdFormHtmlCode(e.target.value)}
                        className="w-full rounded-xl border border-slate-200 bg-slate-50 p-3 font-mono text-xs outline-none focus:border-brand dark:border-slate-700 dark:bg-surface-dark-raised dark:text-emerald-400"
                        dir="ltr"
                      />
                    </div>
                  )}

                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                    <div>
                      <label className="mb-1 block text-xs font-bold text-slate-700 dark:text-slate-300">
                        استهداف الأجهزة
                      </label>
                      <select
                        value={adFormTargetDevice}
                        onChange={(e) => setAdFormTargetDevice(e.target.value)}
                        className="w-full rounded-xl border border-slate-200 bg-slate-50 px-2 py-2 text-xs font-bold outline-none focus:border-brand dark:border-slate-700 dark:bg-surface-dark-raised dark:text-white"
                      >
                        <option value="all">جميع الأجهزة (الكل)</option>
                        <option value="desktop">أجهزة الكمبيوتر فقط</option>
                        <option value="mobile">الهواتف الذكية فقط</option>
                      </select>
                    </div>

                    <div>
                      <label className="mb-1 block text-xs font-bold text-slate-700 dark:text-slate-300">
                        أولوية العرض (Priority)
                      </label>
                      <input
                        type="number"
                        min="0"
                        max="1000"
                        value={adFormPriority}
                        onChange={(e) => setAdFormPriority(e.target.value)}
                        className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 font-latin text-xs outline-none focus:border-brand dark:border-slate-700 dark:bg-surface-dark-raised dark:text-white"
                      />
                    </div>

                    <div className="flex flex-col justify-end">
                      <label className="flex items-center gap-2 cursor-pointer pb-2">
                        <input
                          type="checkbox"
                          checked={adFormIsActive}
                          onChange={(e) => setAdFormIsActive(e.target.checked)}
                          className="h-4 w-4 rounded text-brand focus:ring-brand"
                        />
                        <span className="text-xs font-bold text-slate-700 dark:text-slate-300">
                          تفعيل الإعلان فوراً
                        </span>
                      </label>
                    </div>
                  </div>

                  <div className="flex items-center justify-end gap-2 border-t border-slate-100 pt-3 dark:border-slate-800">
                    <button
                      type="button"
                      onClick={() => setShowAdModal(false)}
                      className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-bold text-slate-600 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                    >
                      إلغاء
                    </button>
                    <button
                      type="submit"
                      className="rounded-xl bg-brand px-5 py-2 text-xs font-bold text-white transition hover:bg-brand-hover shadow-md shadow-brand/20"
                    >
                      حفظ الإعلان
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      )}

      {/* =========================================================================
          TAB 3: SITE ANALYTICS & VISITOR STATISTICS
         ========================================================================= */}
      {adminTab === "analytics" && (
        <div className="space-y-6">
          {/* Header & Date Period Filter Pills */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-base font-extrabold text-slate-900 dark:text-white sm:text-lg">
                إحصائيات الزوار والمنصة
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                تحليل دقيق ومباشر لعدد الزيارات والزوار الفريدين مصنفة حسب الفترات الزمنية
              </p>
            </div>

            <div className="flex items-center gap-1.5 rounded-2xl border border-slate-200/80 bg-white/70 p-1 dark:border-slate-800 dark:bg-surface-dark/70">
              <button
                type="button"
                onClick={() => {
                  setAnalyticsPeriod("day");
                  loadAnalytics(token, "day");
                }}
                className={`rounded-xl px-3 py-1.5 text-xs font-bold transition ${
                  analyticsPeriod === "day"
                    ? "bg-brand text-white shadow-sm"
                    : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                }`}
              >
                اليوم (24 ساعة)
              </button>
              <button
                type="button"
                onClick={() => {
                  setAnalyticsPeriod("week");
                  loadAnalytics(token, "week");
                }}
                className={`rounded-xl px-3 py-1.5 text-xs font-bold transition ${
                  analyticsPeriod === "week"
                    ? "bg-brand text-white shadow-sm"
                    : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                }`}
              >
                هذا الأسبوع (7 أيام)
              </button>
              <button
                type="button"
                onClick={() => {
                  setAnalyticsPeriod("month");
                  loadAnalytics(token, "month");
                }}
                className={`rounded-xl px-3 py-1.5 text-xs font-bold transition ${
                  analyticsPeriod === "month"
                    ? "bg-brand text-white shadow-sm"
                    : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                }`}
              >
                هذا الشهر (30 يوماً)
              </button>
              <button
                type="button"
                onClick={() => {
                  setAnalyticsPeriod("year");
                  loadAnalytics(token, "year");
                }}
                className={`rounded-xl px-3 py-1.5 text-xs font-bold transition ${
                  analyticsPeriod === "year"
                    ? "bg-brand text-white shadow-sm"
                    : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                }`}
              >
                هذا العام (12 شهراً)
              </button>
            </div>
          </div>

          {analyticsError && (
            <div className="rounded-2xl border border-red-200 bg-red-50 p-3 text-xs font-bold text-red-600 dark:border-red-900/50 dark:bg-red-500/10 dark:text-red-300">
              {analyticsError}
            </div>
          )}

          {analyticsLoading && !analyticsData && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="h-20 animate-pulse rounded-2xl bg-slate-100 dark:bg-surface-dark-raised" />
                ))}
              </div>
              <div className="h-64 animate-pulse rounded-3xl bg-slate-100 dark:bg-surface-dark-raised" />
            </div>
          )}

          {analyticsData && (
            <>
              {/* Summary 4-KPI Grid */}
              {(() => {
                const s = analyticsData.summary || {};
                const currentPeriodVisits =
                  analyticsPeriod === "day"
                    ? s.today_visits
                    : analyticsPeriod === "month"
                    ? s.month_visits
                    : analyticsPeriod === "year"
                    ? s.year_visits
                    : s.week_visits;
                const currentPeriodUniques =
                  analyticsPeriod === "day"
                    ? s.today_uniques
                    : analyticsPeriod === "month"
                    ? s.month_uniques
                    : analyticsPeriod === "year"
                    ? s.year_uniques
                    : s.week_uniques;

                const dev = analyticsData.device_stats || {};
                const totalDev = (dev.mobile || 0) + (dev.desktop || 0) + (dev.tablet || 0) || 1;
                const mobilePct = Math.round(((dev.mobile || 0) / totalDev) * 100);

                return (
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                    <div className="rounded-2xl border border-slate-200/80 bg-white/80 p-4 shadow-sm dark:border-slate-800 dark:bg-surface-dark/80 backdrop-blur">
                      <div className="text-[11px] font-bold text-slate-500 dark:text-slate-400">
                        إجمالي الزيارات
                      </div>
                      <div className="mt-1 flex items-baseline justify-between">
                        <span className="font-latin text-2xl font-black text-slate-900 dark:text-white">
                          {(currentPeriodVisits ?? 0).toLocaleString()}
                        </span>
                        <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-bold">
                          مشاهدة
                        </span>
                      </div>
                    </div>

                    <div className="rounded-2xl border border-slate-200/80 bg-white/80 p-4 shadow-sm dark:border-slate-800 dark:bg-surface-dark/80 backdrop-blur">
                      <div className="text-[11px] font-bold text-slate-500 dark:text-slate-400">
                        الزوار الفريدون
                      </div>
                      <div className="mt-1 flex items-baseline justify-between">
                        <span className="font-latin text-2xl font-black text-brand dark:text-brand-light">
                          {(currentPeriodUniques ?? 0).toLocaleString()}
                        </span>
                        <span className="text-[10px] text-slate-400 font-bold">
                          زائر فريد
                        </span>
                      </div>
                    </div>

                    <div className="rounded-2xl border border-slate-200/80 bg-white/80 p-4 shadow-sm dark:border-slate-800 dark:bg-surface-dark/80 backdrop-blur">
                      <div className="text-[11px] font-bold text-slate-500 dark:text-slate-400">
                        نسبة زوار الجوال
                      </div>
                      <div className="mt-1 flex items-baseline justify-between">
                        <span className="font-latin text-2xl font-black text-emerald-600 dark:text-emerald-400">
                          %{mobilePct}
                        </span>
                        <span className="text-[10px] text-slate-400">
                          {dev.mobile || 0} هاتف
                        </span>
                      </div>
                    </div>

                    <div className="rounded-2xl border border-slate-200/80 bg-white/80 p-4 shadow-sm dark:border-slate-800 dark:bg-surface-dark/80 backdrop-blur">
                      <div className="text-[11px] font-bold text-slate-500 dark:text-slate-400">
                        إجمالي الزيارات التراكمي
                      </div>
                      <div className="mt-1 flex items-baseline justify-between">
                        <span className="font-latin text-2xl font-black text-slate-900 dark:text-white">
                          {(s.total_visits ?? 0).toLocaleString()}
                        </span>
                        <span className="text-[10px] text-slate-400">
                          كافة الأوقات
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })()}

              {/* Time-Series Traffic Volume Bar Chart */}
              <div className="rounded-3xl border border-slate-200/80 bg-white/80 p-5 shadow-sm dark:border-slate-800 dark:bg-surface-dark/80 backdrop-blur">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3 dark:border-slate-800">
                  <div>
                    <h4 className="text-sm font-extrabold text-slate-900 dark:text-white">
                      مخطط حركة الزوار (Traffic Volume Chart)
                    </h4>
                    <p className="text-[11px] text-slate-400">
                      توزيع الزيارات حسب {analyticsPeriod === "day" ? "ساعات اليوم" : analyticsPeriod === "week" ? "أيام الأسبوع" : analyticsPeriod === "month" ? "أيام الشهر" : "أشهر السنة"}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                    <span className="flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-full bg-brand" />
                      إجمالي الزيارات
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
                      الزوار الفريدون
                    </span>
                  </div>
                </div>

                {/* Bars Container */}
                {(() => {
                  const chart = analyticsData.chart_data || [];
                  const maxV = Math.max(...chart.map((c) => c.visits || 0), 1);

                  return (
                    <div className="h-56 flex items-end gap-1.5 sm:gap-2 pt-6 pb-2 overflow-x-auto no-scrollbar">
                      {chart.map((point, idx) => {
                        const heightPct = Math.max(Math.round(((point.visits || 0) / maxV) * 100), 4);
                        const uniquesPct = Math.max(Math.round(((point.uniques || 0) / maxV) * 100), 2);

                        return (
                          <div
                            key={point.date || point.hour || point.month || idx}
                            className="flex flex-1 flex-col items-center justify-end h-full min-w-[20px] sm:min-w-[28px] group relative"
                          >
                            {/* Hover Tooltip */}
                            <div className="pointer-events-none absolute -top-12 z-20 hidden whitespace-nowrap rounded-lg bg-slate-900 px-2.5 py-1 text-[10px] font-bold text-white shadow-xl group-hover:block dark:bg-black">
                              <div>{point.label}</div>
                              <div className="text-brand-light">{point.visits} زيارة • {point.uniques} فريد</div>
                            </div>

                            {/* Bar Stack */}
                            <div className="w-full flex items-end justify-center h-full">
                              <div
                                style={{ height: `${heightPct}%` }}
                                className="w-full max-w-[22px] rounded-t-md bg-brand/20 dark:bg-brand/30 transition-all duration-300 relative overflow-hidden group-hover:bg-brand/40"
                              >
                                <div
                                  style={{ height: `${uniquesPct}%` }}
                                  className="absolute bottom-0 inset-x-0 rounded-t-md bg-brand transition-all duration-300"
                                />
                              </div>
                            </div>

                            {/* X-axis Label */}
                            <span className="mt-2 block truncate font-latin text-[9px] sm:text-[10px] text-slate-400 group-hover:text-slate-800 dark:group-hover:text-white">
                              {point.label}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  );
                })()}
              </div>

              {/* 2-Column Grid: Devices Breakdown + Top Visited Pages */}
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {/* Device Breakdown */}
                <div className="rounded-3xl border border-slate-200/80 bg-white/80 p-5 shadow-sm dark:border-slate-800 dark:bg-surface-dark/80 backdrop-blur">
                  <h4 className="mb-3 text-sm font-extrabold text-slate-900 dark:text-white">
                    توزيع الأجهزة والمنصات (Device Breakdown)
                  </h4>

                  {(() => {
                    const dev = analyticsData.device_stats || {};
                    const total = (dev.mobile || 0) + (dev.desktop || 0) + (dev.tablet || 0) || 1;
                    const mobPct = Math.round(((dev.mobile || 0) / total) * 100);
                    const deskPct = Math.round(((dev.desktop || 0) / total) * 100);
                    const tabPct = Math.round(((dev.tablet || 0) / total) * 100);

                    return (
                      <div className="space-y-3.5">
                        <div>
                          <div className="flex justify-between text-xs font-bold text-slate-700 dark:text-slate-200 mb-1">
                            <span className="flex items-center gap-1.5">
                              <svg className="h-3.5 w-3.5 text-brand" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <rect x="5" y="2" width="14" height="20" rx="2" ry="2" />
                                <path d="M12 18h.01" />
                              </svg>
                              الهواتف الذكية (Mobile)
                            </span>
                            <span className="font-latin">%{mobPct} ({dev.mobile || 0})</span>
                          </div>
                          <div className="h-2 w-full rounded-full bg-slate-100 dark:bg-surface-dark-raised overflow-hidden">
                            <div style={{ width: `${mobPct}%` }} className="h-full rounded-full bg-brand transition-all duration-500" />
                          </div>
                        </div>

                        <div>
                          <div className="flex justify-between text-xs font-bold text-slate-700 dark:text-slate-200 mb-1">
                            <span className="flex items-center gap-1.5">
                              <svg className="h-3.5 w-3.5 text-emerald-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                                <path d="M8 21h8M12 17v4" />
                              </svg>
                              أجهزة الكمبيوتر (Desktop)
                            </span>
                            <span className="font-latin">%{deskPct} ({dev.desktop || 0})</span>
                          </div>
                          <div className="h-2 w-full rounded-full bg-slate-100 dark:bg-surface-dark-raised overflow-hidden">
                            <div style={{ width: `${deskPct}%` }} className="h-full rounded-full bg-emerald-500 transition-all duration-500" />
                          </div>
                        </div>

                        <div>
                          <div className="flex justify-between text-xs font-bold text-slate-700 dark:text-slate-200 mb-1">
                            <span className="flex items-center gap-1.5">
                              <svg className="h-3.5 w-3.5 text-amber-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <rect x="4" y="2" width="16" height="20" rx="2" />
                                <path d="M12 18h.01" />
                              </svg>
                              الأجهزة اللوحية (Tablet)
                            </span>
                            <span className="font-latin">%{tabPct} ({dev.tablet || 0})</span>
                          </div>
                          <div className="h-2 w-full rounded-full bg-slate-100 dark:bg-surface-dark-raised overflow-hidden">
                            <div style={{ width: `${tabPct}%` }} className="h-full rounded-full bg-amber-500 transition-all duration-500" />
                          </div>
                        </div>
                      </div>
                    );
                  })()}
                </div>

                {/* Top Visited Pages */}
                <div className="rounded-3xl border border-slate-200/80 bg-white/80 p-5 shadow-sm dark:border-slate-800 dark:bg-surface-dark/80 backdrop-blur">
                  <h4 className="mb-3 text-sm font-extrabold text-slate-900 dark:text-white">
                    أكثر الصفحات والمباريات زيارة
                  </h4>

                  {(() => {
                    const pages = analyticsData.top_pages || [];
                    if (pages.length === 0) {
                      return (
                        <p className="py-8 text-center text-xs text-slate-400">
                          لا توجد بيانات تصفح مسجلة لهذه الفترة
                        </p>
                      );
                    }

                    return (
                      <div className="space-y-2">
                        {pages.map((p, idx) => (
                          <div
                            key={p.path || idx}
                            className="flex items-center justify-between rounded-xl border border-slate-100 bg-slate-50/70 p-2.5 text-xs dark:border-slate-800 dark:bg-surface-dark-raised"
                          >
                            <span className="truncate font-latin font-bold text-slate-800 dark:text-slate-200 max-w-[200px]" dir="ltr">
                              {p.path}
                            </span>
                            <div className="flex items-center gap-2">
                              <span className="rounded-full bg-brand/10 px-2 py-0.5 font-latin font-bold text-brand dark:bg-brand/20 dark:text-brand-light text-[11px]">
                                {p.visits} زيارة
                              </span>
                              <span className="rounded-full bg-slate-200 px-2 py-0.5 font-latin text-slate-600 dark:bg-slate-700 dark:text-slate-300 text-[10px]">
                                {p.uniques} فريد
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    );
                  })()}
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* =========================================================================
          TAB 4: SYSTEM OVERVIEW & DIAGNOSTICS
         ========================================================================= */}
      {adminTab === "overview" && (
        <div className="space-y-4">
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-surface-dark">
            <h3 className="mb-4 text-base font-extrabold text-slate-900 dark:text-white">
              تشخيص واستقرار النظام (System Diagnostics)
            </h3>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <div className="rounded-2xl border border-slate-100 bg-slate-50/70 p-4 dark:border-slate-800 dark:bg-surface-dark-raised">
                <div className="text-xs font-bold text-slate-400">قاعدة البيانات المحلية</div>
                <div className="mt-1 font-latin text-sm font-extrabold text-slate-800 dark:text-slate-200">
                  SQLite (data/live_score.db)
                </div>
                <div className="mt-2 text-[11px] text-emerald-600 dark:text-emerald-400">
                  الجداول: admin_overrides, admin_streams, ads
                </div>
              </div>

              <div className="rounded-2xl border border-slate-100 bg-slate-50/70 p-4 dark:border-slate-800 dark:bg-surface-dark-raised">
                <div className="text-xs font-bold text-slate-400">خادم الواجهة الخلفية</div>
                <div className="mt-1 font-latin text-sm font-extrabold text-slate-800 dark:text-slate-200">
                  FastAPI + Uvicorn (Port 8000)
                </div>
                <div className="mt-2 text-[11px] text-emerald-600 dark:text-emerald-400">
                  الحالة: استجابة فورية (Live)
                </div>
              </div>

              <div className="rounded-2xl border border-slate-100 bg-slate-50/70 p-4 dark:border-slate-800 dark:bg-surface-dark-raised">
                <div className="text-xs font-bold text-slate-400">محرك بث ومطابقة الروابط</div>
                <div className="mt-1 font-latin text-sm font-extrabold text-slate-800 dark:text-slate-200">
                  Embed Extractor Engine
                </div>
                <div className="mt-2 text-[11px] text-blue-600 dark:text-blue-400">
                  يدعم فك تضمين بلوجر ومواقع البث تلقائياً
                </div>
              </div>
            </div>

            <div className="mt-6 rounded-2xl border border-slate-200/80 bg-slate-50 p-4 text-xs dark:border-slate-800 dark:bg-slate-900/50">
              <span className="font-bold text-slate-700 dark:text-slate-300">ملاحظة أمنية:</span>
              <p className="mt-1 text-slate-500 dark:text-slate-400">
                جلسة الإشراف الحالية مشفرة بـ Header: X-Admin-Token ومحفوظة في SessionStorage. تنتهي الصلاحية عند إغلاق التبويب أو النقر على تسجيل الخروج.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
