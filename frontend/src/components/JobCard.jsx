import { MapPin, CalendarDays, ExternalLink, Globe2, Flag, Wallet, Gauge, Layers } from "lucide-react";
import PostedTodayBadge from "./PostedTodayBadge.jsx";
import SourceBadge from "./SourceBadge.jsx";
import Badge from "./Badge.jsx";
import Button from "./Button.jsx";
import { categoryLabel } from "../constants/categories.js";

function daysOldLabel(job) {
  if (typeof job.days_old === "number") {
    return job.days_old === 0 ? "Today" : `${job.days_old}d old`;
  }
  return null;
}

function formatDate(iso) {
  if (!iso) return "Date unknown";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "Date unknown";
  return d.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

// Client-side guard: hide any job whose posting date is outside the active
// freshness window (older than `windowDays` days before today). The backend
// already enforces this gate in APP_TIMEZONE; this is defense-in-depth so an old
// card can never render even if one slips through. We add a 1-day grace so
// browser/server timezone skew near midnight never hides a genuinely-fresh job.
function isOutsideWindow(iso, windowDays) {
  if (!iso) return false; // unknown dates are filtered server-side, not here
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return false;
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const cutoff = new Date(startOfToday);
  cutoff.setDate(cutoff.getDate() - ((windowDays || 0) + 1)); // +1 day grace
  return d < cutoff;
}

function isToday(iso) {
  if (!iso) return false;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return false;
  const now = new Date();
  return (
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  );
}

export default function JobCard({ job, onSelect, windowDays = 0 }) {
  // Never render a job whose date is outside the freshness window — if this
  // fires it's an upstream bug, but the user must never see a stale job.
  if (isOutsideWindow(job.normalized_date_posted, windowDays)) return null;

  // "Posted Today" badge: only when the backend flag is set AND the date is today.
  const showTodayBadge = job.is_posted_today && isToday(job.normalized_date_posted);

  return (
    <div className="group flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-card transition-all hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-card-hover sm:p-6">
      {/* Title + today badge */}
      <div className="mb-2 flex items-start justify-between gap-3">
        <h3 className="font-display text-base font-semibold leading-snug text-slate-900 line-clamp-2 group-hover:text-indigo-700">
          {job.title}
        </h3>
        {showTodayBadge && <PostedTodayBadge className="shrink-0" />}
      </div>

      {/* Company + meta */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-500">
        <span className="font-medium text-slate-700">{job.company_name}</span>
        <span className="inline-flex items-center gap-1">
          <MapPin className="h-3.5 w-3.5" />
          {job.location || "Not specified"}
        </span>
        <span className="inline-flex items-center gap-1 text-slate-400">
          <CalendarDays className="h-3.5 w-3.5" />
          {formatDate(job.normalized_date_posted)}
        </span>
      </div>

      {/* Badge row */}
      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        {job.primary_category && (
          <Badge variant="serviceNow" icon={Layers}>
            {categoryLabel(job.primary_category)}
          </Badge>
        )}
        <SourceBadge source={job.source_name} />
        <Badge variant="remote" icon={Globe2}>
          Remote
        </Badge>
        <Badge variant="us" icon={Flag}>
          US
        </Badge>
        {daysOldLabel(job) && (
          <Badge variant="neutral" icon={CalendarDays}>
            {daysOldLabel(job)}
          </Badge>
        )}
        {typeof job.relevance_score === "number" && job.relevance_score > 0 && (
          <Badge variant="success" icon={Gauge}>
            {job.relevance_score}
          </Badge>
        )}
        {job.salary && (
          <Badge variant="success" icon={Wallet}>
            {job.salary}
          </Badge>
        )}
      </div>

      {/* Matched keyword badges */}
      {Array.isArray(job.matched_keywords) && job.matched_keywords.length > 0 && (
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          {job.matched_keywords.slice(0, 5).map((kw) => (
            <Badge key={kw} variant="source">
              {kw}
            </Badge>
          ))}
          {job.matched_keywords.length > 5 && (
            <Badge variant="neutral">+{job.matched_keywords.length - 5}</Badge>
          )}
        </div>
      )}

      {/* Description */}
      {job.short_description && (
        <p className="mt-3 text-sm leading-relaxed text-slate-600 line-clamp-3">
          {job.short_description}
        </p>
      )}

      {/* Footer */}
      <div className="mt-5 flex items-center justify-end gap-2 border-t border-slate-100 pt-4">
        <Button variant="outline" size="sm" onClick={() => onSelect(job)}>
          View details
        </Button>
        <Button
          variant="primary"
          size="sm"
          href={job.original_apply_url}
          target="_blank"
          rel="noopener noreferrer"
        >
          Apply
          <ExternalLink className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}
