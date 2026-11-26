import { useEffect, useRef, useState } from "react";
import { fetchActiveAds } from "../lib/api";

export default function AdSlot({
  position,
  device,
  className = "",
  onDismiss,
}) {
  const [ad, setAd] = useState(null);
  const [dismissed, setDismissed] = useState(() => {
    if (position === "sticky_bottom" && typeof window !== "undefined") {
      try {
        return window.sessionStorage.getItem("kora_sticky_ad_dismissed") === "true";
      } catch (e) {
        return false;
      }
    }
    return false;
  });
  const [loading, setLoading] = useState(true);
  const htmlContainerRef = useRef(null);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();

    async function loadAd() {
      try {
        setLoading(true);
        const res = await fetchActiveAds({ position, device, signal: controller.signal });
        if (active) {
          if (res?.ads && res.ads.length > 0) {
            setAd(res.ads[0]);
          } else {
            setAd(null);
          }
        }
      } catch (err) {
        if (active && err.name !== "AbortError") {
          setAd(null);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadAd();

    return () => {
      active = false;
      controller.abort();
    };
  }, [position, device]);

  // Execute embedded scripts when custom_html is rendered
  useEffect(() => {
    if (!ad || ad.ad_type !== "custom_html" || !htmlContainerRef.current) return;
    const scripts = htmlContainerRef.current.querySelectorAll("script");
    scripts.forEach((oldScript) => {
      const newScript = document.createElement("script");
      Array.from(oldScript.attributes).forEach((attr) => {
        newScript.setAttribute(attr.name, attr.value);
      });
      newScript.textContent = oldScript.textContent;
      oldScript.parentNode?.replaceChild(newScript, oldScript);
    });
  }, [ad]);

  if (dismissed || !ad) {
    return null;
  }

  const deviceClass =
    ad.target_device === "mobile"
      ? "md:hidden block"
      : ad.target_device === "desktop"
      ? "hidden md:block"
      : "";

  const handleDismiss = () => {
    setDismissed(true);
    if (position === "sticky_bottom" && typeof window !== "undefined") {
      try {
        window.sessionStorage.setItem("kora_sticky_ad_dismissed", "true");
      } catch (e) {}
    }
    if (onDismiss) onDismiss();
  };

  const isSticky = position === "sticky_bottom";

  return (
    <div
      data-testid={`ad-slot-${position}`}
      dir="rtl"
      className={`relative w-full overflow-hidden transition-all duration-200 ${
        isSticky
          ? "fixed bottom-0 inset-x-0 z-40 bg-slate-900/95 border-t border-slate-700/60 p-2.5 backdrop-blur shadow-2xl flex items-center justify-center"
          : "my-3.5"
      } ${deviceClass} ${className}`.trim()}
    >
      <div className={`relative w-full ${isSticky ? "max-w-4xl mx-auto" : ""}`}>
        {/* Ad Header / Sponsor Badge & Dismiss */}
        <div className="flex items-center justify-between mb-1.5 px-1">
          <span className="text-[10px] tracking-wider text-slate-400/90 font-medium px-1.5 py-0.5 rounded bg-slate-800/80 border border-slate-700/50">
            إعلان
          </span>
          {isSticky && (
            <button
              type="button"
              onClick={handleDismiss}
              aria-label="إغلاق الإعلان"
              className="p-1 text-slate-400 hover:text-white rounded-md bg-slate-800/80 hover:bg-slate-700 border border-slate-700/50 transition-colors"
            >
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Ad Content */}
        {ad.ad_type === "image_banner" ? (
          <div className="flex justify-center">
            {ad.link_url ? (
              <a
                href={ad.link_url}
                target="_blank"
                rel="noopener noreferrer nofollow"
                className="block max-w-full group"
              >
                <img
                  src={ad.image_url}
                  alt={ad.title || "إعلان"}
                  className="rounded-xl w-full object-cover max-h-48 border border-slate-800/70 shadow-md group-hover:opacity-95 transition-opacity"
                  loading="lazy"
                />
              </a>
            ) : (
              <img
                src={ad.image_url}
                alt={ad.title || "إعلان"}
                className="rounded-xl w-full object-cover max-h-48 border border-slate-800/70 shadow-md"
                loading="lazy"
              />
            )}
          </div>
        ) : (
          <div
            ref={htmlContainerRef}
            className="flex justify-center overflow-x-auto text-center"
            dangerouslySetInnerHTML={{ __html: ad.html_code }}
          />
        )}
      </div>
    </div>
  );
}
