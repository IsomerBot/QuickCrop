# Repository Guidelines

## Project Structure & Module Organization
- `backend/`: FastAPI app (`main.py`), services, models, utils, and `tests/`.
- `frontend/`: Next.js (App Router) with TypeScript, Tailwind, components, and `tests/`.
- `docker/`, `docker-compose*.yml`: Containerization; see `README.md` for entrypoints.
- `docs/`: Developer and deployment docs. `.env.example` files in root, backend, and frontend.

## Build, Test, and Development Commands
- Run locally (Docker): `docker-compose up --build` (frontend on `:3000`, API on `:8000`).
- Backend dev: `cd backend && uvicorn main:app --reload --port 8000`.
- Backend tests: `cd backend && pytest -q` (coverage: `pytest --cov=services --cov=api`).
- Backend quality: `black backend && isort backend && flake8 backend && mypy backend`.
- Frontend dev: `cd frontend && npm install && npm run dev`.
- Frontend build/start: `npm run build && npm start`.
- Frontend lint/type/format: `npm run lint && npm run type-check && npm run format`.
- Frontend tests: `cd frontend && npx jest` (JSDOM, Testing Library).

## Coding Style & Naming Conventions
- Python: Black formatting (88 cols), type hints required in new code, `snake_case` for functions/vars, `PascalCase` for classes.
- JS/TS: Prettier + ESLint (Next.js config), 2-space indent, `camelCase` for vars/functions, `PascalCase` for React components and their files (e.g., `CropEditor.tsx`).
- Paths: Tests mirror sources (`backend/tests/test_*.py`, `frontend/tests/**/*.test.tsx`).

## Testing Guidelines
- Aim for 80%+ coverage on changed backend modules; include async tests where relevant.
- Frontend: Write unit tests with Jest + Testing Library; prefer behavior over implementation details.
- Name tests clearly and keep fixtures small; add sample images under `frontend/public/sample-images/` only if required.

## Commit & Pull Request Guidelines
- Use Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`.
- PRs: concise title/description, link issues, include screenshots/GIFs for UI changes, and notes on test coverage.
- CI readiness: code formatted, lint/type checks pass, tests green.

## Security & Configuration Tips
- Do not commit secrets. Copy from `.env.example` and set `TINIFY_API_KEY`, `SECRET_KEY`, and CORS settings per environment.
- Change default `TINIFY_API_KEY` and `SECRET_KEY` in production.
- Validate file types/sizes server-side (limits set in `core/config.py`).

## Agent-Specific Notes
- Keep changes focused and small; update docs when behavior or endpoints change.
- Avoid broad refactors; preserve public API routes under `/api/v1` and Next.js app structure.
