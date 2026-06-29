import { CircleDot } from "lucide-react";

// Highly visible "Posted Today" badge — a priority feature of the product.
export default function PostedTodayBadge({ className = "" }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-200 ${className}`}
    >
      <CircleDot className="h-3 w-3 animate-pulse" strokeWidth={2.5} />
      Posted Today
    </span>
  );
}
