# Frontend (React + Vite)

This frontend is a React + TypeScript SPA built with Vite. In production and Docker, the backend serves the built assets via FastAPI `StaticFiles`.

## Development
- Install dependencies:
```bash
npm ci
```
- Start dev server:
```bash
npm run dev
```
By default, API calls use same-origin in production and `http://127.0.0.1:8000` in dev if you set `VITE_API_BASE`.

Create `./.env.development` to explicitly point to your backend:
```
VITE_API_BASE=http://127.0.0.1:8000
```

## Build
```bash
npm run build
```
Build output goes to `dist/`, which the backend serves at `/`.

## Environment
- `VITE_API_BASE` controls the API root.
  - Dev: set to your running backend, e.g. `http://127.0.0.1:8000`.
  - Prod: typically same-origin; omit to default to the current origin.
See `.env.example` for a reference.

## Run via backend
After building (`npm run build`), start the backend and open `http://127.0.0.1:8000/`. The SPA is served from `frontend/dist` by FastAPI.
