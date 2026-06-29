import {
  CheckCircle2,
  CircleAlert,
  Ban,
  XCircle,
  MinusCircle,
} from "lucide-react";
import clsx from "clsx";

const STATUS = {
  success: { label: "Success", badge: "bg-emerald-50 text-emerald-700 ring-emerald-200", icon: CheckCircle2 },
  no_results: { label: "No results", badge: "bg-amber-50 text-amber-700 ring-amber-200", icon: CircleAlert },
  blocked: { label: "Blocked", badge: "bg-rose-50 text-rose-700 ring-rose-200", icon: Ban },
  error: { label: "Error", badge: "bg-red-50 text-red-700 ring-red-200", icon: XCircle },
  skipped: { label: "Skipped", badge: "bg-slate-100 text-slate-500 ring-slate-200", icon: MinusCircle },
};

function FunnelStat({ label, value, accent, bar, pct }) {
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="text-[10px] uppercase tracking-wide text-slate-400">{label}</span>
        <span className={clsx("font-mono text-sm font-semibold tabular-nums", accent)}>
          {value}
        </span>
      </div>
      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-100">
        <div
          className={clsx("h-full rounded-full transition-all", bar)}
          style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
        />
      </div>
    </div>
  );
}

function formatTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleString();
}

export default function SourceStatusCard({ d }) {
  const meta = STATUS[d.status] || STATUS.skipped;
  const Icon = meta.icon;
  const note = d.error_message || d.reason;
  const base = Math.max(d.raw_count, 1);

  return (
    <div className="flex flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-card transition-all hover:shadow-card-hover">
      <div className="mb-4 flex items-center justify-between gap-2">
        <h3 className="font-display text-sm font-semibold text-slate-900">{d.source_name}</h3>
        <span
          className={clsx(
            "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset",
            meta.badge
          )}
        >
          <Icon className="h-3.5 w-3.5" />
          {meta.label}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-x-5 gap-y-3">
        <FunnelStat label="Raw" value={d.raw_count} accent="text-slate-600" bar="bg-slate-400" pct={100} />
        <FunnelStat
          label="ServiceNow"
          value={d.servicenow_count}
          accent="text-indigo-600"
          bar="bg-indigo-500"
          pct={(d.servicenow_count / base) * 100}
        />
        <FunnelStat
          label="Remote"
          value={d.remote_count}
          accent="text-sky-600"
          bar="bg-sky-500"
          pct={(d.remote_count / base) * 100}
        />
        <FunnelStat
          label="US"
          value={d.us_count}
          accent="text-blue-600"
          bar="bg-blue-500"
          pct={(d.us_count / base) * 100}
        />
      </div>

      <div className="mt-4 flex items-center justify-between rounded-xl bg-emerald-50 px-3 py-2 ring-1 ring-inset ring-emerald-100">
        <span className="text-xs font-medium text-emerald-700">Saved</span>
        <span className="font-mono text-base font-semibold text-emerald-700 tabular-nums">
          {d.saved_count}
        </span>
      </div>

      {(d.rejected_non_servicenow + d.rejected_non_remote + d.rejected_non_us) > 0 && (
        <div className="mt-3 flex flex-wrap gap-1 text-[11px] text-slate-500">
          <span className="rounded bg-slate-100 px-1.5 py-0.5">
            ✕ ServiceNow {d.rejected_non_servicenow}
          </span>
          <span className="rounded bg-slate-100 px-1.5 py-0.5">
            ✕ remote {d.rejected_non_remote}
          </span>
          <span className="rounded bg-slate-100 px-1.5 py-0.5">✕ US {d.rejected_non_us}</span>
          {d.duplicate_count > 0 && (
            <span className="rounded bg-slate-100 px-1.5 py-0.5">dupes {d.duplicate_count}</span>
          )}
        </div>
      )}

      {note && (
        <p
          className="mt-3 line-clamp-2 rounded-lg bg-rose-50/60 px-2.5 py-1.5 text-xs text-rose-600"
          title={note}
        >
          {note}
        </p>
      )}

      {d.near_matches?.length > 0 && (
        <details className="mt-3 text-xs">
          <summary className="cursor-pointer font-medium text-indigo-600 hover:text-indigo-700">
            {d.near_matches.length} ServiceNow near-match(es)
          </summary>
          <ul className="mt-1.5 space-y-1 text-slate-500">
            {d.near_matches.map((n, i) => (
              <li key={i} className="truncate" title={n}>
                • {n}
              </li>
            ))}
          </ul>
        </details>
      )}

      <p className="mt-3 border-t border-slate-100 pt-2 text-[11px] text-slate-400">
        Last run: {formatTime(d.last_run_at)}
      </p>
    </div>
  );
}
