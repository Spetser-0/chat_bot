# Spetser AI — Comprehensive API Documentation

Version: 2.0  
Base URL: `/api/v1`  
Protocol: HTTPS (HTTP/2 in production)  
Authentication: HTTP-only session cookie (`spetser_session`) or Bearer token (`Authorization: Bearer <JWT>`)

---

## 1. Authentication Endpoints

### 1.1 Register Student Account
- **Path**: `POST /api/v1/auth/register`
- **Auth**: Public (Rate-limited: 5 req/min by IP)
- **Request Body**:
  ```json
  {
    "email": "student@university.edu.ly",
    "password": "StrongPassword123!",
    "display_name": "Ahmed Mohamed"
  }
  ```
- **Query Parameters**: `?ref=REFERRAL_CODE` (optional)
- **Response** (`201 Created` or `200 OK`):
  ```json
  {
    "data": {
      "id": "e2f476a0-5cb3-487b-bb66-88dd61db2a54",
      "email": "student@university.edu.ly",
      "display_name": "Ahmed Mohamed",
      "role": "student",
      "status": "active",
      "credit_balance": "0.0000",
      "is_premium": false,
      "referral_code": "SPET-AHMED12"
    },
    "error": null,
    "request_id": "req-123456"
  }
  ```
- **Cookies**: Sets `spetser_session` (`HttpOnly`, `SameSite=Lax`, `Secure` in production).
- **Error Codes**: `400 BAD_REQUEST`, `409 EMAIL_ALREADY_EXISTS`, `422 VALIDATION_ERROR`, `429 RATE_LIMIT_EXCEEDED`
- **Example cURL**:
  ```bash
  curl -X POST http://localhost:8000/api/v1/auth/register \
    -H "Content-Type: application/json" \
    -d '{"email":"student@university.edu.ly","password":"StrongPassword123!","display_name":"Ahmed"}'
  ```

### 1.2 Login Student
- **Path**: `POST /api/v1/auth/login`
- **Auth**: Public (Rate-limited: 5 req/min by IP)
- **Request Body**:
  ```json
  {
    "email": "student@university.edu.ly",
    "password": "StrongPassword123!"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "data": {
      "id": "e2f476a0-5cb3-487b-bb66-88dd61db2a54",
      "email": "student@university.edu.ly",
      "display_name": "Ahmed Mohamed",
      "role": "student",
      "status": "active",
      "credit_balance": "50.0000",
      "is_premium": false
    },
    "error": null,
    "request_id": "req-123456"
  }
  ```
- **Error Codes**: `401 AUTH_ERROR`, `429 RATE_LIMIT_EXCEEDED`

### 1.3 Get Current User Profile
- **Path**: `GET /api/v1/auth/me`
- **Auth**: Active student session cookie or Bearer token
- **Response** (`200 OK`):
  ```json
  {
    "data": {
      "id": "e2f476a0-5cb3-487b-bb66-88dd61db2a54",
      "email": "student@university.edu.ly",
      "display_name": "Ahmed Mohamed",
      "role": "student",
      "credit_balance": "50.0000",
      "is_premium": false
    },
    "error": null
  }
  ```
- **Error Codes**: `401 AUTH_ERROR`

### 1.4 Logout
- **Path**: `POST /api/v1/auth/logout`
- **Auth**: Session cookie
- **Response** (`200 OK`): Revokes cookie and increments student `session_version`.

---

## 2. Chat & AI Completions

### 2.1 Send Message / Completions
- **Path**: `POST /api/v1/chat/completions`
- **Auth**: Active student (Rate-limited: 20 req/min, 200/day)
- **Request Body**:
  ```json
  {
    "message": "اشرح لي خوارزمية البحث الثنائي بالتفصيل مع مثال بالبايثون",
    "conversation_id": "optional-uuid",
    "skill_slug": "tutor",
    "stream": true,
    "regenerate": false
  }
  ```
- **Response**:
  - If `stream: false`: `ChatCompletionResponse` JSON with content, token counts, and cost in USD.
  - If `stream: true`: `text/event-stream` Server-Sent Events (`event: conversation`, `event: start`, `event: chunk`, `event: done`).
- **Error Codes**: `401 AUTH_ERROR`, `402 INSUFFICIENT_CREDITS`, `403 FORBIDDEN`, `429 RATE_LIMIT_EXCEEDED`, `502 PROVIDER_ERROR`
- **Example cURL**:
  ```bash
  curl -N -X POST http://localhost:8000/api/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Cookie: spetser_session=..." \
    -d '{"message":"مرحبا","stream":true}'
  ```

---

## 3. Conversations Lifecycle

### 3.1 List User Conversations
- **Path**: `GET /api/v1/conversations?include_archived=false`
- **Auth**: Active student

