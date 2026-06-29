// Job categories shared with the backend taxonomy
// (backend/app/scraper/job_taxonomy.py). `id` is what the API stores as
// primary_category and accepts as the `category` filter.
export const CATEGORIES = [
  { id: "servicenow", label: "ServiceNow" },
  { id: "php_laravel", label: "PHP / Laravel" },
  { id: "node_backend", label: "Node.js / Backend" },
  { id: "react_frontend", label: "React / Frontend" },
  { id: "mern", label: "MERN Stack" },
  { id: "mean", label: "MEAN Stack" },
  { id: "fullstack", label: "Full Stack" },
  { id: "software_engineer", label: "Software Engineer" },
  { id: "python_backend", label: "Python / Backend" },
  { id: "devops_cloud", label: "DevOps / Cloud" },
  { id: "data_ai", label: "Data / AI" },
  { id: "qa_automation", label: "QA / Automation" },
];

// Quick keyword filters (free-text `q` searches, not category ids).
export const KEYWORD_FILTERS = [
  "PHP",
  "Laravel",
  "Node.js",
  "React.js",
  "MERN",
  "MEAN",
  "Full Stack Developer",
  "Software Engineer",
  "Backend Developer",
  "Frontend Developer",
  "ServiceNow",
];

const _LABELS = Object.fromEntries(CATEGORIES.map((c) => [c.id, c.label]));

export function categoryLabel(id) {
  return _LABELS[id] || id;
}
