# Spetser AI - Architecture Documentation

**Last Updated**: 2026-10-04  
**Status**: Phase 0 - Initial Version

---

## Overview

Spetser AI is an Arabic-first educational AI platform designed for university and school students, initially focused on Libya and the Arab world. The platform provides specialized AI assistance through a "Skills" system, where each skill represents a distinct AI personality (e.g., math tutor, code reviewer, essay helper).

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  • Vite + TypeScript                                        │
│  • Arabic RTL Support                                       │
│  • Dark/Light Mode                                          │
│  • Real-time Streaming Chat UI                             │
└────────────────┬────────────────────────────────────────────┘
                 │ HTTPS/WSS
                 │
┌────────────────▼────────────────────────────────────────────┐
│                   Backend API (FastAPI)                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  API Layer (FastAPI Routers)                         │  │
│  │  /api/v1/auth, /chat, /credits, /payments, /admin   │  │
│  └──────────────┬───────────────────────────────────────┘  │
│                 │                                            │
│  ┌──────────────▼───────────────────────────────────────┐  │
│  │  Service Layer                                        │  │
│  │  • LLM Router (multi-provider failover)              │  │
│  │  • Skill Resolver (load AI personalities)            │  │
│  │  • Credit Service (wallet & metering)                │  │
│  │  • Payment Service (crypto gateway)                  │  │
│  │  • Referral Service (attribution & rewards)          │  │
│  └──────────────┬───────────────────────────────────────┘  │
│                 │                                            │
│  ┌──────────────▼───────────────────────────────────────┐  │
│  │  Database Layer (SQLAlchemy + Alembic)               │  │
│  │  • Models, Migrations, Transactions                  │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────┬────────────────────────────────────────────┘
                 │
    ┌────────────┼────────────────────┐
    │            │                    │
