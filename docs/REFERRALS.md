# Spetser AI - Referral System Documentation

**Last Updated**: 2026-10-08  
**Status**: Phase 7 COMPLETE (Lessons 7.1–7.7) — see "Implementation Map" at the bottom for what actually shipped.

---

## Overview

The referral system allows users to invite friends and earn rewards when those friends make their first payment. This creates organic growth through word-of-mouth while rewarding early adopters.

---

## Concept Explanation

### Child Explanation

Imagine you have a special invitation card with your name on it. When you give this card to a friend and they join the game and buy coins, the game gives you a small gift as a "thank you" for bringing your friend. The more friends you invite, the more gifts you get!

### Technical Explanation

Each user gets a unique referral code (e.g., `SPETSER-AB12CD`). When a new user signs up using that code, the relationship is tracked in the database. After the new user makes their first successful payment, the referrer receives a credit reward. The system includes anti-fraud measures to prevent abuse.

---

## Database Schema

```sql
-- Extend students table
ALTER TABLE students ADD COLUMN referral_code VARCHAR(20) UNIQUE;
ALTER TABLE students ADD COLUMN referred_by_user_id UUID REFERENCES students(id);
CREATE INDEX idx_students_referral_code ON students(referral_code);
CREATE INDEX idx_students_referred_by ON students(referred_by_user_id);

-- Referral tracking
CREATE TABLE referrals (
    id UUID PRIMARY KEY,
    referrer_user_id UUID NOT NULL REFERENCES students(id),
    referred_user_id UUID NOT NULL UNIQUE REFERENCES students(id),  -- One referral per user
    referral_code VARCHAR(20) NOT NULL,
    
    -- Attribution context
    landing_page_url TEXT,
    ip_address INET,
    user_agent TEXT,
    
    -- Status tracking
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
        -- 'pending': User signed up but hasn't paid yet
        -- 'qualified': User made first payment, reward pending
        -- 'rewarded': Reward paid to referrer
        -- 'revoked': Admin revoked due to fraud
    qualified_at TIMESTAMP,
    rewarded_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT different_users CHECK (referrer_user_id != referred_user_id)
);

CREATE INDEX idx_referrals_referrer ON referrals(referrer_user_id);
CREATE INDEX idx_referrals_status ON referrals(status);

-- Reward transactions
CREATE TABLE reward_transactions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES students(id),
    referral_id UUID REFERENCES referrals(id),
    
    amount NUMERIC(10,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD_CREDIT',  -- 'USD_CREDIT', 'POINTS'
    type VARCHAR(50) NOT NULL,
        -- 'signup_bonus': New user signup reward
        -- 'subscription_commission': Recurring commission
        -- 'manual_bonus': Admin-granted reward
        
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
        -- 'pending': Reward created but not released
        -- 'payable': Ready to pay out
        -- 'paid': Credits added to user balance
        -- 'revoked': Fraud detected, reward cancelled
        
    scheduled_release_at TIMESTAMP,  -- Holding period end date
    reference_invoice_id UUID REFERENCES payment_invoices(id),
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT amount_positive CHECK (amount > 0)
);

CREATE INDEX idx_reward_txns_user ON reward_transactions(user_id);
CREATE INDEX idx_reward_txns_status ON reward_transactions(status);
CREATE INDEX idx_reward_txns_referral ON reward_transactions(referral_id);
CREATE INDEX idx_reward_txns_scheduled ON reward_transactions(scheduled_release_at);
```

---

## Referral Code Generation

### Format

`SPETSER-{6_CHARS}` where 6_CHARS is alphanumeric (uppercase)

Examples:
- `SPETSER-A1B2C3`
- `SPETSER-XYZ789`
- `SPETSER-HELLO1`

### Generation Logic

