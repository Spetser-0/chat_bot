# Spetser AI - Complete Database ERD

**Last Updated**: 2026-10-04T17:41:18Z  
**Phase**: 1 - Database Foundation  
**Status**: Design Complete, Implementation Pending

---

## Overview

This document provides the complete Entity-Relationship Diagram (ERD) for Spetser AI, showing both existing tables and new tables to be created in Phase 1.

---

## Legend

- ✅ **GREEN** = Existing table (already implemented)
- 🔧 **ORANGE** = Existing table to be extended
- ⏳ **BLUE** = New table to be created

---

## Complete Schema Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  🔧 students (EXTEND)                                           │
├─────────────────────────────────────────────────────────────────┤
│ • id                          UUID PK                           │
│ • external_auth_id            VARCHAR(255) UNIQUE              │
│ • email                       VARCHAR(320) UNIQUE ✓            │
│ • display_name                VARCHAR(200)                      │
│ • password_hash               VARCHAR(255)                      │
│ • phone_number                VARCHAR(30)                       │
│ • role                        VARCHAR(20) ✓ [extend enum]      │
│ • status                      VARCHAR(20)                       │
│ • session_version             INTEGER                           │
│ • credit_balance              NUMERIC(18,4)                     │
│ ━━━ NEW FIELDS (Lesson 1.3) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│ • referral_code               VARCHAR(20) UNIQUE ⏳            │
│ • referred_by_user_id         UUID FK(students.id) ⏳          │
│ • is_premium                  BOOLEAN DEFAULT false ⏳          │
│ • premium_expires_at          TIMESTAMPTZ ⏳                    │
│ • failed_login_attempts       INTEGER DEFAULT 0 ⏳             │
│ • locked_until                TIMESTAMPTZ ⏳                    │
│ • last_login_ip               VARCHAR(45) ⏳                    │
│ • created_at                  TIMESTAMPTZ                       │
│ • updated_at                  TIMESTAMPTZ                       │
└─────────────────────────────────────────────────────────────────┘
           │
           │ 1:N (referrer)
           ├──────────────────────────────┐
           │                              │
           │ 1:N (referred users)         │
           ├─────────────┐                │
           │             │                │
           │             ▼                ▼
           │   ┌─────────────────────────────────────────────┐
           │   │  ⏳ referrals (NEW - Lesson 1.11)          │
           │   ├─────────────────────────────────────────────┤
           │   │ • id                    UUID PK             │
           │   │ • referrer_user_id      UUID FK ✓          │
           │   │ • referred_user_id      UUID FK ✓ UNIQUE   │
           │   │ • referral_code         VARCHAR(20)         │
           │   │ • landing_page_url      TEXT                │
           │   │ • ip_address            INET                │
           │   │ • user_agent            TEXT                │
           │   │ • status                VARCHAR(20)         │
           │   │   - pending, qualified, rewarded, revoked   │
           │   │ • qualified_at          TIMESTAMPTZ         │
           │   │ • rewarded_at           TIMESTAMPTZ         │
           │   │ • created_at            TIMESTAMPTZ         │
           │   └─────────────────────────────────────────────┘
           │                │
           │                │ 1:N
           │                ▼
           │   ┌─────────────────────────────────────────────┐
           │   │  ⏳ reward_transactions (NEW - Lesson 1.12) │
           │   ├─────────────────────────────────────────────┤
           │   │ • id                    UUID PK             │
           │   │ • user_id               UUID FK(students) ✓ │
           │   │ • referral_id           UUID FK             │
           │   │ • amount                NUMERIC(10,2)       │
           │   │ • currency              VARCHAR(10)         │
           │   │ • type                  VARCHAR(50)         │
           │   │   - signup_bonus, subscription_commission   │
           │   │ • status                VARCHAR(20)         │
           │   │   - pending, payable, paid, revoked         │
           │   │ • scheduled_release_at  TIMESTAMPTZ         │
           │   │ • reference_invoice_id  UUID FK(invoices)   │
           │   │ • created_at            TIMESTAMPTZ         │
           │   │ • updated_at            TIMESTAMPTZ         │
           │   └─────────────────────────────────────────────┘
           │
           │ 1:N
           ├──────────────────────────────┐
           │                              │
           ▼                              │
