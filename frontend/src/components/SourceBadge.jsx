import clsx from "clsx";

// Small colored badge for the job's source.
const TONES = {
  RemoteOK: "bg-amber-50 text-amber-700 ring-amber-100",
  Remotive: "bg-sky-50 text-sky-700 ring-sky-100",
  Arbeitnow: "bg-violet-50 text-violet-700 ring-violet-100",
  Himalayas: "bg-teal-50 text-teal-700 ring-teal-100",
  Greenhouse: "bg-green-50 text-green-700 ring-green-100",
  Lever: "bg-indigo-50 text-indigo-700 ring-indigo-100",
  Ashby: "bg-fuchsia-50 text-fuchsia-700 ring-fuchsia-100",
  MockDev: "bg-slate-100 text-slate-600 ring-slate-200",
  // --- New sources ---
  WeWorkRemotely: "bg-rose-50 text-rose-700 ring-rose-100",
  WorkingNomads: "bg-orange-50 text-orange-700 ring-orange-100",
  Jobspresso: "bg-cyan-50 text-cyan-700 ring-cyan-100",
  "Remote.co": "bg-emerald-50 text-emerald-700 ring-emerald-100",
  NoDesk: "bg-lime-50 text-lime-700 ring-lime-100",
  SkipTheDrive: "bg-yellow-50 text-yellow-700 ring-yellow-100",
  HubstaffTalent: "bg-blue-50 text-blue-700 ring-blue-100",
  EuropeRemotely: "bg-purple-50 text-purple-700 ring-purple-100",
  WawAsia: "bg-pink-50 text-pink-700 ring-pink-100",
  Remote4Me: "bg-amber-50 text-amber-700 ring-amber-100",
  Pangian: "bg-teal-50 text-teal-700 ring-teal-100",
  Remotees: "bg-sky-50 text-sky-700 ring-sky-100",
  Outsourcely: "bg-violet-50 text-violet-700 ring-violet-100",
  RemoteFreelance: "bg-orange-50 text-orange-700 ring-orange-100",
  CompanyCareers: "bg-emerald-50 text-emerald-700 ring-emerald-100",
  SmartRecruiters: "bg-indigo-50 text-indigo-700 ring-indigo-100",
  Workday: "bg-blue-50 text-blue-700 ring-blue-100",
  Recruitee: "bg-cyan-50 text-cyan-700 ring-cyan-100",
  Teamtailor: "bg-fuchsia-50 text-fuchsia-700 ring-fuchsia-100",
};

// Sources that are company ATS / career page types
const ATS_SOURCES = new Set([
  "CompanyCareers", "Greenhouse", "Lever", "Ashby",
  "SmartRecruiters", "Workday", "Recruitee", "Teamtailor",
]);

export default function SourceBadge({ source }) {
  const tone = TONES[source] || "bg-slate-50 text-slate-600 ring-slate-200";
  const isATS = ATS_SOURCES.has(source);
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
        tone
      )}
    >
      {isATS && "🏢 "}
      {source}
    </span>
  );
}