┌───▼───┐   ┌───▼────┐   ┌──────────▼──────────┐
│ PostgreSQL │   │ Redis  │   │ External Services    │
│ (Supabase) │   │ Cache  │   │ • Anthropic Claude   │
│            │   │ Rate   │   │ • Google Gemini      │
│            │   │ Limit  │   │ • OpenAI (optional)  │
│            │   │        │   │ • NOWPayments/Cryptomus │
│            │   │        │   │ • Supabase Storage   │
└────────────┘   └────────┘   └─────────────────────┘
```

---

## Backend Architecture

### Directory Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI app factory
│   ├── api/
│   │   ├── deps.py             # Shared dependencies
│   │   └── v1/
│   │       └── routes/
│   │           ├── auth.py     # Authentication endpoints
│   │           ├── health.py   # Health checks
│   │           ├── chat.py     # Chat/AI interaction (planned)
│   │           ├── credits.py  # Credit balance & history (planned)
│   │           ├── payments.py # Payment invoices & webhooks (planned)
│   │           ├── referrals.py # Referral links & stats (planned)
│   │           ├── skills.py   # Public skill listing (planned)
│   │           └── admin.py    # Admin management (planned)
│   ├── core/
│   │   ├── config.py           # Settings via pydantic-settings
│   │   ├── security.py         # Encryption, hashing, JWT (to be enhanced)
│   │   ├── logging.py          # Structured logging (to be created)
│   │   ├── exceptions.py       # Custom exceptions (to be created)
│   │   └── dependencies.py     # Auth dependencies (to be created)
│   ├── db/
│   │   ├── session.py          # Database session factory
│   │   ├── base.py             # SQLAlchemy Base
│   │   └── init_db.py          # Database initialization
│   ├── models/
│   │   ├── student.py          # User/Student model (current)
│   │   ├── provider.py         # AI provider config (current)
│   │   ├── ai_provider.py      # New multi-provider model (planned)
│   │   ├── skill.py            # AI personality/skill model (planned)
│   │   ├── skill_tool.py       # Skill-tool associations (planned)
│   │   ├── conversation.py     # Chat conversations (planned)
│   │   ├── message.py          # Chat messages (planned)
│   │   ├── credit_ledger.py    # Credit transactions (exists, may extend)
│   │   ├── payment_invoice.py  # Payment records (planned)
│   │   ├── referral.py         # Referral tracking (planned)
│   │   ├── reward_transaction.py # Referral rewards (planned)
│   │   ├── webhook_event.py    # Webhook deduplication (planned)
│   │   └── audit_log.py        # Audit trail (exists, may extend)
│   ├── schemas/
│   │   ├── auth.py             # Auth request/response schemas
│   │   ├── chat.py             # Chat schemas (planned)
│   │   ├── credit.py           # Credit schemas (planned)
│   │   ├── payment.py          # Payment schemas (planned)
│   │   ├── referral.py         # Referral schemas (planned)
│   │   ├── skill.py            # Skill schemas (planned)
│   │   └── admin.py            # Admin schemas (planned)
│   ├── services/
│   │   ├── auth.py             # Authentication service (exists)
│   │   ├── llm_router.py       # Multi-provider LLM router (planned)
│   │   ├── provider_service.py # AI provider CRUD (planned)
│   │   ├── skill_resolver.py   # Skill loading & prompt building (planned)
│   │   ├── credit_service.py   # Wallet management (planned)
│   │   ├── payment_service.py  # Payment processing (planned)
│   │   ├── referral_service.py # Referral logic (planned)
│   │   ├── analytics_service.py # Admin analytics (planned)
│   │   ├── audit_service.py    # Audit logging wrapper (planned)
│   │   └── security_service.py # Encryption utilities (planned)
│   ├── middleware/
│   │   └── request_id.py       # Request tracing (exists)
│   └── utils/
│       ├── ids.py              # ID generation (planned)
│       ├── money.py            # Currency utilities (planned)
│       ├── tokens.py           # Token counting (planned)
│       ├── validators.py       # Input validation (planned)
│       └── prompt_variables.py # Dynamic prompt injection (planned)
├── alembic/
│   └── versions/               # Database migrations
├── tests/
│   ├── conftest.py             # Test fixtures
│   ├── unit/                   # Unit tests
│   └── integration/            # Integration tests
└── pyproject.toml              # Dependencies & config
```

---

## Database Schema (Planned)

### Entity Relationship Diagram

