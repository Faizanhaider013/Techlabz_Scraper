# Frontend — Job Aggregator Website

React 18 + Vite + Tailwind CSS. Displays aggregated jobs with search, filters,
sorting, a prominent **Posted Today** view, a job detail modal, and a stats
dashboard. Fully responsive (desktop / tablet / mobile).

## Quick start

```bash
npm install
cp .env.example .env          # VITE_API_BASE_URL defaults to http://localhost:8000
npm run dev                   # http://localhost:5173
```

Make sure the backend is running (see `../backend/README.md`).

## Build

```bash
npm run build                 # outputs to dist/
npm run preview               # preview the production build
```

## Layout

```
src/
  App.jsx
  main.jsx
  services/api.js                 # API client (uses VITE_API_BASE_URL)
  components/
    JobCard.jsx                   # job card with apply button + today badge
    JobFilters.jsx                # search, date pills, dropdowns, sort
    PostedTodayBadge.jsx          # the priority "Posted Today" badge
    StatsCards.jsx                # dashboard stat cards
    LoadingState.jsx              # skeleton loaders
    EmptyState.jsx                # friendly no-results message
  pages/
    JobsPage.jsx                  # main page: tabs, filters, grid, pagination
    JobDetailPage.jsx             # job detail modal (full description + apply)
```

## Deploy (Vercel)

- Root directory: `frontend/`
- Build command: `npm run build`, output dir: `dist/`
- Set `VITE_API_BASE_URL` to the deployed backend URL
- Add the frontend URL to the backend's `CORS_ORIGINS`
