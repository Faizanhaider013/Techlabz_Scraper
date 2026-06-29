import { BadgeCheck, Globe2, Layers, CalendarCheck } from "lucide-react";

function TrustBadge({ icon: Icon, children }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200/80 bg-white/70 px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm backdrop-blur">
      <Icon className="h-3.5 w-3.5 text-indigo-600" strokeWidth={2.25} />
      {children}
    </span>
  );
}

export default function HeroBar({ windowDays = 0 }) {
  const recent = windowDays > 0;
  const dateBadge = recent ? `Last ${windowDays} Days` : "Today Only";
  return (
    <section className="relative overflow-hidden rounded-3xl border border-slate-200 bg-gradient-to-br from-indigo-600 via-indigo-600 to-blue-600 px-6 py-10 shadow-glow sm:px-10 sm:py-12">
      {/* Decorative glows */}
      <div
        aria-hidden
        className="pointer-events-none absolute -right-16 -top-20 h-64 w-64 rounded-full bg-white/10 blur-3xl"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -bottom-24 -left-10 h-64 w-64 rounded-full bg-blue-400/20 blur-3xl"
      />

      <div className="relative max-w-2xl">
        <h2 className="font-display text-3xl font-bold leading-tight tracking-tight text-white md:text-5xl">
          Remote Tech Jobs Aggregator
        </h2>
        <p className="mt-3 max-w-xl text-sm leading-relaxed text-indigo-100 sm:text-base">
          Real remote software, full-stack, ServiceNow, PHP, Laravel, Node.js, React,
          MERN, MEAN, and engineering jobs{" "}
          <strong className="font-semibold text-white">
            {recent ? `posted in the last ${windowDays} days` : "posted today"}
          </strong>
          . From trusted sources — no fake jobs.
        </p>

        <div className="mt-6 flex flex-wrap gap-2">
          <TrustBadge icon={BadgeCheck}>Real Jobs Only</TrustBadge>
          <TrustBadge icon={Globe2}>Remote Focused</TrustBadge>
          <TrustBadge icon={Layers}>Multi-Stack Search</TrustBadge>
          <TrustBadge icon={CalendarCheck}>{dateBadge}</TrustBadge>
        </div>
      </div>
    </section>
  );
}