```
┌─────────────────┐
│   students      │ (existing, will extend)
├─────────────────┤
│ id (PK)         │
│ email           │◄───────┐
│ supabase_id     │        │ Foreign Keys
│ role*           │        │
│ credit_balance* │        │
│ referral_code*  │        │
│ referred_by_id* │───┐    │
│ is_premium*     │   │    │
└─────────────────┘   │    │
    │                 │    │
    │ 1:N             │    │
    ▼                 │    │
┌─────────────────┐   │    │
│ conversations   │   │    │
├─────────────────┤   │    │
│ id (PK)         │   │    │
│ user_id (FK)    │───┘    │
│ active_skill*   │        │
│ title           │        │
└─────────────────┘        │
    │                      │
    │ 1:N                  │
    ▼                      │
┌─────────────────┐        │
│   messages      │        │
├─────────────────┤        │
│ id (PK)         │        │
│ conversation_id │        │
│ role            │        │
│ content         │        │
│ skill_slug*     │───┐    │
│ provider_name*  │   │    │
│ input_tokens*   │   │    │
│ output_tokens*  │   │    │
│ cost_credits*   │   │    │
└─────────────────┘   │    │
                      │    │
┌─────────────────┐   │    │
│    skills       │◄──┘    │
├─────────────────┤        │
│ id (PK)         │        │
│ slug (UNIQUE)   │        │
│ system_prompt   │        │
│ temperature     │        │
│ preferred_prov* │───┐    │
│ fallback_prov*  │   │    │
│ is_premium*     │   │    │
│ cost_multiplier*│   │    │
└─────────────────┘   │    │
    │                 │    │
    │ 1:N             │    │
    ▼                 │    │
┌─────────────────┐   │    │
│  skill_tools    │   │    │
├─────────────────┤   │    │
│ id (PK)         │   │    │
│ skill_id (FK)   │   │    │
│ tool_name       │   │    │
│ tool_config     │   │    │
└─────────────────┘   │    │
                      │    │
┌─────────────────┐   │    │
│  ai_providers   │◄──┘    │
├─────────────────┤        │
│ id (PK)         │        │
│ slug (UNIQUE)   │        │
│ name            │        │
│ api_key_enc*    │        │
│ model_name      │        │
│ priority_weight*│        │
│ cost_per_1k*    │        │
│ is_active*      │        │
└─────────────────┘        │
                           │
┌─────────────────┐        │
│ credit_txns*    │        │
├─────────────────┤        │
│ id (PK)         │        │
│ user_id (FK)    │────────┘
│ amount          │
│ balance_after*  │
│ type*           │
│ reference_type* │
│ idempotency_key*│
└─────────────────┘
    ▲
    │
┌───┴──────────────┐
│ payment_invoices*│
├──────────────────┤
│ id (PK)          │
│ user_id (FK)     │
│ external_id      │
│ amount_usd       │
│ crypto_amount*   │
│ status*          │
│ webhook_payload* │
└──────────────────┘

┌─────────────────┐
│   referrals*    │
├─────────────────┤
│ id (PK)         │
│ referrer_id(FK) │
│ referred_id(FK) │
│ status*         │
│ rewarded_at*    │
└─────────────────┘
    │
    │ 1:N
    ▼
┌─────────────────┐
│ reward_txns*    │
├─────────────────┤
│ id (PK)         │
│ user_id (FK)    │
│ referral_id(FK) │
│ amount          │
│ status*         │
└─────────────────┘

┌─────────────────┐
│ webhook_events* │
├─────────────────┤
│ id (PK)         │
│ provider        │
│ external_id     │
│ payload         │
│ processed*      │
└─────────────────┘

┌─────────────────┐
│   audit_logs    │ (exists)
├─────────────────┤
│ id (PK)         │
│ actor_id (FK)*  │
│ action          │
│ entity_type     │
│ before_json*    │
│ after_json*     │
└─────────────────┘

* = New field or table (planned)
```

---

## Frontend Architecture

### Directory Structure (Planned)

```
frontend/
├── src/
│   ├── app/ or pages/
│   │   ├── index.tsx           # Home/chat page
│   │   ├── login.tsx           # Login page
│   │   ├── register.tsx        # Registration page
│   │   ├── billing.tsx         # Credits & payments
│   │   ├── referral.tsx        # Referral dashboard
│   │   └── admin/
│   │       ├── dashboard.tsx   # Admin overview
│   │       ├── providers.tsx   # AI provider management
│   │       ├── skills.tsx      # Skill management
│   │       ├── users.tsx       # User management
│   │       └── analytics.tsx   # Platform analytics
│   ├── components/
│   │   ├── chat/
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── MessageList.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── StreamingText.tsx
│   │   │   ├── Composer.tsx
│   │   │   └── SkillSelector.tsx
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Header.tsx
│   │   │   ├── ThemeToggle.tsx
│   │   │   └── UserMenu.tsx
│   │   ├── billing/
│   │   │   ├── CreditBalance.tsx
│   │   │   ├── PaymentModal.tsx
│   │   │   └── TransactionHistory.tsx
│   │   ├── referral/
│   │   │   ├── ReferralLink.tsx
│   │   │   ├── ReferralStats.tsx
│   │   │   └── InviteFriends.tsx
│   │   ├── admin/
│   │   │   ├── ProviderForm.tsx
│   │   │   ├── SkillForm.tsx
│   │   │   └── AnalyticsChart.tsx
│   │   └── ui/
│   │       ├── Button.tsx
│   │       ├── Input.tsx
│   │       ├── Modal.tsx
│   │       └── Card.tsx
│   ├── lib/
│   │   ├── api.ts              # Axios client with interceptors
│   │   ├── auth.ts             # Auth utilities
│   │   ├── streaming.ts        # SSE/streaming parser
│   │   ├── format.ts           # Date, currency formatting
│   │   └── rtl.ts              # RTL utilities
│   ├── hooks/
│   │   ├── useChat.ts          # Chat state & streaming
│   │   ├── useCredits.ts       # Credit balance
│   │   ├── useReferral.ts      # Referral data
│   │   └── useAdmin.ts         # Admin operations
│   ├── types/
│   │   ├── api.ts              # API request/response types
│   │   ├── chat.ts             # Chat types
│   │   └── admin.ts            # Admin types
│   └── styles/
│       ├── index.css           # Global styles, CSS variables
│       └── rtl.css             # RTL-specific overrides
├── public/
└── package.json
```