┌─────────────────────────────────┐       │
│  ⏳ payment_invoices (NEW)      │       │
│     (Lesson 1.10)               │       │
├─────────────────────────────────┤       │
│ • id                 UUID PK    │       │
│ • user_id            UUID FK ✓  │───────┘
│ • provider           VARCHAR(50)│
│ • external_invoice_id VARCHAR UNIQUE │
│ • amount_usd         NUMERIC(10,2) │
│ • currency           VARCHAR(10)│
│ • crypto_amount      NUMERIC(20,8)│
│ • crypto_address     TEXT       │
│ • payment_url        TEXT       │
│ • qr_code_url        TEXT       │
│ • status             VARCHAR(20)│
│   - pending, confirming,       │
│     paid, expired, failed       │
│ • expires_at         TIMESTAMPTZ│
│ • paid_at            TIMESTAMPTZ│
│ • webhook_payload    JSONB     │
│ • idempotency_key    VARCHAR UNIQUE │
│ • created_at         TIMESTAMPTZ│
│ • updated_at         TIMESTAMPTZ│
└─────────────────────────────────┘
           │
           │ Referenced by
           ▼
┌─────────────────────────────────┐
│  ⏳ webhook_events (NEW)        │
│     (Lesson 1.13)               │
├─────────────────────────────────┤
│ • id                 UUID PK    │
│ • provider           VARCHAR(50)│
│ • event_type         VARCHAR(100)│
│ • external_id        VARCHAR(255)│
│ • payload            JSONB      │
│ • signature          VARCHAR(500)│
│ • processed          BOOLEAN    │
│ • processed_at       TIMESTAMPTZ│
│ • error              TEXT       │
│ • created_at         TIMESTAMPTZ│
│ • UNIQUE(provider, external_id) │
└─────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  ⏳ ai_providers (NEW - Lesson 1.4)                             │
├─────────────────────────────────────────────────────────────────┤
│ • id                          UUID PK                           │
│ • name                        VARCHAR(100)                      │
│ • slug                        VARCHAR(50) UNIQUE               │
│ • base_url                    VARCHAR(500)                      │
│ • model_name                  VARCHAR(100)                      │
│ • api_key_encrypted           TEXT                             │
│ • priority_weight             INTEGER DEFAULT 100               │
│ • timeout_seconds             INTEGER DEFAULT 30                │
│ • max_retries                 INTEGER DEFAULT 3                 │
│ • cost_input_per_1k           NUMERIC(10,6)                    │
│ • cost_output_per_1k          NUMERIC(10,6)                    │
│ • is_active                   BOOLEAN DEFAULT true              │
│ • is_primary                  BOOLEAN DEFAULT false             │
│ • metadata                    JSONB                             │
│ • created_at                  TIMESTAMPTZ                       │
│ • updated_at                  TIMESTAMPTZ                       │
└─────────────────────────────────────────────────────────────────┘
           │
           │ Referenced by (preferred_provider_id)
           │ Referenced by (fallback_provider_id)
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│  ⏳ skills (NEW - Lesson 1.5)                                   │
├─────────────────────────────────────────────────────────────────┤
│ • id                          UUID PK                           │
│ • name                        VARCHAR(100)                      │
│ • slug                        VARCHAR(50) UNIQUE               │
│ • description                 TEXT                              │
│ • system_prompt               TEXT                              │
│ • temperature                 NUMERIC(3,2) DEFAULT 0.7          │
│ • max_tokens                  INTEGER DEFAULT 4096              │
│ • preferred_provider_id       UUID FK(ai_providers.id)         │
│ • fallback_provider_id        UUID FK(ai_providers.id)         │
│ • is_public                   BOOLEAN DEFAULT false             │
│ • is_premium                  BOOLEAN DEFAULT false             │
│ • cost_multiplier             NUMERIC(4,2) DEFAULT 1.0          │
│ • version                     INTEGER DEFAULT 1                 │
│ • created_by_user_id          UUID FK(students.id)             │
│ • created_at                  TIMESTAMPTZ                       │
│ • updated_at                  TIMESTAMPTZ                       │
│ • CHECK (temperature BETWEEN 0.0 AND 2.0)                      │
│ • CHECK (max_tokens > 0)                                        │
│ • CHECK (cost_multiplier > 0)                                   │
└─────────────────────────────────────────────────────────────────┘
           │
           │ 1:N
           ▼
