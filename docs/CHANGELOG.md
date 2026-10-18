# Changelog — Spetser AI

All notable changes to the Spetser AI platform are documented in this file.

## [1.0.0] - 2026-10-18

### Added
- Comprehensive security audit (Phase 1) with 10 findings documented and fully mitigated.
- Complete design system with CSS tokens, animation system, and guidelines (Phase 2).
- Rebuilt frontend component architecture with atomic UI components (Button, Input, Toast) and chat interface (Phase 3).
- Redis caching layer (`backend/app/core/cache.py`) with `cache_result` and `invalidate_cache` (Phase 4).
- Distributed rate limiting middleware (`backend/app/middleware/rate_limit.py`) with fail-open fallback (Phase 4).
- Standardized error handling hierarchy (`backend/app/core/exceptions.py`) and global handlers (Phase 4).
- Automated penetration test suite (`test_penetration_suite.py`) with 8/8 passing security vectors (Phase 5).
- Full documentation suite: Architecture, comprehensive API specifications, and Security Audit (Phase 6).

### Security
- Fixed 1 critical vulnerability (`SEC-CRIT-01`: test credit grant restricted strictly to development).
- Fixed 1 high-severity vulnerability (`SEC-HIGH-01`: hardened dev auth bypass with fail-closed checks).
- Fixed 4 medium-severity vulnerabilities (`SEC-MED-01..04`: cookie deletion flags, provider key RBAC, webhook fallback secrets, and markdown link scheme sanitization).
- Fixed 4 low-severity vulnerabilities (`SEC-LOW-01..04`: referral throttle, download route aliases, default email redaction, and code block sanitization).
- Enforced distributed sliding-window rate limiting on sensitive routes.
- Hardened CORS configuration with explicit origin whitelists and security headers (CSP, HSTS, X-Frame-Options).

### Changed
- Database connection pool optimized for PostgreSQL/asyncpg (pool_size=20, max_overflow=10, pool_pre_ping=True, pool_recycle=1800).
- Standardized error responses across all endpoints.
- Re-architected frontend components with design system token integration and React 19 standards.
