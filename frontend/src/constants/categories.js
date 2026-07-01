// Job categories shared with the backend taxonomy
// (backend/app/scraper/job_taxonomy.py). `id` is what the API stores as
// primary_category and accepts as the `category` filter.
export const CATEGORIES = [
  { id: "servicenow", label: "ServiceNow" },
  { id: "mern", label: "MERN Stack" },
  { id: "mean", label: "MEAN Stack" },
  { id: "node_backend", label: "Node.js" },
  { id: "php", label: "PHP" },
  { id: "laravel", label: "Laravel" },
  { id: "react_frontend", label: "Frontend" },
];

// Quick keyword filters (free-text `q` searches, not category ids).
export const KEYWORD_FILTERS = [
  "ServiceNow",
  "MERN",
  "MEAN",
  "Node.js",
  "PHP",
  "Laravel",
  "Frontend",
];

const _LABELS = Object.fromEntries(CATEGORIES.map((c) => [c.id, c.label]));

export function categoryLabel(id) {
  return _LABELS[id] || id;
}