```python
# app/utils/referral_code.py

import secrets
import string

def generate_referral_code() -> str:
    """Generate unique referral code."""
    alphabet = string.ascii_uppercase + string.digits  # A-Z, 0-9
    suffix = ''.join(secrets.choice(alphabet) for _ in range(6))
    return f"SPETSER-{suffix}"

async def create_unique_referral_code(session) -> str:
    """Generate code and ensure uniqueness."""
    max_attempts = 10
    for _ in range(max_attempts):
        code = generate_referral_code()
        
        # Check if code already exists
        existing = await session.execute(
            select(Student).where(Student.referral_code == code)
        )
        if not existing.scalar_one_or_none():
            return code
    
    raise RuntimeError("Failed to generate unique referral code")
```

### Code Assignment

**On User Registration**:
```python
async def register_user(email: str, password: str, ref_code: str | None = None):
    # Create user with Supabase Auth
    user = await create_auth_user(email, password)
    
    # Generate referral code for new user
    new_user_code = await create_unique_referral_code(session)
    
    # Check if user was referred
    referrer_id = None
    if ref_code:
        referrer = await session.execute(
            select(Student).where(Student.referral_code == ref_code)
        )
        referrer = referrer.scalar_one_or_none()
        if referrer:
            referrer_id = referrer.id
    
    # Create student record
    student = Student(
        id=user.id,
        email=email,
        referral_code=new_user_code,
        referred_by_user_id=referrer_id
    )
    session.add(student)
    
    # If referred, create referrals entry
    if referrer_id:
        referral = Referral(
            referrer_user_id=referrer_id,
            referred_user_id=student.id,
            referral_code=ref_code,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            landing_page_url=request.headers.get("referer"),
            status="pending"
        )
        session.add(referral)
    
    await session.commit()
    return student
```

---

## Referral Links

### Link Formats

**Option 1: Subdirectory**
```
https://spetser.ai/r/SPETSER-A1B2C3
```

**Option 2: Query Parameter**
```
https://spetser.ai?ref=SPETSER-A1B2C3
https://spetser.ai/register?ref=SPETSER-A1B2C3
```

### Frontend Handling

```typescript
// src/pages/Register.tsx or App.tsx

useEffect(() => {
  // Option 1: Extract from path
  const pathMatch = window.location.pathname.match(/^\/r\/([A-Z0-9-]+)$/);
  if (pathMatch) {
    const refCode = pathMatch[1];
    localStorage.setItem('ref_code', refCode);
    // Redirect to register page
    navigate('/register');
  }
  
  // Option 2: Extract from query param
  const params = new URLSearchParams(window.location.search);
  const refCode = params.get('ref');
  if (refCode) {
    localStorage.setItem('ref_code', refCode);
  }
}, []);

// On registration submit
const handleRegister = async (email, password) => {
  const refCode = localStorage.getItem('ref_code');
  await api.post('/api/v1/auth/register', {
    email,
    password,
    referral_code: refCode  // Include in registration
  });
  localStorage.removeItem('ref_code');  // Clear after use
};
```

---

## Reward Triggers

### Trigger 1: First Payment

When a referred user makes their first payment:

```python
# In payment webhook handler, after crediting user

async def handle_payment_confirmed(invoice: PaymentInvoice):
    # Add credits to user
    await credit_service.add_credits(invoice.user_id, invoice.amount_usd * 100, ...)
    
    # Check if this is user's first payment
    payment_count = await session.scalar(
        select(func.count(PaymentInvoice.id))
        .where(
            PaymentInvoice.user_id == invoice.user_id,
            PaymentInvoice.status == "paid"
        )
    )
    
    if payment_count == 1:  # First payment
        # Check if user was referred
        referral = await session.execute(
            select(Referral).where(Referral.referred_user_id == invoice.user_id)
        )
        referral = referral.scalar_one_or_none()
        
        if referral:
            await process_referral_reward(referral, invoice)
```

### Reward Processing