┌─────────────────────────────────────────────────────────────────┐
│  ⏳ skill_tools (NEW - Lesson 1.6)                              │
├─────────────────────────────────────────────────────────────────┤
│ • id                          UUID PK                           │
│ • skill_id                    UUID FK(skills.id) ON DELETE CASCADE│
│ • tool_name                   VARCHAR(50)                       │
│ • tool_config                 JSONB                             │
│ • is_enabled                  BOOLEAN DEFAULT true              │
│ • created_at                  TIMESTAMPTZ                       │
│ • UNIQUE(skill_id, tool_name)                                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  ⏳ conversations (NEW - Lesson 1.7)                            │
├─────────────────────────────────────────────────────────────────┤
│ • id                          UUID PK                           │
│ • user_id                     UUID FK(students.id) ON DELETE CASCADE│
│ • title                       VARCHAR(500)                      │
│ • active_skill_slug           VARCHAR(50)                       │
│ • is_archived                 BOOLEAN DEFAULT false             │
│ • created_at                  TIMESTAMPTZ                       │
│ • updated_at                  TIMESTAMPTZ                       │
└─────────────────────────────────────────────────────────────────┘
           │
           │ 1:N
           ▼
┌─────────────────────────────────────────────────────────────────┐
│  ⏳ messages (NEW - Lesson 1.8)                                 │
├─────────────────────────────────────────────────────────────────┤
│ • id                          UUID PK                           │
│ • conversation_id             UUID FK(conversations.id) ON DELETE CASCADE│
│ • role                        VARCHAR(20)                       │
│   - system, user, assistant, tool                               │
│ • content                     TEXT                              │
│ • skill_slug                  VARCHAR(50)                       │
│ • provider_name               VARCHAR(100)                      │
│ • model_name                  VARCHAR(100)                      │
│ • input_tokens                INTEGER                           │
│ • output_tokens               INTEGER                           │
│ • cost_credits                NUMERIC(18,4)                     │
│ • latency_ms                  INTEGER                           │
│ • created_at                  TIMESTAMPTZ                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  🔧 credit_ledger (EXTEND - Lesson 1.9)                         │
├─────────────────────────────────────────────────────────────────┤
│ • id                          UUID PK                           │
│ • student_id                  UUID FK(students.id)             │
│ • request_id                  UUID FK(requests.id)             │
│ • provider                    VARCHAR(100)                      │
│ • model                       VARCHAR(100)                      │
│ • input_tokens                INTEGER                           │
│ • output_tokens               INTEGER                           │
│ • computed_usd_cost           NUMERIC(18,8)                     │
│ • pricing_version             VARCHAR(50)                       │
│ • credits_charged             NUMERIC(18,4)                     │
│ • entry_type                  VARCHAR(20)                       │
│ • idempotency_key             VARCHAR(255) UNIQUE              │
│ ━━━ NEW FIELDS (Lesson 1.9) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│ • balance_after               NUMERIC(18,4) ⏳                  │
│ • reference_type              VARCHAR(50) ⏳                    │
│ • reference_id                UUID ⏳                            │
│ • description                 TEXT ⏳                            │
│ • created_at                  TIMESTAMPTZ                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  ✅ audit_logs (EXISTING - No changes needed)                   │
├─────────────────────────────────────────────────────────────────┤
│ • id                          UUID PK                           │
│ • actor_id                    UUID FK(students.id)             │
│ • action                      VARCHAR(100)                      │
│ • resource_type               VARCHAR(100)                      │
│ • resource_id                 VARCHAR(255)                      │
│ • metadata_json               JSONB                             │
│ • correlation_id              VARCHAR(100)                      │
│ • created_at                  TIMESTAMPTZ                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  ✅ OTHER EXISTING TABLES (Not modified in Phase 1)            │
├─────────────────────────────────────────────────────────────────┤
│ • requests                    (existing, unchanged)              │
│ • deliverables                (existing, unchanged)              │
│ • prompt_versions             (existing, unchanged)              │
│ • providers                   (existing, may deprecate later)    │
│ • model_configurations        (existing, may deprecate later)    │
│ • feature_configurations      (existing, may deprecate later)    │
│ • routing_rules               (existing, may deprecate later)    │
│ • source_records              (existing, unchanged)              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Table Summary

