// Skeleton loaders so the screen is never blank while data loads.

export function JobCardSkeleton() {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card sm:p-6">
      <div className="mb-3 h-5 w-3/4 animate-pulse rounded bg-slate-200" />
      <div className="mb-4 flex gap-3">
        <div className="h-4 w-24 animate-pulse rounded bg-slate-100" />
        <div className="h-4 w-20 animate-pulse rounded bg-slate-100" />
      </div>
      <div className="mb-4 flex gap-1.5">
        <div className="h-5 w-16 animate-pulse rounded-md bg-slate-100" />
        <div className="h-5 w-16 animate-pulse rounded-md bg-slate-100" />
        <div className="h-5 w-12 animate-pulse rounded-md bg-slate-100" />
      </div>
      <div className="space-y-2">
        <div className="h-3 w-full animate-pulse rounded bg-slate-100" />
        <div className="h-3 w-full animate-pulse rounded bg-slate-100" />
        <div className="h-3 w-2/3 animate-pulse rounded bg-slate-100" />
      </div>
      <div className="mt-5 flex justify-end gap-2 border-t border-slate-100 pt-4">
        <div className="h-9 w-24 animate-pulse rounded-xl bg-slate-100" />
        <div className="h-9 w-20 animate-pulse rounded-xl bg-slate-200" />
      </div>
    </div>
  );
}

export function StatsSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div
          key={i}
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card"
        >
          <div className="mb-3 flex items-center justify-between">
            <div className="h-3 w-20 animate-pulse rounded bg-slate-200" />
            <div className="h-8 w-8 animate-pulse rounded-lg bg-slate-100" />
          </div>
          <div className="h-8 w-16 animate-pulse rounded bg-slate-200" />
          <div className="mt-2 h-3 w-24 animate-pulse rounded bg-slate-100" />
        </div>
      ))}
    </div>
  );
}

export default function LoadingSkeleton({ count = 6 }) {
  return (
    <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
      {Array.from({ length: count }).map((_, i) => (
        <JobCardSkeleton key={i} />
      ))}
    </div>
  );
}
