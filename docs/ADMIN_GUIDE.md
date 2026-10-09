# Spetser AI - Admin Guide

**Last Updated**: 2026-10-04  
**Status**: Phase 0 - Initial Design (Phase 8 Implementation)

---

## Overview

The Admin Dashboard provides tools for platform administrators, developers, and superadmins to manage the Spetser AI platform.

---

## User Roles

| Role | Permissions |
|------|-------------|
| `user` | Standard user (default) - can use platform, buy credits, refer friends |
| `admin` | Can manage users, view payments, manage referrals |
| `developer` | Can manage AI providers, skills, view logs, access developer APIs |
| `superadmin` | Full access - can perform manual payment confirms, grant/revoke roles |

---

## Admin Dashboard Features

### 1. Provider Management (`/admin/providers`)

**View All Providers**
- List active and inactive AI providers
- See usage statistics per provider
- View cost per 1k tokens
- Check last successful call timestamp

**Add New Provider**
- Provider name and slug
- API base URL
- Model name
- API key (encrypted automatically)
- Cost rates (input/output per 1k tokens)
- Priority weight (for load balancing)
- Timeout and retry settings

**Edit Provider**
- Update API key
- Adjust cost rates
- Change priority weight
- Toggle active status

**Test Provider**
- Send test prompt
- Verify API key works
- Check latency

**Security**: API keys displayed as `sk-***abcd` (masked). Never show full key.

---

### 2. Skill Management (`/admin/skills`)

**View All Skills**
- Public and private skills
- Usage stats (messages per skill)
- Average cost per skill

**Create New Skill**
- Name, slug, description
- System prompt (with variable helper)
- Temperature and max tokens
- Preferred and fallback providers
- Public/private flag
- Premium flag
- Cost multiplier
- Allowed tools

**Edit Skill**
- Update prompt (increments version)
- Change providers
- Adjust cost multiplier

**Test Skill**
- Send test message
- Preview AI response
- Verify prompt variables inject correctly

---

### 3. User Management (`/admin/users`)

**Search Users**
- By email, ID, or referral code
- Filter by role, premium status

**View User Details**
- Email, registration date
- Credit balance, total spent
- Referrals made
- Payment history
- Recent activity

**Manage User**
- Adjust credits (with reason logged)
- Grant/revoke premium
- Ban/unban (prevents login and API access)
- Change role (admin only for superadmin)

**User Timeline**
- Credit transactions
- Payments
- Messages sent
- Skills used

---

### 4. Payment Management (`/admin/payments`)

**View All Payments**
- Filter by status, user, date range
- Sort by amount, date

**Invoice Details**
- User info
- Amount (USD and crypto)
- Payment address
- Status history
- Webhook payload (raw JSON)

**Manual Actions** (superadmin only)
- Manual confirm (if webhook failed but blockchain shows payment)
- Mark as refunded
- All manual actions logged to audit log

**Revenue Analytics**
- Daily/weekly/monthly revenue
- Total by payment method
- Average transaction size

---

### 5. Referral Management (`/admin/referrals`)

**View All Referrals**
- Filter by status
- Flag suspicious referrals
- Sort by qualified date

**Referral Details**
- Referrer and referred user
- Attribution data (IP, user agent)
- Payment that qualified referral
- Reward status
- Fraud indicators

**Actions**
- Revoke referral (cancels rewards)
- Manual reward release
- Block referral code

**Fraud Detection**
- Multiple referrals from same IP
- Disposable emails
- Rapid payment patterns

---

### 6. Analytics (`/admin/analytics`)

**Overview Dashboard**
- Total users, active users (7/30 days)
- Total revenue (all time, this month)
- Total messages sent
- Average credits per user

**AI Usage**
- Messages per provider
- Token usage per provider
- Cost breakdown
- Failover rate

**Skills Analytics**
- Most popular skills
- Average cost per skill
- Premium vs free skill usage

**User Growth**
- New users per day/week/month
- Referral conversion rate
- Premium conversion rate

**Charts**
- Revenue over time
- User growth
- Token usage

---

### 7. Audit Logs (`/admin/audit-logs`)

**Search Logs**
- Filter by actor, action, entity type
- Date range

**Log Entries Show**
- Who (actor)
- What (action)
- When (timestamp)
- Where (IP address)
- Before/After (JSON diff)

**Common Actions Logged**
- Provider API key changes
- Manual credit adjustments
- User bans
- Role grants
- Manual payment confirms
- Referral revocations

---

## Admin API Endpoints

### Provider Management