```python
async def process_referral_reward(referral: Referral, invoice: PaymentInvoice):
    """Process referral reward after first payment."""
    
    # Calculate reward (e.g., 10% of payment amount)
    reward_amount = invoice.amount_usd * Decimal("0.10")
    
    # Minimum reward: $1, Maximum: $10 (adjust as needed)
    reward_amount = max(Decimal("1.00"), min(reward_amount, Decimal("10.00")))
    
    # Create reward transaction
    reward = RewardTransaction(
        user_id=referral.referrer_user_id,
        referral_id=referral.id,
        amount=reward_amount,
        type="signup_bonus",
        status="pending",
        scheduled_release_at=datetime.utcnow() + timedelta(days=7),  # 7-day hold
        reference_invoice_id=invoice.id
    )
    session.add(reward)
    
    # Update referral status
    referral.status = "qualified"
    referral.qualified_at = datetime.utcnow()
    
    await session.commit()
    
    logger.info("Referral reward created",
                referrer_id=referral.referrer_user_id,
                referred_id=referral.referred_user_id,
                amount=reward_amount,
                release_date=reward.scheduled_release_at)
```

---

## Reward Release (Cron Job)

### Scheduled Task

```python
# app/tasks/release_rewards.py

async def release_pending_rewards():
    """Release rewards that have passed holding period."""
    
    async with AsyncSession() as session:
        # Find rewards ready to release
        pending_rewards = await session.execute(
            select(RewardTransaction)
            .where(
                RewardTransaction.status == "pending",
                RewardTransaction.scheduled_release_at <= datetime.utcnow()
            )
        )
        
        for reward in pending_rewards.scalars():
            try:
                # Add credits to referrer
                await credit_service.add_credits(
                    user_id=reward.user_id,
                    amount=reward.amount * 100,  # Convert USD to credits
                    transaction_type="referral_reward",
                    reference_id=str(reward.id),
                    description=f"Referral reward: ${reward.amount}"
                )
                
                # Update reward status
                reward.status = "paid"
                
                # Update referral status
                referral = await session.get(Referral, reward.referral_id)
                referral.status = "rewarded"
                referral.rewarded_at = datetime.utcnow()
                
                await session.commit()
                
                logger.info("Reward released",
                           reward_id=reward.id,
                           user_id=reward.user_id,
                           amount=reward.amount)
                
            except Exception as e:
                logger.error("Failed to release reward",
                            reward_id=reward.id,
                            error=str(e))
                await session.rollback()
```

**Cron Schedule**: Run every hour
```bash
# crontab
0 * * * * /path/to/python /path/to/release_rewards.py
```

---

## Anti-Fraud Measures

### 1. Self-Referral Prevention

```python
if referrer_user_id == referred_user_id:
    raise ValueError("Cannot refer yourself")
```

### 2. Unique Referred User

Database constraint ensures one user can only be referred once:
```sql
ALTER TABLE referrals ADD CONSTRAINT unique_referred_user 
    UNIQUE (referred_user_id);
```

### 3. IP/Device Tracking

```python
# During registration
referral = Referral(
    referrer_user_id=referrer.id,
    referred_user_id=new_user.id,
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent")
)
```

### 4. Pattern Detection (Admin Review)

Flag suspicious referrals:
- Multiple referrals from same IP within 24 hours
- Multiple referrals with similar email patterns (e.g., user1@, user2@, user3@)
- Immediate payment after registration (< 5 minutes)
- Disposable email domains

```python
async def detect_suspicious_patterns(referral: Referral) -> list[str]:
    """Return list of fraud indicators."""
    warnings = []
    
    # Check for multiple referrals from same IP
    recent_referrals = await session.scalar(
        select(func.count(Referral.id))
        .where(
            Referral.referrer_user_id == referral.referrer_user_id,
            Referral.ip_address == referral.ip_address,
            Referral.created_at >= datetime.utcnow() - timedelta(hours=24)
        )
    )
    if recent_referrals > 3:
        warnings.append("Multiple referrals from same IP")
    
    # Check for disposable email
    referred_user = await session.get(Student, referral.referred_user_id)
    email_domain = referred_user.email.split("@")[1]
    if email_domain in DISPOSABLE_DOMAINS:
        warnings.append("Disposable email detected")
    
    # Check payment timing
    if referral.qualified_at:
        time_to_payment = (referral.qualified_at - referral.created_at).total_seconds()
        if time_to_payment < 300:  # Less than 5 minutes
            warnings.append("Suspiciously fast payment")
    
    return warnings
```