---

## Key Concepts

### 1. Skills System

**Child Explanation:**  
A skill is like a costume for the AI. When the AI wears the "math teacher" costume, it talks and thinks like a math teacher. When it wears the "code reviewer" costume, it acts like a programmer checking your code.

**Technical Details:**
- Each skill has:
  - `slug`: Unique identifier (e.g., "math-tutor", "essay-helper")
  - `system_prompt`: Instructions that shape the AI's behavior
  - `temperature`: Creativity level (0 = focused, 1 = creative)
  - `max_tokens`: Response length limit
  - `preferred_provider_id`: Primary LLM to use (e.g., Claude)
  - `fallback_provider_id`: Backup LLM if primary fails
  - `is_premium`: Requires subscription
  - `is_public`: Visible to all users
  - `cost_multiplier`: Adjusts credit cost (1.0 = normal, 2.0 = double)
  - `allowed_tools`: Functions the AI can call (e.g., web_search, calculator)

- Users can:
  - Select skills manually from UI
  - Optionally: System auto-routes to appropriate skill based on query

### 2. Multi-Provider LLM Router

**Child Explanation:**  
Imagine calling for pizza. If Pizza Place A doesn't answer, you automatically call Pizza Place B, then C. The LLM router does this with AI providers.

**Technical Details:**
- Supports multiple providers:
  - Anthropic Claude (claude-3-5-sonnet, etc.)
  - Google Gemini (gemini-1.5-pro, etc.)
  - OpenAI (gpt-4, gpt-3.5-turbo)
  - Qwen, Kimi (Chinese models)
- Failover logic:
  1. Try skill's preferred provider
  2. If fails (timeout, error, rate limit), try fallback provider
  3. If both fail, try global providers by priority_weight
  4. Track which provider succeeded for analytics
- Cost tracking:
  - Read `usage.input_tokens` and `usage.output_tokens` from response
  - Calculate cost: `(input_tokens * provider.cost_input_per_1k / 1000) + (output_tokens * provider.cost_output_per_1k / 1000)`
  - Multiply by skill's `cost_multiplier`
  - Deduct from user's credit balance
- Streaming:
  - Use SSE (Server-Sent Events) to stream tokens to frontend
  - Final event contains full usage metadata

### 3. Credit System

**Child Explanation:**  
Credits are like tokens in an arcade. Each time you ask the AI a question, it costs some tokens. When you run out, you buy more.

**Technical Details:**
- Each user has `credit_balance` (numeric, 2 decimal places)
- Every AI interaction costs credits based on:
  - Input tokens used
  - Output tokens generated
  - Provider's pricing
  - Skill's cost multiplier
- Credit transactions:
  - Type: `topup`, `spend`, `refund`, `referral_reward`, `admin_adjustment`, `bonus`
  - Each transaction records `balance_after` for audit trail
  - Uses `idempotency_key` to prevent duplicate charges
- Concurrency safety:
  - Use database row locking or atomic updates
  - Prevent race conditions where two requests spend same credits

