# Spetser AI

Arabic-first educational AI platform for university and school students, initially focused on Libya.

## Status

**Phase 0 — Baseline Stabilization and Repository Audit** ✅ Complete
- Baseline stabilization completed: 167 backend unit/integration tests passing (0 failures).
- Accidental scratch scripts (~44 temporary files) and committed `.pyc` files purged from source control.
- Test discovery made self-contained: `pythonpath = ["."]` in `backend/pyproject.toml` and explicit test defaults in `conftest.py`.
- Alembic initial schema updated with SQLite-compatible variant for `fallback_model_configuration_ids` JSON support. Verified `alembic upgrade head` and `downgrade base`.
- Frontend lint and build clean: `oxlint` (0 errors, 0 warnings), `npm run build` (230 modules, 0 TypeScript errors).
- Idempotency key validation and unready deliverable error envelopes verified and tested.

**Test Results**:
- Backend: 167 passed (`python -m pytest -q`)
- Frontend Lint: 0 errors, 0 warnings (`npm run lint`)
- Frontend Build: 0 errors (`npm run build`)

## Quick Start

### Backend

```bash
cd backend
cp .env.example .env
# Edit .env with your values (DATABASE_URL, secrets, API keys)
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Architecture

```
FastAPI Application
├── /api/v1/auth          # Authentication (register, login, me, logout)
├── /api/v1/health        # Health & readiness probes
├── /api/v1/chat          # (Phase 2) General chat
├── /api/v1/presentations # (Phase 2) Presentation generation
├── /api/v1/requests      # (Phase 2) Request status
├── /api/v1/deliverables  # (Phase 2) File downloads
├── /api/v1/developer     # (Phase 3) Developer Dashboard
└── /api/v1/credits       # (Phase 2) Credit balance
```

## Configuration

All settings via environment variables (see `backend/.env.example`):

| Variable | Description |
|----------|-------------|
| `APP_ENV` | `development` \| `staging` \| `production` |
| `APP_SECRET_KEY` | 32+ char secret for session signing |
| `DATABASE_URL` | PostgreSQL asyncpg URL (Supabase) |
| `SESSION_SECRET_KEY` | 32+ char secret for session cookies |
| `APP_ALLOWED_ORIGINS` | Comma-separated CORS origins |
| `ANTHROPIC_API_KEY` | Claude API key |
| `GOOGLE_GEMINI_API_KEY` | Gemini API key |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key |

## Testing

```bash
cd backend
pytest -q
```

## Design Tokens

CSS custom properties (see `frontend/src/index.css`):
- `--color-parchment: #faf8f5`
- `--color-deep-teal: #016a71`
- `--color-ink: #27251e`
- RTL-first layout with logical CSS properties

## License

Private — developer beta only.