### Tables to Extend (2)

| Table | Lesson | New Fields | Status |
|-------|--------|------------|--------|
| `students` | 1.3 | 7 fields (referral, premium, security) | 🔧 Pending |
| `credit_ledger` | 1.9 | 4 fields (balance_after, reference_type, reference_id, description) | 🔧 Pending |

### New Tables to Create (9)

| Table | Lesson | Purpose | Status |
|-------|--------|---------|--------|
| `ai_providers` | 1.4 | Multi-provider management | ⏳ Pending |
| `skills` | 1.5 | AI personality configs | ⏳ Pending |
| `skill_tools` | 1.6 | Skill-tool associations | ⏳ Pending |
| `conversations` | 1.7 | Chat sessions | ⏳ Pending |
| `messages` | 1.8 | Chat history | ⏳ Pending |
| `payment_invoices` | 1.10 | Crypto payments | ⏳ Pending |
| `referrals` | 1.11 | User referral tracking | ⏳ Pending |
| `reward_transactions` | 1.12 | Referral rewards | ⏳ Pending |
| `webhook_events` | 1.13 | Payment webhook dedup | ⏳ Pending |

### Existing Tables (No Changes) (8)

- `audit_logs` ✅
- `requests` ✅
- `deliverables` ✅
- `prompt_versions` ✅
- `providers` ✅ (legacy, may deprecate)
- `model_configurations` ✅ (legacy, may deprecate)
- `feature_configurations` ✅ (legacy, may deprecate)
- `routing_rules` ✅ (legacy, may deprecate)

---

## Relationships Overview

### Primary Relationships

```
students (1) ──────────> (N) conversations
students (1) ──────────> (N) credit_ledger
students (1) ──────────> (N) payment_invoices
students (1) ──────────> (N) referrals (as referrer)
students (1) ──────────> (1) referrals (as referred)
students (1) ──────────> (N) reward_transactions
students (1) ──────────> (N) audit_logs (as actor)
students (1) ──────────> (N) skills (as creator)

conversations (1) ─────> (N) messages

referrals (1) ─────────> (N) reward_transactions

payment_invoices (1) ──> (N) reward_transactions (reference)

ai_providers (1) ──────> (N) skills (preferred)
ai_providers (1) ──────> (N) skills (fallback)

skills (1) ────────────> (N) skill_tools
skills (1) ────────────> (N) messages (used_skill)
```

---

## Indexes Required

### Lesson 1.15 - All Indexes

