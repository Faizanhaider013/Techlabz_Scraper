import Header from "./Header.jsx";

const CONTAINER = "mx-auto max-w-7xl px-4 sm:px-6 lg:px-8";

// Top-level page layout: sticky header, centered content container, footer.
export default function AppShell({
  onRefresh,
  refreshing,
  view,
  setView,
  lastRefreshed,
  children,
}) {
  return (
    <div className="min-h-screen bg-slate-50">
      {/* Ambient top gradient */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-72 bg-gradient-to-b from-indigo-50/70 via-slate-50/40 to-transparent"
      />
      <div className="relative">
        <Header
          onRefresh={onRefresh}
          refreshing={refreshing}
          view={view}
          setView={setView}
          lastRefreshed={lastRefreshed}
        />
        <main className={`${CONTAINER} space-y-7 py-7`}>{children}</main>

        <footer className="border-t border-slate-200 py-7">
          <div className={`${CONTAINER} text-center text-xs text-slate-400`}>
            ServiceNow Remote US Jobs · Strictly filtered to ServiceNow + Remote +
            United States · Every listing links back to its original posting.
          </div>
        </footer>
      </div>
    </div>
  );
}

export { CONTAINER };
