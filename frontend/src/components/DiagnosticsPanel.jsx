import { Activity, AlertTriangle, Search, Layers, Tag } from "lucide-react";
import SourceStatusCard from "./SourceStatusCard.jsx";
import { categoryLabel } from "../constants/categories.js";

function ChipList({ icon: Icon, title, items, render, empty }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
      <div className="mb-3 flex items-center gap-2">
        <Icon className="h-4 w-4 text-indigo-600" />
        <h3 className="font-display text-sm font-semibold text-slate-800">{title}</h3>
      </div>
      {items && items.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {items.map((it, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1.5 rounded-full bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-700 ring-1 ring-inset ring-slate-200"
            >
              {render(it)}
            </span>
          ))}
        </div>
      ) : (
        <p className="text-xs text-slate-400">{empty}</p>
      )}
    </div>
  );
}

function formatTime(iso) {
  if (!iso) return "never";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "unknown" : d.toLocaleString();
}

function CardSkeleton() {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
      <div className="mb-4 flex items-center justify-between">
        <div className="h-4 w-24 animate-pulse rounded bg-slate-200" />
        <div className="h-5 w-16 animate-pulse rounded-full bg-slate-100" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-6 animate-pulse rounded bg-slate-100" />
        ))}
      </div>
      <div className="mt-4 h-9 animate-pulse rounded-xl bg-slate-100" />
    </div>
  );
}

export default function DiagnosticsPanel({ diagnostics, loading, unavailable, onRefresh }) {
  // Section header is always shown for context.
  const header = (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-2">
        <Activity className="h-5 w-5 text-indigo-600" />
        <h2 className="font-display text-xl font-semibold text-slate-900">
          Source Diagnostics
        </h2>
      </div>
      <p className="text-sm text-slate-500">
        See what each source returned and why jobs were accepted or rejected.
      </p>
    </div>
  );

  if (unavailable) {
    return (
      <div className="space-y-5">
        {header}
        <div className="flex items-center gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-700">
          <AlertTriangle className="h-5 w-5 shrink-0" />
          Diagnostics endpoint not available yet. The rest of the app works normally.
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="space-y-5">
        {header}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (!diagnostics || !diagnostics.sources?.length) {
    return (
      <div className="space-y-5">
        {header}
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-500">
          No diagnostics yet. Click{" "}
          <span className="font-semibold text-slate-700">Refresh Jobs</span> to run the
          scraper and collect source diagnostics.
        </div>
      </div>
    );
  }

  const { sources } = diagnostics;
  const active = sources.filter((s) => s.enabled);
  const inactive = sources.filter((s) => !s.enabled);

  return (
    <div className="space-y-5">
      {header}

      {/* Summary bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white px-5 py-3.5 text-sm shadow-card">
        <span className="text-slate-600">
          Last run <span className="font-semibold text-slate-800">#{diagnostics.run_id}</span>{" "}
          · {formatTime(diagnostics.last_run_at)}
        </span>
        <div className="flex gap-5">
          <span className="text-slate-600">
            Raw fetched:{" "}
            <span className="font-mono font-semibold text-slate-800">
              {diagnostics.total_raw}
            </span>
          </span>
          <span className="text-slate-600">
            Saved:{" "}
            <span className="font-mono font-semibold text-emerald-600">
              {diagnostics.total_saved}
            </span>
          </span>
        </div>
      </div>

      {/* Multi-stack coverage roll-ups */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <ChipList
          icon={Search}
          title="Top successful queries"
          items={diagnostics.top_successful_queries}
          empty="No saved jobs yet — run the scraper."
          render={(q) => (
            <>
              {q.query}
              <span className="font-mono text-emerald-600">{q.saved}</span>
            </>
          )}
        />
        <ChipList
          icon={Layers}
          title="Top categories found"
          items={diagnostics.top_categories_found}
          empty="No categories detected yet."
          render={(c) => (
            <>
              {categoryLabel(c.category)}
              <span className="font-mono text-indigo-600">{c.count}</span>
            </>
          )}
        />
        <ChipList
          icon={Tag}
          title="Top keywords found"
          items={diagnostics.top_keywords_found}
          empty="No keywords detected yet."
          render={(k) => (
            <>
              {k.keyword}
              <span className="font-mono text-violet-600">{k.count}</span>
            </>
          )}
        />
      </div>

      <div>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Active sources (attempted)
        </h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {active.map((d) => (
            <SourceStatusCard key={d.source_name} d={d} />
          ))}
        </div>
      </div>

      {inactive.length > 0 && (
        <div>
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Blocked / skipped sources (with reasons)
          </h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {inactive.map((d) => (
              <SourceStatusCard key={d.source_name} d={d} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