### 4. Crypto Payment Gateway

**Child Explanation:**  
The user sends cryptocurrency (like Bitcoin or Ethereum) to a special address. When the blockchain confirms the payment, the system gives the user credits automatically.

**Technical Details:**
- Integration: NOWPayments or Cryptomus API
- Flow:
  1. User clicks "Buy Credits"
  2. Backend calls payment provider API to create invoice
  3. Backend receives:
     - `payment_address`: Crypto address to send funds to
     - `crypto_amount`: Amount in crypto (e.g., 0.001 BTC)
     - `qr_code_url`: QR code image for mobile wallets
     - `payment_url`: Deep link to wallet apps
  4. Frontend displays payment instructions
  5. User sends crypto
  6. Payment provider sends webhook to backend when:
     - Payment detected (status: confirming)
     - Payment confirmed (status: paid)
     - Payment expired (status: expired)
  7. Backend verifies webhook signature
  8. Backend adds credits to user's balance
  9. Backend triggers referral reward if applicable
- Security:
  - Webhook signature verification (HMAC-SHA256 or similar)
  - Idempotency using `payment_invoices.external_invoice_id`
  - Store raw webhook payload for debugging
  - Rate limit webhook endpoint
  - Validate paid amount >= expected amount

### 5. Referral System

**Child Explanation:**  
You give your friend a special invitation card. When your friend joins and buys credits, you get a small reward as a thank-you gift.

**Technical Details:**
- Each user gets unique `referral_code` (e.g., "SPETSER-AB12CD")
- Shareable link: `https://spetser.ai/r/SPETSER-AB12CD`
- Attribution:
  - During registration, capture `ref` query parameter
  - Store in `students.referred_by_user_id`
  - Create `referrals` row with status `pending`
- Qualification:
  - Referral becomes `qualified` after referred user makes first successful payment
- Reward:
  - Create `reward_transactions` row with status `pending`
  - Optionally delay reward release (e.g., 7 days holding period)
  - When released, add credits to referrer's balance
  - Mark reward as `paid`
- Anti-fraud:
  - Prevent self-referral
  - Track IP, user agent, email domain
  - Block disposable email domains
  - Admin can revoke suspicious referrals
  - One reward per referred user (unique constraint on `referrals.referred_user_id`)

### 6. Admin Dashboard

**Child Explanation:**  
The admin dashboard is the control room. Only trusted people can enter. They can see how many people are using the platform, change AI settings, and help users who have problems.

**Technical Details:**
- Role-based access: `students.role` = `admin`, `developer`, or `superadmin`
- Features:
  - **Provider Management**: Add/edit/disable AI providers, test connections, view usage stats
  - **Skill Management**: Create/edit skills, set prompts, assign providers, set pricing
  - **User Management**: View users, adjust credits, ban/unban, view transaction history
  - **Payment Management**: View invoices, manual confirm (with audit log)
  - **Referral Management**: View referrals, detect fraud patterns, revoke rewards
  - **Analytics**: Charts for revenue, AI usage by provider, top skills, user growth
  - **Audit Logs**: Search and filter sensitive actions
- Security:
  - All admin endpoints require authentication + role check
  - Sensitive actions logged to `audit_logs`
  - API keys displayed as masked (e.g., `sk-***abcd`)

---

## Data Flow Examples

### Example 1: User Sends Chat Message