```sql
-- students (new indexes)
CREATE INDEX idx_students_referral_code ON students(referral_code);
CREATE INDEX idx_students_referred_by ON students(referred_by_user_id);
CREATE INDEX idx_students_is_premium ON students(is_premium) WHERE is_premium = true;

-- ai_providers
CREATE INDEX idx_providers_slug ON ai_providers(slug);
CREATE INDEX idx_providers_is_active ON ai_providers(is_active);
CREATE INDEX idx_providers_priority ON ai_providers(priority_weight DESC);

-- skills
CREATE INDEX idx_skills_slug ON skills(slug);
CREATE INDEX idx_skills_is_public ON skills(is_public) WHERE is_public = true;
CREATE INDEX idx_skills_is_premium ON skills(is_premium) WHERE is_premium = true;
CREATE INDEX idx_skills_preferred_provider ON skills(preferred_provider_id);
CREATE INDEX idx_skills_fallback_provider ON skills(fallback_provider_id);

-- skill_tools
CREATE INDEX idx_skill_tools_skill_id ON skill_tools(skill_id);

-- conversations
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_is_archived ON conversations(is_archived);
CREATE INDEX idx_conversations_created_at ON conversations(created_at DESC);

-- messages
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_skill_slug ON messages(skill_slug);
CREATE INDEX idx_messages_created_at ON messages(created_at);

-- credit_ledger (new indexes)
CREATE INDEX idx_credit_ledger_reference ON credit_ledger(reference_type, reference_id);

-- payment_invoices
CREATE INDEX idx_invoices_user_id ON payment_invoices(user_id);
CREATE INDEX idx_invoices_status ON payment_invoices(status);
CREATE INDEX idx_invoices_external_id ON payment_invoices(external_invoice_id);
CREATE INDEX idx_invoices_created_at ON payment_invoices(created_at DESC);

-- referrals
CREATE INDEX idx_referrals_referrer ON referrals(referrer_user_id);
CREATE INDEX idx_referrals_referred ON referrals(referred_user_id);
CREATE INDEX idx_referrals_status ON referrals(status);
CREATE INDEX idx_referrals_code ON referrals(referral_code);

-- reward_transactions
CREATE INDEX idx_rewards_user_id ON reward_transactions(user_id);
CREATE INDEX idx_rewards_referral_id ON reward_transactions(referral_id);
CREATE INDEX idx_rewards_status ON reward_transactions(status);
CREATE INDEX idx_rewards_scheduled ON reward_transactions(scheduled_release_at);

-- webhook_events
CREATE INDEX idx_webhooks_processed ON webhook_events(processed);
CREATE INDEX idx_webhooks_provider_external ON webhook_events(provider, external_id);
```

---

## Constraints Summary

### Check Constraints

```sql
-- students
ALTER TABLE students ADD CONSTRAINT chk_credit_balance_positive 
    CHECK (credit_balance >= 0);
ALTER TABLE students ADD CONSTRAINT chk_failed_attempts_non_negative 
    CHECK (failed_login_attempts >= 0);

-- skills
ALTER TABLE skills ADD CONSTRAINT chk_temperature_range 
    CHECK (temperature BETWEEN 0.0 AND 2.0);
ALTER TABLE skills ADD CONSTRAINT chk_max_tokens_positive 
    CHECK (max_tokens > 0);
ALTER TABLE skills ADD CONSTRAINT chk_cost_multiplier_positive 
    CHECK (cost_multiplier > 0);

-- payment_invoices
ALTER TABLE payment_invoices ADD CONSTRAINT chk_amount_positive 
    CHECK (amount_usd > 0);
ALTER TABLE payment_invoices ADD CONSTRAINT chk_crypto_amount_positive 
    CHECK (crypto_amount IS NULL OR crypto_amount > 0);

-- reward_transactions
ALTER TABLE reward_transactions ADD CONSTRAINT chk_reward_amount_positive 
    CHECK (amount > 0);

-- referrals
ALTER TABLE referrals ADD CONSTRAINT chk_no_self_referral 
    CHECK (referrer_user_id != referred_user_id);
```

