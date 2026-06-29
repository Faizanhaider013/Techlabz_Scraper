import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  MapPin,
  CalendarDays,
  ExternalLink,
  Globe2,
  Flag,
  Briefcase,
  Wallet,
  Tag,
  Gauge,
  Search,
  Layers,
} from "lucide-react";
import { api } from "../services/api.js";
import PostedTodayBadge from "./PostedTodayBadge.jsx";
import SourceBadge from "./SourceBadge.jsx";
import Badge from "./Badge.jsx";
import Button from "./Button.jsx";
import { categoryLabel } from "../constants/categories.js";

function formatDate(iso) {
  if (!iso) return "Date unknown";
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? "Date unknown"
    : d.toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
}

function MetaItem({ icon: Icon, label, value }) {
  return (
    <div className="flex items-start gap-2.5">
      <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-500">
        <Icon className="h-4 w-4" />
      </span>
      <div className="min-w-0">
        <dt className="text-xs text-slate-400">{label}</dt>
        <dd className="truncate text-sm font-medium text-slate-700">{value || "—"}</dd>
      </div>
    </div>
  );
}

export default function JobDetailModal({ jobId, onClose }) {
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    api
      .getJob(jobId)
      .then((d) => active && setJob(d))
      .catch((e) => active && setError(e.message))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [jobId]);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  return createPortal(
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/40 p-0 backdrop-blur-sm sm:items-center sm:p-4"
        onClick={onClose}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.18 }}
      >
        <motion.div
          className="flex max-h-[92vh] w-full max-w-3xl flex-col overflow-hidden rounded-t-3xl bg-white shadow-2xl sm:rounded-3xl"
          onClick={(e) => e.stopPropagation()}
          initial={{ opacity: 0, y: 28, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.98 }}
          transition={{ type: "spring", stiffness: 320, damping: 30 }}
        >
          {/* Header */}
          <div className="flex items-start justify-between gap-3 border-b border-slate-100 px-6 py-5">
            <div className="min-w-0">
              {loading ? (
                <div className="h-7 w-56 animate-pulse rounded bg-slate-200" />
              ) : (
                <h2 className="font-display text-xl font-bold leading-tight text-slate-900">
                  {job?.title}
                </h2>
              )}
              {job && (
                <p className="mt-1 text-sm font-medium text-slate-600">
                  {job.company_name}
                </p>
              )}
            </div>
            <button
              onClick={onClose}
              aria-label="Close"
              className="rounded-full p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Body */}
          <div className="scrollbar-soft flex-1 overflow-y-auto px-6 py-5">
            {error && (
              <p className="rounded-xl bg-rose-50 p-3 text-sm text-rose-600">
                Failed to load job: {error}
              </p>
            )}

            {job && (
              <>
                <div className="mb-5 flex flex-wrap items-center gap-2">
                  {job.is_posted_today && <PostedTodayBadge />}
                  <SourceBadge source={job.source_name} />
                  <Badge variant="remote" icon={Globe2}>
                    {job.remote_type || "Remote"}
                  </Badge>
                  <Badge variant="us" icon={Flag}>
                    US
                  </Badge>
                </div>

                <dl className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <MetaItem icon={MapPin} label="Location" value={job.location} />
                  <MetaItem
                    icon={CalendarDays}
                    label="Date posted"
                    value={
                      typeof job.days_old === "number"
                        ? `${formatDate(job.normalized_date_posted)} · ${
                            job.days_old === 0 ? "today" : `${job.days_old}d old`
                          }`
                        : formatDate(job.normalized_date_posted)
                    }
                  />
                  <MetaItem icon={Briefcase} label="Job type" value={job.job_type} />
                  <MetaItem icon={Wallet} label="Salary" value={job.salary} />
                  <MetaItem
                    icon={Layers}
                    label="Category"
                    value={job.primary_category ? categoryLabel(job.primary_category) : null}
                  />
                  <MetaItem
                    icon={Gauge}
                    label="Relevance score"
                    value={job.relevance_score != null ? String(job.relevance_score) : null}
                  />
                  <MetaItem
                    icon={Search}
                    label="Query used"
                    value={job.query_used || job.keyword_matched}
                  />
                </dl>

                {/* Matched categories */}
                {Array.isArray(job.matched_categories) && job.matched_categories.length > 0 && (
                  <div className="mb-5">
                    <h4 className="mb-2 font-display text-sm font-semibold text-slate-800">
                      Matched categories
                    </h4>
                    <div className="flex flex-wrap gap-1.5">
                      {job.matched_categories.map((c) => (
                        <Badge key={c} variant="serviceNow">
                          {categoryLabel(c)}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Matched keywords */}
                {Array.isArray(job.matched_keywords) && job.matched_keywords.length > 0 && (
                  <div className="mb-5">
                    <h4 className="mb-2 font-display text-sm font-semibold text-slate-800">
                      Matched keywords
                    </h4>
                    <div className="flex flex-wrap gap-1.5">
                      {job.matched_keywords.map((t) => (
                        <Badge key={t} variant="source">
                          {t}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                <div>
                  <h4 className="mb-2 font-display text-sm font-semibold text-slate-800">
                    Description
                  </h4>
                  <p className="whitespace-pre-line text-sm leading-relaxed text-slate-600">
                    {job.full_description ||
                      job.short_description ||
                      "No description provided by the source."}
                  </p>
                </div>
              </>
            )}
          </div>

          {/* Footer */}
          {job && (
            <div className="border-t border-slate-100 px-6 py-4">
              <Button
                variant="primary"
                size="lg"
                href={job.original_apply_url}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full"
              >
                Apply on {job.source_name}
                <ExternalLink className="h-4 w-4" />
              </Button>
            </div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>,
    document.body
  );
}
