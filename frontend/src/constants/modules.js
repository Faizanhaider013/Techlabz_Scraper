// ServiceNow module codes shared with the backend taxonomy
// (backend/app/scraper/servicenow_taxonomy.py MODULES). The `code` is what the
// API stores on each job (matched_modules) and accepts as the `module` filter.
export const MODULES = [
  { code: "ITSM", label: "ITSM" },
  { code: "ITOM", label: "ITOM" },
  { code: "CMDB", label: "CMDB" },
  { code: "HRSD", label: "HRSD" },
  { code: "CSM", label: "CSM" },
  { code: "FSM", label: "FSM" },
  { code: "SecOps", label: "SecOps" },
  { code: "IRM/GRC", label: "IRM / GRC" },
  { code: "SPM/ITBM", label: "SPM / ITBM" },
  { code: "ITAM", label: "ITAM / SAM / HAM" },
  { code: "App Engine", label: "App Engine" },
  { code: "Service Portal", label: "Service Portal" },
  { code: "Integration Hub", label: "Integration Hub" },
  { code: "Discovery", label: "Discovery" },
  { code: "Flow Designer", label: "Flow Designer" },
  { code: "Virtual Agent", label: "Virtual Agent" },
  { code: "Performance Analytics", label: "Performance Analytics" },
  { code: "DevOps", label: "DevOps" },
];

const _LABELS = Object.fromEntries(MODULES.map((m) => [m.code, m.label]));

export function moduleLabel(code) {
  return _LABELS[code] || code;
}
