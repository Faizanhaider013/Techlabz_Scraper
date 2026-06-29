import { SearchX, RefreshCw, Activity } from "lucide-react";
import clsx from "clsx";
import Button from "./Button.jsx";

// Premium empty state. Explains *why* there are no jobs and offers next steps.
// Never shows fake jobs.
export default function EmptyState({
  title = "No ServiceNow Remote US jobs posted today were found yet.",
  message = "The scraper checked active sources, but no jobs passed Today + ServiceNow + Remote + United States filters.",
  onRefresh,
  onViewDiagnostics,
  refreshing = false,
}) {
  return (
    <div className="relative overflow-hidden rounded-3xl border border-dashed border-slate-300 bg-gradient-to-b from-white to-slate-50 px-6 py-16 text-center">
      <div
        aria-hidden
        className="pointer-events-none absolute left-1/2 top-0 h-40 w-40 -translate-x-1/2 rounded-full bg-indigo-100/50 blur-3xl"
      />
      <div className="relative mx-auto flex max-w-md flex-col items-center">
        <div className="mb-5 flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-indigo-100 to-blue-100 ring-1 ring-inset ring-indigo-200/60">
          <SearchX className="h-9 w-9 text-indigo-600" strokeWidth={1.75} />
        </div>
        <h3 className="font-display text-xl font-semibold text-slate-900">{title}</h3>
        <p className="mt-2 text-sm leading-relaxed text-slate-500">{message}</p>

        {(onRefresh || onViewDiagnostics) && (
          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            {onRefresh && (
              <Button variant="primary" size="lg" onClick={onRefresh} disabled={refreshing}>
                <RefreshCw className={clsx("h-4 w-4", refreshing && "animate-spin")} />
                {refreshing ? "Refreshing…" : "Refresh today jobs"}
              </Button>
            )}
            {onViewDiagnostics && (
              <Button variant="outline" size="lg" onClick={onViewDiagnostics}>
                <Activity className="h-4 w-4" />
                View diagnostics
              </Button>
            )}
          </div>
        )}

        <p className="mt-5 text-xs text-slate-400">
          This is better than showing unrelated jobs.
        </p>
      </div>
    </div>
  );
}