### 3.2 Get Conversation Detail
- **Path**: `GET /api/v1/conversations/{id}`
- **Auth**: Active student (Strict IDOR ownership enforced)

### 3.3 Update Conversation
- **Path**: `PATCH /api/v1/conversations/{id}`
- **Auth**: Active student
- **Request Body**:
  ```json
  {
    "title": "مذاكرة الخوارزميات",
    "is_archived": false
  }
  ```

### 3.4 Delete Conversation
- **Path**: `DELETE /api/v1/conversations/{id}`
- **Auth**: Active student

---

## 4. Credits & Wallet

### 4.1 Get Credit Balance
- **Path**: `GET /api/v1/credits/balance`
- **Auth**: Active student
- **Response** (`200 OK`):
  ```json
  {
    "data": {
      "balance": "120.5000",
      "credits_per_usd": "10.0"
    }
  }
  ```

### 4.2 Get Credit History
- **Path**: `GET /api/v1/credits/history?limit=20&offset=0`
- **Auth**: Active student

### 4.3 Test Credit Grant (Development Only)
- **Path**: `POST /api/v1/credits/grant`
- **Auth**: Active student (Denied with `403 FORBIDDEN` in production)

---

## 5. Payments & Invoices

### 5.1 Create Crypto Invoice
- **Path**: `POST /api/v1/payments/create-invoice`
- **Auth**: Active student
- **Request Body**:
  ```json
  {
    "amount_usd": 10.0,
    "currency": "USDT",
    "idempotency_key": "buy-1730000000-xyz",
    "description": "Credit Pack Topup"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "data": {
      "invoice_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "amount_usd": "10.00",
      "amount_crypto": "10.000000",
      "currency": "USDT",
      "pay_address": "TQj8...depositAddress",
      "payment_url": "https://gateway.example.com/pay/...",
      "status": "PENDING"
    }
  }
  ```

### 5.2 Poll Invoice Status
- **Path**: `GET /api/v1/payments/{invoice_id}/status`
- **Auth**: Active student (Owner)

### 5.3 Webhook Ingress
- **Path**: `POST /api/v1/payments/webhook`
- **Auth**: HMAC-SHA512 header verification (`x-signature` / `sign`)

---

## 6. Referrals & Growth

### 6.1 Validate Referral Code (Public)
- **Path**: `GET /api/v1/referrals/{code}/validate`
- **Auth**: Public (Rate-limited: 30 req/min)

### 6.2 Get Personal Referral Link & Stats
- **Path**: `GET /api/v1/referrals/link`
- **Path**: `GET /api/v1/referrals/me`
- **Path**: `GET /api/v1/referrals/stats`
- **Auth**: Active student

---

## 7. AI Skills Catalogue

### 7.1 List Public Skills
- **Path**: `GET /api/v1/skills`
- **Auth**: Public

### 7.2 Get Skill Details
- **Path**: `GET /api/v1/skills/{slug}`
- **Auth**: Public (System prompts are never returned)

---

## 8. Administrative Endpoints (`/api/v1/admin/*`)
Requires `developer`, `admin`, or `superadmin` role. All routes share `rate_limit_admin` (60 req/min).

| Endpoint | Method | Required Role | Description |
|---|---|---|---|
| `/api/v1/admin/analytics/overview` | GET | `developer` | Platform metrics overview |
| `/api/v1/admin/analytics/llm-usage` | GET | `developer` | Token & latency metrics by provider/skill |
| `/api/v1/admin/analytics/revenue` | GET | `developer` | Revenue and invoice aggregates |
| `/api/v1/admin/analytics/referrals` | GET | `developer` | Referral funnel and reward liability |
| `/api/v1/admin/users` | GET | `developer` | Search and filter users |
| `/api/v1/admin/users/{id}` | GET | `developer` | Detailed student profile |
| `/api/v1/admin/users/{id}/ban` | POST | `admin` | Ban user and revoke sessions |
| `/api/v1/admin/users/{id}/unban` | POST | `admin` | Unban user and reset lockouts |
| `/api/v1/admin/users/{id}/adjust-credits` | POST | `admin` | Manual credit adjustment with audit |
| `/api/v1/admin/providers` | GET/POST | `developer`/`admin` | List or create AI providers (keys encrypted) |
| `/api/v1/admin/providers/{slug}` | PATCH/DELETE | `admin` | Update or remove AI provider |
| `/api/v1/admin/skills` | GET/POST | `developer`/`admin` | List or create AI skills |
| `/api/v1/admin/payments/{id}/manual-confirm` | POST | `superadmin` | Manually credit wallet for invoice |
| `/api/v1/admin/audit-logs` | GET | `developer` | Search immutable audit trail |
| `/api/v1/admin/metrics` | GET | `developer` | Process telemetry counters |
