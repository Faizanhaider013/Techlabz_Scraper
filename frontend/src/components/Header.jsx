import { Activity, LayoutGrid, RefreshCw } from "lucide-react";
import clsx from "clsx";
import Button from "./Button.jsx";

function formatTime(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? null
    : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function Header({
  onRefresh,
  refreshing,
  view,
  setView,
  lastRefreshed,
}) {
  const time = formatTime(lastRefreshed);
  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3.5 sm:px-6 lg:px-8">
        {/* Brand */}
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-blue-500 shadow-sm">
            <LayoutGrid className="h-5 w-5 text-white" strokeWidth={2.25} />
          </div>
          <div className="min-w-0">
            <h1 className="truncate font-display text-[15px] font-bold leading-tight tracking-tight text-slate-900 sm:text-base">
              ServiceNow Remote US Jobs Today
            </h1>
            <p className="hidden truncate text-xs text-slate-500 sm:block">
              Real, recent ServiceNow remote US roles — strictly filtered.
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex shrink-0 items-center gap-2">
          {time && (
            <span className="mr-1 hidden text-xs text-slate-400 lg:inline">
              Updated {time}
            </span>
          )}
          <Button
            variant={view === "diagnostics" ? "secondary" : "outline"}
            size="md"
            onClick={() => setView(view === "diagnostics" ? "jobs" : "diagnostics")}
            className="hidden sm:inline-flex"
          >
            <Activity className="h-4 w-4" />
            {view === "diagnostics" ? "Job Board" : "Diagnostics"}
          </Button>
          <Button variant="primary" size="md" onClick={onRefresh} disabled={refreshing}>
            <RefreshCw className={clsx("h-4 w-4", refreshing && "animate-spin")} />
            <span className="hidden sm:inline">
              {refreshing ? "Refreshing…" : "Refresh Jobs"}
            </span>
          </Button>
        </div>
      </div>
    </header>
  );
}
