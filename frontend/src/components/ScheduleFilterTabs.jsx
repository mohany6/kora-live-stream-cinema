export const SCHEDULE_TABS = [
  { key: "yesterday", label: "مباريات الأمس", offset: -1 },
  { key: "today", label: "مباريات اليوم", offset: 0 },
  { key: "tomorrow", label: "مباريات الغد", offset: 1 },
];

export default function ScheduleFilterTabs({ activeTab = "today", onTabChange }) {
  return (
    <nav
      role="tablist"
      aria-label="تصفية المباريات حسب اليوم"
      dir="rtl"
      className="no-scrollbar flex w-full items-center gap-2 overflow-x-auto rounded-2xl border border-slate-200/70 bg-white/70 p-1.5 dark:border-slate-700/60 dark:bg-surface-dark/70 sm:w-auto"
    >
      {SCHEDULE_TABS.map((tab) => {
        const active = tab.key === activeTab;
        return (
          <button
            key={tab.key}
            type="button"
            role="tab"
            aria-selected={active}
            data-testid={`schedule-tab-${tab.key}`}
            onClick={() => onTabChange?.(tab.key)}
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
    </nav>
  );
}
