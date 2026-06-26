# ResumeAI Brain

Living reference for the codebase layout, request flow, and security changes.
Update this file when architecture or behavior changes so future edits do not require a full repo sweep.

## System Design

- `frontend/` is the Vite + React UI.
- `backend/` is the FastAPI API and rendering service layer.
- Authentication is JWT-based and stored on the client for the current session flow.
- Resume analysis, agent analysis, job search, history, and exports are all server-backed.
- PDF generation uses a persistent Node/Puppeteer helper with a subprocess fallback.

## High-Level Architecture

1. User opens the React app.
2. `AuthContext` restores the token and calls `/api/auth/me`.
3. Protected routes and API calls use the bearer token.
4. Resume uploads go to the backend, where parsing, validation, AI calls, scoring, and history save happen.
5. Export routes generate PDF or LaTeX downloads from the tailored resume payload.

## Main Frontend Flow

- `frontend/src/App.tsx` wires routing and global providers.
- `frontend/src/context/AuthContext.tsx` manages login state and token persistence.
- `frontend/src/lib/api.ts` contains all API calls and response normalization.
- `frontend/src/pages/Landing.tsx` is the public landing page and authenticated workspace switch.
- `frontend/src/components/UnifiedWorkspace.tsx` is the main product surface for logged-in users.

## Main Backend Flow

- `backend/main.py` boots FastAPI, registers middleware, sets headers, and mounts routers.
- `backend/routers/auth.py` handles register, login, and `/me`.
- `backend/routers/analyze.py` handles resume analysis and export endpoints.
- `backend/routers/agent.py` handles the SSE agent workflow.
- `backend/routers/history.py` handles per-user history CRUD.
- `backend/routers/jobs.py` handles job search and description formatting.

## Data Ownership Rules

- History queries always filter by `user_id`.
- Single history entries are fetched by both `entry_id` and `user_id`.
- Deletes also require `user_id`.
- Protected analysis/export endpoints require authentication.

## File Validation Rules

- Uploads are accepted only as PDF or DOCX.
- Parser checks both filename extension and MIME/content bytes.
- Uploads are limited to 10 MB.
- Empty files are rejected.

## Security Controls Already Added

- Security headers in backend and deployment configs.
- Rate limiting on auth, analysis, agent, job search, and export routes.
- Generic error messages for user-facing failures.
- Server-side traceback logging only.
- CSP / frame / referrer / permissions hardening.
- No client exposure of API keys or backend secrets.

## Recent Changes Made

- Removed `Pricing` from the public top navigation.
- Footer links now show only `GitHub`, `LinkedIn`, and `Mail`.
- Footer links no longer open in a new tab.
- Added stricter upload type checks in the resume parser.
- Added rate limits to high-cost API endpoints.
- Removed internal exception text from user-facing API errors.
- Strengthened response and deployment security headers.

## Workflow Notes

- Keep API contracts stable unless a breaking change is explicitly intended.
- Prefer server-side validation over client-only checks.
- Preserve user flow and UI behavior when hardening security.
- When changing auth, uploads, exports, or history, update this file first or alongside the code.

## Where To Look First

- Auth/session issues: `backend/routers/auth.py`, `frontend/src/context/AuthContext.tsx`
- Analysis flow: `backend/routers/analyze.py`, `backend/services/parser.py`
- Agent flow: `backend/routers/agent.py`, `backend/services/agent_orchestrator.py`
- History access: `backend/routers/history.py`, `backend/models/history.py`
- Export behavior: `backend/services/pdf_generator.py`, `backend/services/latex_generator.py`
- Landing/footer UI: `frontend/src/pages/Landing.tsx`

