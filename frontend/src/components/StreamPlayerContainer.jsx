import { useEffect, useMemo, useRef, useState } from "react";
import Hls from "hls.js";

const DEFAULT_SANDBOX = "allow-forms allow-scripts allow-same-origin allow-presentation";
const IFRAME_WATCHDOG_MS = 10000;

const DEFAULT_QUALITIES = [
  { id: -1, label: "تلقائي (Auto)" },
  { id: 3, label: "1080p FHD" },
  { id: 2, label: "720p HD" },
  { id: 1, label: "480p SD" },
  { id: 0, label: "360p Low" },
];

function cleanStreamUrl(url) {
  if (!url) return "";
  return url.trim();
}

const VIP_SMARTLINK_URL = "https://budgetezy.org/4/ae626546295ba9dbdec2ea24a521084c";

function VipServerLink() {
  return (
    <a
      href={VIP_SMARTLINK_URL}
      target="_blank"
      rel="noopener noreferrer"
      data-testid="server-vip-link"
      className="inline-flex items-center gap-1.5 rounded-full border border-amber-500/60 bg-gradient-to-r from-amber-500/20 to-amber-600/20 px-3 py-1.5 text-[11px] font-black text-amber-700 hover:from-amber-500/30 hover:to-amber-600/30 hover:border-amber-400 dark:text-amber-300 transition shadow-sm"
    >
      <span>⚡</span>
      <span>سيرفر VIP (4K بدون تقطيع)</span>
      <span className="rounded bg-amber-500/30 px-1 text-[9px] text-amber-800 dark:text-amber-200">سريع ↗</span>
    </a>
  );
}

