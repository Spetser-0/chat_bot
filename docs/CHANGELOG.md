# Changelog — Spetser AI

All notable changes to the Spetser AI platform are documented in this file.

## [Unreleased] - Comprehensive Refactor v2.0

### Added
- Reference skill ecosystem in `.claude/skills/` (`security-audit`, `ui-ux-pro-max`, `taste-skill`, `emil-design-eng`).
- Dedicated security audit and penetration test documentation suites.

### Fixed
- Isolated test environment configuration from machine-local `.env` values in `backend/tests/conftest.py`.
- Corrected asyncpg driver URL resolution in `backend/alembic/env.py`.
- Named foreign key constraint `students_referred_by_user_id_fkey` and removed invalid UUID-to-NUMERIC type alterations in `backend/alembic/versions/20261005_0202_f2029e7b9acb_phase1_database_foundation.py`.