### Unique Constraints

```sql
-- Already defined in column definitions
-- students.referral_code UNIQUE
-- students.email UNIQUE
-- ai_providers.slug UNIQUE
-- skills.slug UNIQUE
-- skill_tools (skill_id, tool_name) UNIQUE
-- payment_invoices.external_invoice_id UNIQUE
-- payment_invoices.idempotency_key UNIQUE
-- referrals.referred_user_id UNIQUE
-- webhook_events (provider, external_id) UNIQUE
-- credit_ledger.idempotency_key UNIQUE
```

---

## Data Types Reference

### Common Types Used

| Type | Usage | Example |
|------|-------|---------|
| `UUID` | Primary keys, foreign keys | `id`, `user_id` |
| `VARCHAR(n)` | Strings with known max length | `email`, `slug` |
| `TEXT` | Unlimited length strings | `system_prompt`, `content` |
| `NUMERIC(p,s)` | Monetary values | `NUMERIC(18,4)` for credits |
| `INTEGER` | Whole numbers | `priority_weight`, `tokens` |
| `BOOLEAN` | True/false flags | `is_active`, `is_premium` |
| `TIMESTAMPTZ` | Timestamps with timezone | `created_at`, `expires_at` |
| `JSONB` | Structured JSON data | `metadata`, `payload` |
| `INET` | IP addresses (PostgreSQL) | `ip_address` |

### Why NUMERIC for Money

❌ **Never use FLOAT or DOUBLE for money!**
- Floating point has rounding errors
- 0.1 + 0.2 ≠ 0.3 in float arithmetic

✅ **Always use NUMERIC/DECIMAL**
- Exact decimal representation
- No rounding errors
- Safe for financial calculations

---

## Migration Order (Lesson 1.16)

The migration must create tables in this order to respect foreign key dependencies:

1. ✅ `students` (extend existing - add new columns)
2. ⏳ `ai_providers` (no dependencies)
3. ⏳ `skills` (depends on: ai_providers, students)
4. ⏳ `skill_tools` (depends on: skills)
5. ⏳ `conversations` (depends on: students)
6. ⏳ `messages` (depends on: conversations)
7. ✅ `credit_ledger` (extend existing - add new columns)
8. ⏳ `payment_invoices` (depends on: students)
9. ⏳ `referrals` (depends on: students)
10. ⏳ `reward_transactions` (depends on: students, referrals, payment_invoices)
11. ⏳ `webhook_events` (no dependencies)

---

## Estimated Row Counts (First Year)

| Table | Estimated Rows | Growth Rate |
|-------|---------------|-------------|
| students | 10,000 | Steady |
| conversations | 50,000 | 5 per user |
| messages | 500,000 | 10 per conversation |
| credit_ledger | 500,000 | 1 per message + topups |
| payment_invoices | 5,000 | 0.5 per user |
| referrals | 3,000 | 30% referral rate |
| reward_transactions | 3,000 | 1 per qualified referral |
| webhook_events | 15,000 | 3 per payment (avg) |
| skills | 50 | Managed by admins |
| skill_tools | 150 | 3 per skill (avg) |
| ai_providers | 10 | Managed by admins |
| audit_logs | 10,000 | Admin actions only |

**Largest tables**: `messages` (500K), `credit_ledger` (500K)  
**Indexing critical for**: conversations, messages queries

---

## Next Steps

With this ERD complete, we can now:
1. Begin Lesson 1.3: Extend students table
2. Continue through Lessons 1.4-1.13: Create new tables
3. Lesson 1.15: Add all indexes and constraints
4. Lesson 1.16: Generate single comprehensive migration
5. Lesson 1.17: Write complete test suite

---

**ERD Status**: ✅ **DESIGN COMPLETE**  
**Next**: Lesson 1.3 - Extend students table with 7 new fields