### 5. Holding Period

7-day delay before reward payout allows time to investigate:
```python
scheduled_release_at = datetime.utcnow() + timedelta(days=7)
```

### 6. Admin Revocation

```python
@router.post("/admin/referrals/{referral_id}/revoke")
async def revoke_referral(
    referral_id: UUID,
    reason: str,
    current_user: Student = Depends(require_admin)
):
    """Revoke a referral and its rewards."""
    referral = await session.get(Referral, referral_id)
    
    # Mark referral as revoked
    referral.status = "revoked"
    
    # Revoke associated rewards
    rewards = await session.execute(
        select(RewardTransaction).where(RewardTransaction.referral_id == referral_id)
    )
    for reward in rewards.scalars():
        if reward.status == "paid":
            # Deduct credits from user
            await credit_service.add_credits(
                user_id=reward.user_id,
                amount=-(reward.amount * 100),
                transaction_type="admin_adjustment",
                description=f"Revoked fraudulent referral reward: {reason}"
            )
        reward.status = "revoked"
    
    # Audit log
    audit = AuditLog(
        actor_user_id=current_user.id,
        action="referral.revoked",
        entity_type="Referral",
        entity_id=str(referral_id),
        after_json={"reason": reason}
    )
    session.add(audit)
    
    await session.commit()
```

---

## API Endpoints

### User Endpoints

#### GET /api/v1/referrals/me

Get user's referral info.

**Response**:
```json
{
  "referral_code": "SPETSER-A1B2C3",
  "referral_link": "https://spetser.ai/r/SPETSER-A1B2C3",
  "total_referrals": 5,
  "qualified_referrals": 3,
  "pending_referrals": 2,
  "total_earned": 30.00,
  "pending_rewards": 15.00
}
```

#### GET /api/v1/referrals/stats

Get detailed referral statistics.

**Response**:
```json
{
  "referrals": [
    {
      "referred_user_email": "fri***@example.com",  // Partially masked
      "status": "rewarded",
      "signed_up_at": "2026-09-15T10:00:00Z",
      "qualified_at": "2026-09-16T14:30:00Z",
      "reward_amount": 10.00
    }
  ],
  "rewards": [
    {
      "amount": 10.00,
      "status": "paid",
      "created_at": "2026-09-16T14:30:00Z"
    },
    {
      "amount": 5.00,
      "status": "pending",
      "scheduled_release_at": "2026-10-10T00:00:00Z"
    }
  ]
}
```

#### GET /api/v1/referrals/link

Get shareable referral link (with social sharing buttons).

**Response**:
```json
{
  "referral_code": "SPETSER-A1B2C3",
  "link": "https://spetser.ai/r/SPETSER-A1B2C3",
  "qr_code_url": "https://api.qrserver.com/v1/create-qr-code/?data=...",
  "share_text": "Join Spetser AI, the Arabic-first educational AI platform! Use my link: https://spetser.ai/r/SPETSER-A1B2C3"
}
```

### Public Endpoint

#### GET /api/v1/referrals/validate/{code}

Validate referral code (frontend uses this before registration).

**Response**:
```json
{
  "valid": true,
  "referrer_name": "Ahmed"  // First name or email prefix
}
```

Or:
```json
{
  "valid": false,
  "error": "Invalid or expired referral code"
}
```

### Admin Endpoints

#### GET /api/v1/admin/referrals

List all referrals with filters.

**Query Params**:
- `status`: Filter by status
- `suspicious`: Show only flagged referrals
- `user_id`: Filter by referrer

#### POST /api/v1/admin/referrals/{id}/revoke

Revoke referral and rewards.

#### GET /api/v1/admin/analytics/referrals

Referral program analytics.

---

## Frontend Components

### Referral Dashboard Page

