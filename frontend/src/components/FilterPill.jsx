import clsx from "clsx";

// A single selectable pill (used for date filters).
export default function FilterPill({ active, children, ...props }) {
  return (
    <button
      type="button"
      className={clsx(
        "rounded-full px-3.5 py-1.5 text-sm font-medium transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500",
        active
          ? "bg-indigo-600 text-white shadow-sm"
          : "bg-slate-100 text-slate-700 hover:bg-slate-200"
      )}
      {...props}
    >
      {children}
    </button>
  );
}
