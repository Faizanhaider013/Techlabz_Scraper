import {
  Search,
  MapPin,
  Tag,
  Database,
  ArrowUpDown,
  SlidersHorizontal,
  CalendarCheck,
  Layers,
  X,
} from "lucide-react";
import { CATEGORIES, categoryLabel, KEYWORD_FILTERS } from "../constants/categories.js";

const inputBase =
  "h-11 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-3 text-sm text-slate-800 placeholder:text-slate-400 outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100";
const selectBase =
  "h-11 w-full appearance-none rounded-xl border border-slate-200 bg-white pl-10 pr-9 text-sm text-slate-800 outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100";

function Field({ icon: Icon, children }) {
  return (
    <div className="relative">
      <Icon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
      {children}
    </div>
  );
}

function Section({ label, children }) {
  return (
    <div className="space-y-2">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </p>
      {children}
    </div>
  );
}

export default function JobFilters({
  filters,
  onChange,
  sources = [],
  keywords = [],
  defaults,
  windowDays = 0,
}) {
  const set = (patch) => onChange({ ...filters, ...patch, page: 1 });

  // Active filter chips (everything that differs from defaults).
  const active = [];
  if (filters.q) active.push({ key: "q", label: `“${filters.q}”` });
  if (filters.category) active.push({ key: "category", label: categoryLabel(filters.category) });
  if (filters.keyword) active.push({ key: "keyword", label: filters.keyword });
  if (filters.location) active.push({ key: "location", label: filters.location });
  if (filters.source) active.push({ key: "source", label: filters.source });

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
      <div className="mb-4 flex items-center gap-2">
        <SlidersHorizontal className="h-4 w-4 text-indigo-600" />
        <h3 className="font-display text-sm font-semibold text-slate-800">Filters</h3>
      </div>

      <div className="space-y-5">
        {/* Search */}
        <Field icon={Search}>
          <input
            type="text"
            value={filters.q || ""}
            onChange={(e) => set({ q: e.target.value })}
            placeholder="Search title, company…"
            className={inputBase}
          />
        </Field>

        {/* Freshness notice (no date pills: the window is fixed by config) */}
        <div className="flex items-center gap-2 rounded-xl bg-emerald-50 px-3 py-2 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-100">
          <CalendarCheck className="h-4 w-4" />
          {windowDays > 0
            ? `Showing jobs from the last ${windowDays} days`
            : "Showing jobs posted today only"}
        </div>

        {/* Category */}
        <Section label="Category">
          <Field icon={Layers}>
            <select
              value={filters.category || ""}
              onChange={(e) => set({ category: e.target.value })}
              className={selectBase}
            >
              <option value="">All categories</option>
              {CATEGORIES.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </select>
            <ChevronIcon />
          </Field>
        </Section>

        {/* Keyword */}
        <Section label="Keyword">
          <Field icon={Tag}>
            <select
              value={filters.keyword || ""}
              onChange={(e) => set({ keyword: e.target.value })}
              className={selectBase}
            >
              <option value="">All keywords</option>
              {(keywords && keywords.length ? keywords : KEYWORD_FILTERS).map((k) => (
                <option key={k} value={k}>
                  {k}
                </option>
              ))}
            </select>
            <ChevronIcon />
          </Field>
        </Section>

        {/* Location */}
        <Section label="Location">
          <Field icon={MapPin}>
            <input
              type="text"
              value={filters.location || ""}
              onChange={(e) => set({ location: e.target.value })}
              placeholder="e.g. United States"
              className={inputBase}
            />
          </Field>
        </Section>

        {/* Source */}
        <Section label="Source">
          <Field icon={Database}>
            <select
              value={filters.source || ""}
              onChange={(e) => set({ source: e.target.value })}
              className={selectBase}
            >
              <option value="">All sources</option>
              {sources.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            <ChevronIcon />
          </Field>
        </Section>

        {/* Sort */}
        <Section label="Sort by">
          <Field icon={ArrowUpDown}>
            <select
              value={filters.sort || "newest"}
              onChange={(e) => set({ sort: e.target.value })}
              className={selectBase}
            >
              <option value="newest">Newest first</option>
              <option value="oldest">Oldest first</option>
            </select>
            <ChevronIcon />
          </Field>
        </Section>

        {/* Active filters + reset */}
        {active.length > 0 && (
          <div className="border-t border-slate-100 pt-4">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                Active
              </p>
              <button
                onClick={() => onChange({ ...defaults })}
                className="text-xs font-medium text-indigo-600 hover:text-indigo-700"
              >
                Reset all
              </button>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {active.map((chip) => (
                <button
                  key={chip.key}
                  onClick={() => set({ [chip.key]: chip.reset ?? "" })}
                  className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700 ring-1 ring-inset ring-indigo-100 transition hover:bg-indigo-100"
                >
                  {chip.label}
                  <X className="h-3 w-3" />
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function ChevronIcon() {
  return (
    <svg
      className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden
    >
      <path
        fillRule="evenodd"
        d="M5.23 7.21a.75.75 0 011.06.02L10 11.17l3.71-3.94a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
        clipRule="evenodd"
      />
    </svg>
  );
}
