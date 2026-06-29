import { CircleDot, Layers, CheckCircle2, CalendarDays } from "lucide-react";
import clsx from "clsx";

function StatCard({ icon: Icon, label, value, helper, iconClass, valueClass }) {
  return (
    <div className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-card transition-all hover:-translate-y-0.5 hover:shadow-card-hover">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {label}
        </p>
        <span
          className={clsx(
            "flex h-8 w-8 items-center justify-center rounded-lg ring-1 ring-inset",
            iconClass
          )}
        >
          <Icon className="h-4 w-4" strokeWidth={2.25} />
        </span>
      </div>
      <p
        className={clsx(
          "mt-3 font-mono text-3xl font-semibold tracking-tight tabular-nums",
          valueClass || "text-slate-900"
        )}
      >
        {value ?? "—"}
      </p>
      <p className="mt-1 text-xs text-slate-400">{helper}</p>
    </div>
  );
}

export default function StatsCards({ stats }) {
  const windowDays = stats?.window_days ?? 0;
  const recent = windowDays > 0;
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard
        icon={CircleDot}
        label="Total Recent Jobs"
        value={recent ? stats?.total_jobs : stats?.today_jobs}
        helper={
          recent
            ? `ServiceNow · Remote · US · last ${windowDays} days`
            : "ServiceNow · Remote · US · Today"
        }
        iconClass="bg-emerald-50 text-emerald-600 ring-emerald-100"
        valueClass="text-emerald-600"
      />
      <StatCard
        icon={CalendarDays}
        label="Posted Today"
        value={stats?.posted_today}
        helper="Posted today (strict)"
        iconClass="bg-amber-50 text-amber-600 ring-amber-100"
      />
      <StatCard
        icon={Layers}
        label="Categories"
        value={stats?.total_categories}
        helper="Tech categories with jobs"
        iconClass="bg-indigo-50 text-indigo-600 ring-indigo-100"
      />
      <StatCard
        icon={CheckCircle2}
        label="Sources Checked"
        value={stats?.sources_checked ?? stats?.sources_attempted}
        helper="Active sources attempted"
        iconClass="bg-sky-50 text-sky-600 ring-sky-100"
      />
    </div>
  );
}