```
1. User types message in frontend
2. Frontend selects skill (e.g., "math-tutor")
3. Frontend sends POST /api/v1/chat/completions
   {
     "conversation_id": "...",
     "message": "Solve x^2 + 5x + 6 = 0",
     "skill_slug": "math-tutor",
     "stream": true
   }

4. Backend authenticates user
5. Backend loads skill "math-tutor" from database
6. Backend checks user credit balance
7. Backend builds messages:
   - System: skill's system_prompt with {{user_name}} injected
   - History: previous messages in conversation
   - User: current message

8. Backend calls LLM Router:
   - Try preferred_provider (e.g., Claude)
   - If fails, try fallback_provider
   - Stream response tokens via SSE

9. Frontend receives SSE events:
   - event: token, data: "To"
   - event: token, data: " solve"
   - ...
   - event: done, data: { usage: {input_tokens: 120, output_tokens: 80}, cost_credits: 0.05 }

10. Backend records:
    - Insert message row (role: assistant, cost_credits: 0.05, provider_name: "claude", ...)
    - Insert credit_transaction (type: spend, amount: -0.05, ...)
    - Update user credit_balance

11. Frontend displays full response
```

### Example 2: User Buys Credits via Crypto

```
1. User clicks "Buy Credits" → selects $10 USD package
2. Frontend sends POST /api/v1/payments/create-invoice
   {
     "amount_usd": 10,
     "currency": "BTC",
     "idempotency_key": "uuid-..."
   }

3. Backend calls NOWPayments API:
   - POST /v1/payment
   - Receives: payment_id, pay_address, pay_amount, qr_code_data, pay_url

4. Backend inserts payment_invoices row:
   - external_invoice_id = payment_id
   - status = "pending"
   - crypto_address = pay_address

5. Backend returns:
   {
     "invoice_id": "...",
     "payment_address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
     "crypto_amount": "0.00025",
     "qr_code_url": "...",
     "expires_at": "2026-10-04T17:00:00Z"
   }

6. Frontend displays QR code and payment instructions
7. User sends Bitcoin to address
8. NOWPayments detects payment → sends webhook:
   POST /api/v1/payments/webhook
   Headers: x-nowpayments-sig: "hmac-sha256-signature"
   Body: { payment_id: "...", payment_status: "confirming", ... }

9. Backend:
   - Verifies signature
   - Checks webhook_events for duplicate (external_id = payment_id)
   - If duplicate, returns 200 (idempotency)
   - Inserts webhook_events row
   - Finds payment_invoice by external_invoice_id
   - Updates status = "confirming"

10. Blockchain confirms payment → NOWPayments sends another webhook:
    { payment_id: "...", payment_status: "finished", ... }

11. Backend:
    - Verifies signature
    - Updates payment_invoice status = "paid"
    - Adds credits to user (credit_transaction type: topup, amount: +1000)
    - Checks if user has referrer:
      - If yes, qualifies referral
      - Creates reward_transaction for referrer

12. User sees updated credit balance in UI
13. Referrer sees pending reward in dashboard
```

---

## Security Architecture

### Authentication & Authorization
- **Current**: Supabase Auth (JWT tokens)
- **Planned Enhancements**:
  - Role-based access control (RBAC) for admin endpoints
  - Refresh token rotation
  - Session management via Redis
  - Failed login attempt tracking
  - Account lockout after N failed attempts

### Encryption
- **Secrets in Environment**: All API keys, database URLs, JWT secrets stored in `.env`
- **Secrets in Database**: AI provider API keys encrypted with Fernet (symmetric encryption)
  - Master key stored in `LLM_MASTER_ENCRYPTION_KEY` env variable
  - Never log or return decrypted keys in API responses
  - Admin sees masked keys: `sk-***abcd`

### Input Validation
- All request bodies validated via Pydantic schemas
- Max lengths enforced (message content, skill prompts)
- Enum validation for status fields
- SQL injection prevented via ORM (SQLAlchemy)

### Rate Limiting
- `slowapi` middleware with Redis backend
- Limits:
  - Auth endpoints: 5/min per IP
  - Chat endpoints: 30/min per user
  - Payment webhook: Provider IP allowlist if available
  - Admin endpoints: 100/min per user

### Audit Logging
- All sensitive admin actions logged to `audit_logs`:
  - Provider API key changes
  - Manual credit adjustments
  - User bans
  - Manual payment confirmations
- Log includes:
  - `actor_user_id`: Who performed action
  - `action`: What happened
  - `before_json`, `after_json`: State changes
  - `ip_address`, `user_agent`: Request metadata

