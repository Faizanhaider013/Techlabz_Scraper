import clsx from "clsx";

const VARIANTS = {
  serviceNow: "bg-indigo-50 text-indigo-700 ring-indigo-100",
  remote: "bg-sky-50 text-sky-700 ring-sky-100",
  us: "bg-blue-50 text-blue-700 ring-blue-100",
  today: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  source: "bg-violet-50 text-violet-700 ring-violet-100",
  neutral: "bg-slate-100 text-slate-600 ring-slate-200",
  success: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  warning: "bg-amber-50 text-amber-700 ring-amber-200",
  danger: "bg-rose-50 text-rose-700 ring-rose-200",
};

export default function Badge({ variant = "neutral", className, icon: Icon, children }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
        VARIANTS[variant],
        className
      )}
    >
      {Icon && <Icon className="h-3 w-3" strokeWidth={2.25} />}
      {children}
    </span>
  );
}