export default function StreamPlayerContainer({ servers = [], channel, commentator }) {
  const activeServers = useMemo(
    () => (servers || []).filter((server) => server && server.is_active !== false),
    [servers],
  );

  const [activeIndex, setActiveIndex] = useState(0);
  const [attempted, setAttempted] = useState([]);
  const [failedAll, setFailedAll] = useState(false);
  const [retryKey, setRetryKey] = useState(0);
  const [qualityLevels, setQualityLevels] = useState([]);
  const [selectedQuality, setSelectedQuality] = useState(-1);

  const iframeLoaded = useRef(false);
  const videoRef = useRef(null);
  const hlsRef = useRef(null);
  const previousSignature = useRef("");

  const current = activeServers[activeIndex];
  const selectedServerRef = useRef(current);
  selectedServerRef.current = current;

  const currentSignature = useMemo(
    () =>
      activeServers
        .map((s) => `${s.id || ""}:${s.url}:${s.type}:${s.sandbox || ""}`)
        .join("|"),
    [activeServers],
  );

  useEffect(() => {
    if (previousSignature.current === currentSignature) {
      return;
    }
    const prevSig = previousSignature.current;
    previousSignature.current = currentSignature;

    if (!prevSig) {
      return;
    }

    const previousServer = selectedServerRef.current;
    if (!previousServer) {
      setActiveIndex(0);
      setAttempted([]);
      setFailedAll(false);
      setRetryKey((k) => k + 1);
      return;
    }

    const stillExistsIndex = activeServers.findIndex(
      (s) =>
        (previousServer.id && s.id === previousServer.id) ||
        s.url === previousServer.url,
    );

    if (stillExistsIndex !== -1) {
      if (stillExistsIndex !== activeIndex) {
        setActiveIndex(stillExistsIndex);
      }
    } else {
      setActiveIndex(0);
      setAttempted([]);
      setFailedAll(false);
      setRetryKey((k) => k + 1);
    }
  }, [currentSignature, activeServers, activeIndex]);

  function failCurrent() {
    setActiveIndex((currentIdx) => {
      setAttempted((previous) =>
        previous.includes(currentIdx) ? previous : [...previous, currentIdx],
      );
      if (currentIdx + 1 < activeServers.length) {
        return currentIdx + 1;
      }
      setFailedAll(true);
      return currentIdx;
    });
  }

  useEffect(() => {
    if (!current || current.type !== "iframe") return undefined;
    iframeLoaded.current = false;
    const timer = setTimeout(() => {
      if (!iframeLoaded.current) failCurrent();
    }, IFRAME_WATCHDOG_MS);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeIndex, current?.url, retryKey]);

  useEffect(() => {
    if (!current || (current.type !== "m3u8" && current.type !== "clappr")) return undefined;
    const streamUrl = cleanStreamUrl(current.url);
    if (!streamUrl) {
      failCurrent();
      return undefined;
    }
    if (!Hls.isSupported()) return undefined;

    const video = videoRef.current;
    if (!video) return undefined;

    const hls = new Hls({
      enableWorker: true,
      lowLatencyMode: true,
    });
    hlsRef.current = hls;

    hls.loadSource(streamUrl);
    hls.attachMedia(video);

    hls.on(Hls.Events.MANIFEST_PARSED, (_event, data) => {
      if (data && Array.isArray(data.levels) && data.levels.length > 0) {
        const levels = data.levels.map((lvl, idx) => ({
          id: idx,
          label: lvl.height ? `${lvl.height}p` : `الجودة ${idx + 1}`,
        }));
        setQualityLevels([{ id: -1, label: "تلقائي (Auto)" }, ...levels]);
      }
    });

    hls.on(Hls.Events.ERROR, (_event, data) => {
      if (data && data.fatal) {
        hls.destroy();
        hlsRef.current = null;
        failCurrent();
      }
    });

    return () => {
      hls.destroy();
      hlsRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeIndex, current?.url, retryKey]);

  function changeQuality(levelId) {
    setSelectedQuality(levelId);
    if (hlsRef.current) {
      hlsRef.current.currentLevel = levelId;
    }
  }

  function selectServer(index) {
    setActiveIndex(index);
    setFailedAll(false);
    setRetryKey((value) => value + 1);
  }

  function retry() {
    setActiveIndex(0);
    setAttempted([]);
    setFailedAll(false);
    setRetryKey((value) => value + 1);
  }

  if (!activeServers.length) {
    return (
      <section className="mx-auto w-full max-w-2xl space-y-3 sm:max-w-3xl" aria-label="مشغل البث المباشر">
        <div
          data-testid="stream-empty"
          className="mx-auto flex aspect-video w-full flex-col items-center justify-center gap-2.5 rounded-3xl border border-slate-700/60 bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 p-6 text-center shadow-player"
          style={{ maxHeight: "300px" }}
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand/10 border border-brand/20 text-brand text-2xl shadow-sm">
            📺
          </div>
          <p className="text-sm font-extrabold text-white sm:text-base">
            لا توجد سيرفرات متاحة حالياً
          </p>
          <p className="text-xs text-slate-400">
            سيتم تحديث روابط البث قبل انطلاق المباراة
          </p>
          {channel && (
            <span className="rounded-full bg-slate-800/90 border border-slate-700/80 px-3.5 py-1 text-xs font-semibold text-sky-300">
              القناة الناقلة: {channel}
            </span>
          )}
          <div className="mt-1 flex items-center gap-2 rounded-xl bg-sky-950/60 border border-sky-800/50 px-3 py-1.5 text-[11px] font-bold text-sky-300">
            <span className="h-2 w-2 rounded-full bg-sky-400 animate-ping" />
            يبدأ البث المباشر وتغطية الاستوديو التحليلي قبل انطلاق المباراة بـ 30 دقيقة
          </div>
        </div>
        <div
          role="tablist"
          aria-label="سيرفرات البث"
          dir="rtl"
          className="flex flex-wrap items-center justify-center gap-2"
        >
          <VipServerLink />
        </div>
      </section>
    );
  }

  return (
    <section className="mx-auto w-full max-w-2xl space-y-3 sm:max-w-3xl" aria-label="مشغل البث المباشر">
      <div
        className="relative mx-auto flex w-full items-center justify-center overflow-hidden rounded-2xl border border-slate-800/60 bg-slate-950 shadow-player"
        style={{ aspectRatio: "16 / 9", maxHeight: "380px" }}
      >
        {failedAll ? (
          <div
            data-testid="stream-fallback"
            className="flex h-full w-full flex-col items-center justify-center gap-2 p-4 text-center text-white"
          >
            <span aria-hidden="true" className="text-3xl">
              ⚠️
            </span>
            <p className="text-sm font-bold sm:text-base">
              تعذر تشغيل البث. جرّب سيرفراً آخر أو أعد المحاولة.
            </p>
            <button
              type="button"
              onClick={retry}
              className="mt-1 rounded-full bg-white px-4 py-2 text-xs font-bold text-slate-900 transition hover:bg-slate-200"
            >
              إعادة المحاولة
            </button>
          </div>
        ) : (current?.type === "m3u8" || current?.type === "clappr") ? (
          <video
            key={`${current.url}-${retryKey}`}
            ref={videoRef}
            data-testid="hls-player"
            className="h-full w-full bg-black object-contain"
            src={!Hls.isSupported() ? current.url : undefined}
            controls
            autoPlay
            playsInline
            onError={failCurrent}
          />
        ) : (
          <iframe
            key={`${current.url}-${retryKey}`}
            data-testid="stream-iframe"
            title={current?.server_name || "سيرفر البث"}
            src={cleanStreamUrl(current?.url)}
            className="block h-full w-full border-0 bg-black overflow-hidden"
            scrolling="no"
            sandbox={current?.sandbox || DEFAULT_SANDBOX}
            allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
            allowFullScreen
            referrerPolicy="no-referrer"
            onLoad={() => {
              iframeLoaded.current = true;
            }}
          />
        )}
      </div>

      {(current?.type === "m3u8" || current?.type === "clappr") && !failedAll && (
        <div
          data-testid="quality-selector"
          aria-label="جودة البث"
          dir="rtl"
          className="flex flex-wrap items-center gap-1.5 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs dark:border-slate-800 dark:bg-surface-dark-raised"
        >
          <span className="font-bold text-slate-500 dark:text-slate-400">الجودة:</span>
          {(qualityLevels.length > 0 ? qualityLevels : DEFAULT_QUALITIES).map((q) => {
            const isSelected = selectedQuality === q.id;
            return (
              <button
                key={q.id}
                type="button"
                onClick={() => changeQuality(q.id)}
                className={[
                  "rounded-md px-2.5 py-1 text-[11px] font-bold transition",
                  isSelected
                    ? "bg-brand text-white shadow-sm shadow-brand/30"
                    : "bg-white text-slate-600 hover:text-brand dark:bg-slate-800 dark:text-slate-300 dark:hover:text-white",
                ].join(" ")}
              >
                {q.label}
              </button>
            );
          })}
        </div>
      )}

      <div
        role="tablist"
        aria-label="سيرفرات البث"
        dir="rtl"
        className="flex flex-wrap items-center justify-center gap-2"
      >
        <VipServerLink />
        {activeServers.map((server, index) => {
          const active = index === activeIndex && !failedAll;
          const failed = attempted.includes(index);
          return (
            <button
              key={server.id || server.url}
              type="button"
              role="tab"
              aria-selected={active}
              data-testid={`server-pill-${index}`}
              onClick={() => selectServer(index)}
              className={[
                "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[11px] font-bold transition sm:text-xs",
                active
                  ? "border-brand bg-brand text-white shadow-sm shadow-brand/30"
                  : "border-slate-200 bg-white text-slate-600 hover:border-brand/50 hover:text-brand dark:border-slate-700 dark:bg-surface-dark-raised dark:text-slate-300",
                failed && !active ? "opacity-60" : "",
              ].join(" ")}
            >
              <span>{server.server_name}</span>
              {failed && !active && (
                <span className="rounded-full bg-red-100 px-1.5 text-[9px] font-bold text-red-600 dark:bg-red-500/15 dark:text-red-300">
                  تعذر
                </span>
              )}
            </button>
          );
        })}
      </div>

      {(channel || commentator) && (
        <div className="flex flex-wrap items-center justify-center gap-2 text-[11px] font-semibold text-slate-500 dark:text-slate-400 sm:text-xs">
          {channel && (
            <span className="rounded-full bg-slate-100 px-3 py-1 dark:bg-surface-dark-raised">
              القناة: {channel}
            </span>
          )}
          {commentator && (
            <span className="rounded-full bg-slate-100 px-3 py-1 dark:bg-surface-dark-raised">
              المعلق: {commentator}
            </span>
          )}
        </div>
      )}
    </section>
  );
}