### Webhook Security
- Signature verification (HMAC-SHA256)
- Idempotency via `webhook_events.external_id` unique constraint
- Replay attack prevention (check timestamp if provider sends it)
- Rate limiting

---

## Technology Stack

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI 0.142+
- **Database**: PostgreSQL 14+ (via Supabase)
- **ORM**: SQLAlchemy 2.1+ (async)
- **Migrations**: Alembic 1.20+
- **Auth**: Supabase Auth (JWT)
- **Caching/Rate Limit**: Redis 7+
- **AI Libraries**: anthropic, google-generativeai, (openai optional)
- **Payment**: httpx for API calls to NOWPayments/Cryptomus
- **Logging**: structlog
- **Testing**: pytest, pytest-asyncio
- **Encryption**: cryptography (Fernet)

### Frontend
- **Language**: TypeScript 6.0+
- **Framework**: React 19.2+
- **Build Tool**: Vite 8.3+
- **Router**: react-router-dom 7.18+
- **Forms**: react-hook-form + zod
- **HTTP**: axios
- **State**: @tanstack/react-query
- **Styling**: CSS custom properties (CSS variables), RTL-aware logical properties
- **Linter**: oxlint

### Infrastructure
- **Database**: Supabase PostgreSQL
- **Storage**: Supabase Storage (for deliverables, future avatars)
- **Cache**: Redis (planned)
- **Deployment**: Docker + docker-compose (Phase 12)
- **CI/CD**: GitHub Actions (Phase 12)

---

## Deployment Architecture (Planned - Phase 12)

```
┌─────────────────────────────────────────────┐
│          Reverse Proxy (nginx)              │
│  • HTTPS termination                        │
│  • Rate limiting (backup)                   │
│  • Static file serving (frontend build)     │
└─────────────────┬───────────────────────────┘
                  │
        ┌─────────┼──────────┐
        │                    │
┌───────▼────────┐   ┌───────▼──────────┐
│ FastAPI        │   │ Frontend (static)│
│ (uvicorn)      │   │ (nginx)          │
│ • Horizontal   │   │ • Prerendered    │
│   scaling      │   │ • CDN-ready      │
│ • Health checks│   │                  │
└────────┬───────┘   └──────────────────┘
         │
    ┌────┼─────────────────┐
    │    │                 │
┌───▼────▼───┐   ┌─────────▼─────────┐
│ PostgreSQL │   │ Redis Cluster     │
│ (Supabase) │   │ • Cache           │
│ • Managed  │   │ • Rate limit      │
│ • Backups  │   │ • Sessions        │
└────────────┘   └───────────────────┘
```

---

## Scalability Considerations

### Backend Scaling
- Stateless API design (session in Redis or JWT)
- Horizontal scaling via multiple uvicorn workers/containers
- Database connection pooling (SQLAlchemy async pool)
- Caching frequently accessed data (skills, providers)

### Database Scaling
- Indexes on foreign keys and frequently queried columns
- Partitioning for large tables (messages, credit_transactions) if needed
- Read replicas for analytics queries (future)

### LLM Provider Scaling
- Multiple provider accounts to increase rate limits
- Provider priority_weight for load balancing
- Failover ensures uptime even if one provider down

### Cost Optimization
- Cheaper models for non-critical skills
- Caching common skill prompts
- Token usage monitoring and alerts

---

## Future Enhancements (Post-Phase 12)

- **Conversation Sharing**: Public links to conversations
- **Collaborative Skills**: Users can create and share custom skills
- **Voice Input/Output**: Speech-to-text and text-to-speech
- **Mobile Apps**: React Native or Flutter
- **Advanced Tools**: Web scraping, code execution sandbox, file uploads
- **Multi-Language UI**: Full translation beyond Arabic/English
- **Enterprise Plans**: Team accounts, usage analytics, custom models

---

**End of Architecture Documentation**
