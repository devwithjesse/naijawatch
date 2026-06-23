NaijaWatch — Frontend
=====================

This directory contains the React frontend (Vite + TanStack) for NaijaWatch.

Quick start (dev)
-----------------
1. Install dependencies
   cd frontend
   bun install

2. Development server
   # Set the backend API base URL if different from default
   export VITE_API_BASE=http://localhost:8000
   bun run dev

3. Build for production
   bun run build
   # Output will be in dist/ (standard Vite)

Environment variables
- VITE_API_BASE: The base URL for the backend API (default: http://localhost:8000). Configure this in Netlify build settings for production.

Static assets
- public/ contains logo.png, favicon.ico and other images. Vite serves files in public/ at the site root (e.g., /logo.png).

Netlify deploy notes
- Connect your GitHub repository to Netlify and use the default build command (npm run build) and publish directory (dist/).
- In Netlify site settings (Site → Build & deploy → Environment), add:
  - VITE_API_BASE: https://your-backend-url (Cloud Run)
- For favicon/logo updates: place files into frontend/public/ and commit.

Local preview of email digest (useful to check layout)
- The backend provides a renderer that produces a local HTML preview of the weekly digest. From repo root:
  python backend/utils/render_digest_preview.py --out frontend/digest_preview.html
- Then open frontend/digest_preview.html in your browser.

Notes
- The frontend uses React Query for caching and smart refresh. Map and event requests call /api/events/map and expect concise payloads.
- For production, enable proper caching headers in Netlify and set the API base to the Cloud Run URL.
