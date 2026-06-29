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
};

export default function SourceBadge({ source }) {
  const tone = TONES[source] || "bg-slate-50 text-slate-600 ring-slate-200";
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
        tone
      )}
    >
      {source}
    </span>
  );
}
