// API client for the Job Aggregator backend (uses fetch).

const BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:8000";

async function request(path, { params, ...options } = {}) {
  const url = new URL(`${BASE_URL}${path}`);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, value);
      }
    });
  }
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }
  return res.json();
}

export const api = {
  getJobs: (params) => request("/api/jobs", { params }),
  getTodayJobs: (params) => request("/api/jobs/today", { params }),
  getJob: (id) => request(`/api/jobs/${id}`),
  getStats: (params) => request("/api/stats", { params }),
  getSources: () => request("/api/sources"),
  getCategories: () => request("/api/categories"),
  getRuns: () => request("/api/scraper/runs"),
  // Returns { unavailable: true } if the diagnostics endpoint is missing (404)
  // so older backends don't crash the UI.
  getDiagnostics: async () => {
    try {
      return await request("/api/scraper/diagnostics");
    } catch (e) {
      if (String(e.message).includes("404")) return { unavailable: true };
      throw e;
    }
  },
  getQueryDiagnostics: async () => {
    try {
      return await request("/api/scraper/query-diagnostics");
    } catch (e) {
      if (String(e.message).includes("404")) return { unavailable: true };
      throw e;
    }
  },
  // Trigger scraper in the background (asynchronous, returns instantly)
  triggerScraper: () => request("/api/scraper/run", { method: "POST" }),
};

export { BASE_URL };