```typescript
// src/pages/ReferralDashboard.tsx

export function ReferralDashboard() {
  const { data: stats } = useQuery(['referral-stats'], fetchReferralStats);
  
  return (
    <div>
      <h1>Invite Friends & Earn Credits</h1>
      
      <ReferralLinkCard code={stats.referral_code} link={stats.referral_link} />
      
      <StatsGrid>
        <StatCard label="Total Referrals" value={stats.total_referrals} />
        <StatCard label="Qualified" value={stats.qualified_referrals} />
        <StatCard label="Total Earned" value={`$${stats.total_earned}`} />
        <StatCard label="Pending Rewards" value={`$${stats.pending_rewards}`} />
      </StatsGrid>
      
      <ReferralsList referrals={stats.referrals} />
      <RewardHistory rewards={stats.rewards} />
    </div>
  );
}
```

### Referral Link Component

```typescript
// src/components/referral/ReferralLink.tsx

export function ReferralLink({ code, link }: Props) {
  const [copied, setCopied] = useState(false);
  
  const handleCopy = () => {
    navigator.clipboard.writeText(link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  
  return (
    <Card>
      <h3>Your Referral Link</h3>
      <div className="link-display">
        <code>{link}</code>
        <button onClick={handleCopy}>
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      
      <div className="share-buttons">
        <button onClick={() => shareOnWhatsApp(link)}>WhatsApp</button>
        <button onClick={() => shareOnTwitter(link)}>Twitter</button>
        <button onClick={() => shareOnFacebook(link)}>Facebook</button>
      </div>
      
      <QRCode value={link} size={200} />
    </Card>
  );
}
```

---

## Reward Configuration

### Adjustable Settings

```python
# app/core/config.py

class Settings(BaseSettings):
    # Referral rewards
    REFERRAL_REWARD_PERCENTAGE: Decimal = Decimal("0.10")  # 10% of payment
    REFERRAL_REWARD_MIN: Decimal = Decimal("1.00")  # Minimum $1
    REFERRAL_REWARD_MAX: Decimal = Decimal("10.00")  # Maximum $10
    REFERRAL_HOLDING_DAYS: int = 7  # Days before reward release
    
    # Anti-fraud
    REFERRAL_MAX_PER_IP_PER_DAY: int = 3
    REFERRAL_SUSPICIOUS_PAYMENT_SECONDS: int = 300  # Flag if payment < 5 min after signup
```

---

## Testing

```python
async def test_referral_code_generation():
    """Test referral code format."""
    code = generate_referral_code()
    assert code.startswith("SPETSER-")
    assert len(code) == 13  # "SPETSER-" + 6 chars
    assert code[8:].isalnum()

async def test_self_referral_prevented():
    """Test user cannot refer themselves."""
    user = await create_user("test@example.com")
    with pytest.raises(ValueError, match="Cannot refer yourself"):
        await create_referral(user.id, user.id, user.referral_code)

async def test_referral_reward_triggered():
    """Test reward created after first payment."""
    referrer = await create_user("referrer@example.com")
    referred = await create_user("referred@example.com", ref_code=referrer.referral_code)
    
    # Simulate payment
    invoice = await create_payment(referred.id, amount_usd=10.00)
    await mark_payment_paid(invoice.id)
    
    # Check reward created
    reward = await get_reward_for_referral(referrer.id, referred.id)
    assert reward is not None
    assert reward.amount == 1.00  # 10% of $10, min $1
    assert reward.status == "pending"

async def test_duplicate_referred_user():
    """Test user can only be referred once."""
    referrer1 = await create_user("ref1@example.com")
    referrer2 = await create_user("ref2@example.com")
    referred = await create_user("referred@example.com", ref_code=referrer1.referral_code)
    
    # Try to create second referral
    with pytest.raises(IntegrityError):
        await create_referral(referrer2.id, referred.id, referrer2.referral_code)
```

---

## Future Enhancements

- **Multi-Tier Rewards**: Reward referrer when referred user refers others
- **Leaderboard**: Show top referrers
- **Referral Contests**: Limited-time bonus rewards
- **Custom Referral Codes**: Let users choose vanity codes (e.g., "SPETSER-AHMED")
- **Referral Tiers**: Higher rewards for power users
- **Affiliate Program**: Public influencer/educator program with higher commissions
- **Referral Analytics**: Track conversion rates, popular channels

