import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { LayoutGrid, CircleDot } from "lucide-react";
import clsx from "clsx";
import { api } from "../services/api.js";
import AppShell from "../components/AppShell.jsx";
import HeroBar from "../components/HeroBar.jsx";
import StatsCards from "../components/StatsCards.jsx";
import JobFilters from "../components/JobFilters.jsx";
import JobCard from "../components/JobCard.jsx";
import JobDetailModal from "../components/JobDetailModal.jsx";
import LoadingSkeleton, { StatsSkeleton } from "../components/LoadingSkeleton.jsx";
import EmptyState from "../components/EmptyState.jsx";
import DiagnosticsPanel from "../components/DiagnosticsPanel.jsx";
import Toast from "../components/Toast.jsx";
import { KEYWORD_FILTERS } from "../constants/categories.js";

const DEFAULT_FILTERS = {
  q: "",
  category: "",
  keyword: "",
  location: "",
  date_filter: "all",
  source: "",
  sort: "newest",
  page: 1,
  limit: 12,
};

function Tab({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        "inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition-all",
        active
          ? "bg-slate-900 text-white shadow-sm"
          : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"
      )}
    >
      {children}
    </button>
  );
}

export default function JobsPage() {
  const [view, setView] = useState("jobs"); // "jobs" | "diagnostics"
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [data, setData] = useState(null);
  const [stats, setStats] = useState(null);
  const [statsLoaded, setStatsLoaded] = useState(false);
  const [sources, setSources] = useState([]);
  const [diagnostics, setDiagnostics] = useState(null);
  const [diagLoading, setDiagLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [toast, setToast] = useState(null);
  const [lastRefreshed, setLastRefreshed] = useState(null);
  const [tab, setTab] = useState("all"); // "all" | "today"
  const resultsRef = useRef(null);

  const keywordOptions = KEYWORD_FILTERS;

  const showToast = (type, message) => {
    setToast({ type, message, id: Date.now() });
  };

  const fetchJobs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const effective =
        tab === "today" ? { ...filters, date_filter: "today" } : filters;
      setData(await api.getJobs(effective));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [filters, tab]);

  const fetchMeta = useCallback(async () => {
    try {
      const [s, src] = await Promise.all([api.getStats(), api.getSources()]);
      setStats(s);
      setSources(src.filter((x) => x.status === "active").map((x) => x.name));
    } catch {
      /* meta is non-critical */
    } finally {
      setStatsLoaded(true);
    }
  }, []);

  const fetchDiagnostics = useCallback(async () => {
    setDiagLoading(true);
    try {
      setDiagnostics(await api.getDiagnostics());
    } catch {
      setDiagnostics(null);
    } finally {
      setDiagLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);
  useEffect(() => {
    fetchMeta();
    fetchDiagnostics();
  }, [fetchMeta, fetchDiagnostics]);

  const handleRefresh = async () => {
    setRefreshing(true);
    showToast("info", "Running scraper across all active sources…");
    try {
      const result = await api.triggerScraper(); // POST /api/scraper/run?wait=true
      await Promise.all([fetchJobs(), fetchMeta(), fetchDiagnostics()]);
      setLastRefreshed(new Date().toISOString());
      if ((result?.total_new ?? 0) > 0) {
        showToast("success", `Done — ${result.total_new} ServiceNow remote US job(s) saved.`);
        // Smooth scroll to results.
        setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 150);
      } else {
        showToast("info", "Scraper ran. No new jobs passed the filters — see diagnostics.");
      }
    } catch (e) {
      showToast("error", `Scraper failed: ${e.message}. Is the backend running?`);
    } finally {
      setRefreshing(false);
    }
  };

  const jobs = data?.items || [];
  const total = data?.total || 0;
  const pages = data?.pages || 0;
  const windowDays = stats?.window_days ?? 0;
  const recentLabel = windowDays > 0 ? `Last ${windowDays} Days` : "Today Jobs";
  const diagUnavailable = diagnostics?.unavailable === true;

  return (
    <AppShell
      onRefresh={handleRefresh}
      refreshing={refreshing}
      view={view}
      setView={setView}
      lastRefreshed={lastRefreshed}
    >
      <HeroBar windowDays={windowDays} />

      {statsLoaded ? <StatsCards stats={stats} /> : <StatsSkeleton />}

      {view === "diagnostics" ? (
        <DiagnosticsPanel
          diagnostics={diagUnavailable ? null : diagnostics}
          loading={diagLoading}
          unavailable={diagUnavailable}
        />
      ) : (
        <div ref={resultsRef} className="grid grid-cols-1 gap-6 lg:grid-cols-[300px_1fr]">
          {/* Sidebar filters */}
          <aside className="lg:sticky lg:top-24 lg:self-start">
            <JobFilters
              filters={filters}
              onChange={setFilters}
              sources={sources}
              keywords={keywordOptions}
              defaults={DEFAULT_FILTERS}
              windowDays={windowDays}
            />
          </aside>

          {/* Content */}
          <section className="min-w-0 space-y-5">
            {/* Tabs + count */}
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex gap-2">
                <Tab
                  active={tab === "all"}
                  onClick={() => {
                    setTab("all");
                    setFilters((f) => ({ ...f, date_filter: "all", page: 1 }));
                  }}
                >
                  <LayoutGrid className="h-4 w-4" />
                  {recentLabel}
                </Tab>
                <Tab
                  active={tab === "today"}
                  onClick={() => {
                    setTab("today");
                    setFilters((f) => ({ ...f, page: 1 }));
                  }}
                >
                  <CircleDot className="h-4 w-4" />
                  Posted Today
                  {stats?.posted_today != null && (
                    <span
                      className={clsx(
                        "rounded-full px-1.5 text-xs font-mono",
                        tab === "today" ? "bg-white/20" : "bg-emerald-100 text-emerald-700"
                      )}
                    >
                      {stats.posted_today}
                    </span>
                  )}
                </Tab>
              </div>
              {!loading && !error && (
                <p className="text-sm text-slate-500">
                  <span className="font-semibold text-slate-800">{total}</span> result
                  {total === 1 ? "" : "s"}
                </p>
              )}
            </div>

            {/* Body */}
            {loading ? (
              <LoadingSkeleton count={4} />
            ) : error ? (
              <EmptyState
                title="Couldn't reach the backend"
                message={`${error}. Make sure the API is running on the configured URL.`}
                onRefresh={handleRefresh}
                refreshing={refreshing}
              />
            ) : jobs.length === 0 ? (
              <EmptyState
                title={
                  windowDays > 0
                    ? `No ServiceNow Remote US jobs from the last ${windowDays} days were found yet.`
                    : "No ServiceNow Remote US jobs posted today were found yet."
                }
                message="The scraper checked active sources, but no jobs passed the ServiceNow + Remote + United States filters in this window."
                onRefresh={handleRefresh}
                onViewDiagnostics={() => setView("diagnostics")}
                refreshing={refreshing}
              />
            ) : (
              <div className="grid grid-cols-1 gap-5 animate-fade-in md:grid-cols-2">
                {jobs.map((job) => (
                  <JobCard
                    key={job.id}
                    job={job}
                    windowDays={windowDays}
                    onSelect={(j) => setSelectedJobId(j.id)}
                  />
                ))}
              </div>
            )}

            {/* Pagination */}
            {pages > 1 && (
              <div className="flex items-center justify-center gap-2 pt-2">
                <button
                  disabled={filters.page <= 1}
                  onClick={() => setFilters((f) => ({ ...f, page: f.page - 1 }))}
                  className="rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
                >
                  ← Prev
                </button>
                <span className="px-2 text-sm text-slate-500">
                  Page {filters.page} of {pages}
                </span>
                <button
                  disabled={filters.page >= pages}
                  onClick={() => setFilters((f) => ({ ...f, page: f.page + 1 }))}
                  className="rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
                >
                  Next →
                </button>
              </div>
            )}
          </section>
        </div>
      )}

      {selectedJobId && (
        <JobDetailModal jobId={selectedJobId} onClose={() => setSelectedJobId(null)} />
      )}

      <Toast toast={toast} onDismiss={() => setToast(null)} />
    </AppShell>
  );
}