```
GET    /api/v1/admin/providers
POST   /api/v1/admin/providers
GET    /api/v1/admin/providers/{id}
PATCH  /api/v1/admin/providers/{id}
DELETE /api/v1/admin/providers/{id}
POST   /api/v1/admin/providers/{id}/test
POST   /api/v1/admin/providers/{id}/toggle
```

### Skill Management

```
GET    /api/v1/admin/skills
POST   /api/v1/admin/skills
GET    /api/v1/admin/skills/{id}
PATCH  /api/v1/admin/skills/{id}
DELETE /api/v1/admin/skills/{id}
POST   /api/v1/admin/skills/{id}/test
```

### User Management

```
GET    /api/v1/admin/users
GET    /api/v1/admin/users/{id}
POST   /api/v1/admin/users/{id}/adjust-credits
POST   /api/v1/admin/users/{id}/ban
POST   /api/v1/admin/users/{id}/unban
POST   /api/v1/admin/users/{id}/grant-role
GET    /api/v1/admin/users/{id}/timeline
```

### Payment Management

```
GET    /api/v1/admin/payments
GET    /api/v1/admin/payments/{id}
POST   /api/v1/admin/payments/{id}/manual-confirm  (superadmin)
POST   /api/v1/admin/payments/{id}/refund
```

### Referral Management

```
GET    /api/v1/admin/referrals
GET    /api/v1/admin/referrals/{id}
POST   /api/v1/admin/referrals/{id}/revoke
POST   /api/v1/admin/referrals/{id}/release-reward
```

### Analytics

```
GET    /api/v1/admin/analytics/overview
GET    /api/v1/admin/analytics/revenue
GET    /api/v1/admin/analytics/users
GET    /api/v1/admin/analytics/ai-usage
GET    /api/v1/admin/analytics/skills
GET    /api/v1/admin/analytics/referrals
```

### Audit Logs

```
GET    /api/v1/admin/audit-logs
GET    /api/v1/admin/audit-logs/{log_id}
```

Filters: `actor_id`, `action`, `resource_type`, `resource_id`, `from_date`, `to_date`, `limit`, `offset`.
Read access: developer, admin, superadmin. Audit rows are immutable — written by every admin mutation (skills, providers, users, payments, referrals) and never updated or deleted through the API.

---

## Common Admin Tasks

### Add New AI Provider

1. Navigate to `/admin/providers`
2. Click "Add Provider"
3. Fill form:
   - Name: "Anthropic Claude"
   - Slug: "claude"
   - Base URL: https://api.anthropic.com/v1
   - Model: claude-3-5-sonnet-20241022
   - API Key: sk-ant-... (will be encrypted)
   - Cost Input: 0.003 (per 1k tokens)
   - Cost Output: 0.015 (per 1k tokens)
   - Priority: 100 (higher = preferred)
4. Click "Test Connection"
5. If success, click "Save"

### Create New Skill

1. Navigate to `/admin/skills`
2. Click "Create Skill"
3. Fill form:
   - Name: "Python Tutor"
   - Slug: auto-generated from name
   - System Prompt: "You are an expert Python programming teacher..."
   - Use variable helper to insert `{{user_name}}`, etc.
   - Temperature: 0.5
   - Preferred Provider: Claude
   - Fallback: GPT-4
   - Is Public: Yes
   - Is Premium: No
4. Click "Test" to preview
5. Click "Save"

### Manually Adjust User Credits

1. Navigate to `/admin/users`
2. Search for user
3. Click user → "Adjust Credits"
4. Enter amount (+100 or -50)
5. Enter reason: "Customer support compensation"
6. Click "Confirm"
7. Action logged to audit_logs

### Investigate Suspicious Referral

1. Navigate to `/admin/referrals`
2. Filter: "Show suspicious only"
3. Click referral to view details
4. Review:
   - IP addresses of referrer and referred
   - Email patterns
   - Time between signup and payment
5. If fraud confirmed:
   - Click "Revoke Referral"
   - Enter reason
   - Confirm (reverses any paid rewards)

---

## Security Best Practices

1. **Strong Passwords**: Admins must use 16+ character passwords
2. **2FA** (future): Enable when available
3. **Least Privilege**: Grant minimum necessary role
4. **Session Timeout**: Admin sessions expire after 1 hour inactivity
5. **Audit Everything**: All sensitive actions logged
6. **IP Allowlisting** (production): Restrict admin panel to office IPs if possible

---

## Monitoring & Alerts

### Key Metrics to Watch

- Failed provider API calls (check API keys)
- High credit spend rate (potential abuse)
- Payment webhook failures
- Referral fraud patterns
- User complaints/support tickets

### Set Up Alerts

- Email alert if >50% provider calls fail
- Alert if single user spends >$100/hour
- Alert on webhook signature failures
- Daily revenue report

---

**End of Admin Guide**