---

## Implementation Map (Phase 7, as built)

What actually shipped, and where. Deviations from the Phase-0 design above
are intentional and noted.

### Code

| Concern | Location |
|---|---|
| Referral codes (`SPETSER-XXXXXX`, uniqueness, validation) | `backend/app/services/referral_service.py` — `ReferralService` |
| Anti-fraud checks (Lesson 7.4) | `ReferralService._check_fraud()` — self-referral, duplicate referral, disposable-email blocklist (~25 domains), device-fingerprint collision, per-referrer IP rate limit (5/24h, `MAX_REFERRALS_PER_IP_PER_DAY`) |
| Referral capture at registration (Lesson 7.3) | `backend/app/api/v1/routes/auth.py` — `register(..., ref=...)` |
| Reward qualification + holding (Lesson 7.5) | `ReferralService.on_invoice_paid()` — called from `PaymentService._handle_paid` |
| Reward release (Lesson 7.5) | `ReferralService.release_due_rewards()` / `_release_one()`; admin `force_release_referral()` |
| User endpoints (Lesson 7.6) | `backend/app/api/v1/routes/referrals.py` — `/me`, `/stats`, `/link`, `/{code}/validate` |
| Admin endpoints (Lesson 7.6) | `backend/app/api/v1/routes/admin/referrals.py` — list, `/{id}/revoke`, `/{id}/release`, `/release-due` |
| Migration (`device_fingerprint`) | `backend/alembic/versions/20261008_0303_phase7_referral_device_fingerprint.py` |
| Settings | `referral_reward_percent` (default 10%), `referral_reward_holding_days` (default 7) in `backend/app/core/config.py` |

### Reward lifecycle

1. `POST /auth/register?ref=SPETSER-XXX` → `Referral` row `PENDING`
   (landing page, IP, user-agent, device fingerprint recorded). Fraud
   triggers **drop the attribution but never block registration**
   (fail-open on the referral, not on the account).
2. Referred user's invoice turns `PAID` → `on_invoice_paid()`:
   referral → `QUALIFIED`, `RewardTransaction` created `PENDING` with
   `scheduled_release_at = now + holding_days`, amount = `percent%` of the
   paid USD (one reward per referral, keyed on `referral_id`).
3. `release_due_rewards()` (admin `POST /admin/referrals/release-due`,
   cron-wired in Phase 12): credits referrer via `CreditService`
   (`entry_type=referral_reward`, `idempotency_key=ref-reward-{id}`),
   reward → `PAID`, referral → `REWARDED`.
4. Admin `revoke`: referral → `REVOKED`, unpaid rewards voided; already
   released rewards are not clawed back (ops adjustment, future).

### Deviations from the design doc above

- Fraud failures fail **open**: the account is always created; only the
  referral attribution is dropped. Blocking signup would hurt growth more
  than fraud costs (rewards only flow after a real payment anyway).
- IP rate limit is **per referrer** (5/24h), not global — a global limit
  would punish shared networks (schools, cafés, NAT).
- Reward release endpoint exists now; the cron/worker wiring lands in
  Phase 12 (Docker & deployment).
- Webhook dedupe + credit idempotency (`pay-credit-{ext}`) already
  guarantee a repeated payment webhook cannot double-create a reward.

### Tests (57 referral tests + 2 acceptance)

- `backend/tests/unit/test_referral_service.py` — codes, stats, `_check_fraud` matrix
- `backend/tests/integration/test_referral_endpoints.py` — validate/link/stats/capture/anti-fraud
- `backend/tests/integration/test_referral_rewards.py` — qualification, holding, release, revoke
- `backend/tests/integration/test_admin_referrals.py` — RBAC + admin mutations + `/me`
- `backend/tests/integration/test_phase7_acceptance.py` — end-to-end journey + self-referral cannot earn

---

**End of Referral System Documentation**
