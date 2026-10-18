# Spetser AI — API Specification

Central reference documentation for FastAPI backend endpoints.
Base URL: `/api/v1`

## Authentication & Authorization
- Session token cookie: `spetser_session`
- Role hierarchy: `student` < `admin` < `developer`

## Route Modules Summary

| Prefix | Domain | Description |
|---|---|---|
| `/api/v1/auth` | Authentication | Registration, login, session validation, logout, revocation |
| `/api/v1/conversations` | Chat | Student conversation threads and message completions |
| `/api/v1/credits` | Wallet | Credit ledger balances, grant (dev), transaction history |
| `/api/v1/payments` | Payments | Crypto invoices generation, webhook callbacks |
| `/api/v1/referrals` | Growth | Student referral links, metrics, rewards, fraud prevention |
| `/api/v1/skills` | Skills | Public and premium AI skill catalog |
| `/api/v1/presentations` | Features | Academic presentation generator and secure deliverable downloads |
| `/api/v1/health` | System | Health checks and readiness probes |
| `/api/v1/admin/*` | Governance | User moderation, credit adjustment, skill management, audit log access |
