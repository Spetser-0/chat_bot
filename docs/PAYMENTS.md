# Spetser AI - Payment System Documentation

**Last Updated**: 2026-10-07  
**Status**: ✅ **Phase 6 COMPLETE** - Payment Gateway Fully Implemented

---

---

## Overview

Spetser AI uses cryptocurrency payments to allow users worldwide, especially in Libya and the Arab world, to purchase credits for AI services. The system integrates with third-party crypto payment processors (NOWPayments or Cryptomus) rather than handling private keys directly.

---

## Concept Explanation

### Child Explanation

Imagine you have a piggy bank app. When you want to add coins to your piggy bank, you scan a special barcode with your phone and send digital money (like Bitcoin). The system watches for your payment, and when it arrives, it automatically adds coins to your piggy bank. You can then use those coins to ask the AI robot questions.

### Technical Explanation

The payment flow:
1. User requests to buy credits (e.g., $10 USD → 1,000 credits)
2. Backend calls payment provider API to create an invoice
3. Provider returns a crypto address, QR code, and payment amount
4. User sends cryptocurrency to the address
5. Provider monitors blockchain and sends webhook when payment confirmed
6. Backend verifies webhook, adds credits to user's balance
7. If user was referred, system triggers referral reward

---

## Payment Providers

### Option 1: NOWPayments

**Website**: https://nowpayments.io  
**Supported Coins**: 300+ cryptocurrencies including BTC, ETH, USDT, USDC, LTC, etc.  
**Fees**: ~0.5-1% per transaction  
**Settlement**: Crypto or fiat

**Pros**:
- Large selection of coins
- Well-documented API
- Good webhook reliability

**Cons**:
- Slightly higher fees than some competitors

### Option 2: Cryptomus

**Website**: https://cryptomus.com  
**Supported Coins**: 40+ major cryptocurrencies  
**Fees**: 0.5% per transaction  
**Settlement**: Crypto only

**Pros**:
- Lower fees
- Clean API
- Fast integration

**Cons**:
- Fewer supported coins

### Recommendation

Start with **NOWPayments** for wider coin support. Can add Cryptomus as backup later.

---

## Database Schema

```sql
CREATE TABLE payment_invoices (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES students(id),
    
    -- Provider info
    provider VARCHAR(50) NOT NULL,  -- 'nowpayments', 'cryptomus', 'manual'
    external_invoice_id VARCHAR(255) UNIQUE,  -- Provider's payment ID
    
    -- Amount details
    amount_usd NUMERIC(10,2) NOT NULL,
    currency VARCHAR(10) NOT NULL,  -- 'BTC', 'ETH', 'USDT', etc.
    crypto_amount NUMERIC(20,8),  -- Amount in crypto (e.g., 0.00025 BTC)
    
    -- Payment details
    crypto_address TEXT,  -- Address to send payment to
    payment_url TEXT,  -- Deep link for mobile wallets
    qr_code_url TEXT,  -- QR code image URL
    
    -- Status tracking
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
        -- 'pending', 'confirming', 'paid', 'expired', 'failed', 'refunded'
    expires_at TIMESTAMP,  -- Payment window expiration
    paid_at TIMESTAMP,
    
    -- Audit
    webhook_payload JSONB,  -- Raw webhook data
    idempotency_key VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT amount_positive CHECK (amount_usd > 0),
    CONSTRAINT crypto_amount_positive CHECK (crypto_amount IS NULL OR crypto_amount > 0)
);

CREATE INDEX idx_payment_invoices_user_id ON payment_invoices(user_id);
CREATE INDEX idx_payment_invoices_status ON payment_invoices(status);
CREATE INDEX idx_payment_invoices_external_id ON payment_invoices(external_invoice_id);

CREATE TABLE webhook_events (
    id UUID PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,  -- 'nowpayments', 'cryptomus'
    event_type VARCHAR(100) NOT NULL,  -- 'payment.confirmed', 'payment.expired', etc.
    external_id VARCHAR(255) NOT NULL,  -- Provider's event/payment ID
    payload JSONB NOT NULL,  -- Full webhook body
    signature VARCHAR(500),  -- Webhook signature
    processed BOOLEAN DEFAULT false,
    processed_at TIMESTAMP,
    error TEXT,  -- Error message if processing failed
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(provider, external_id)  -- Prevent duplicate webhook processing
);

CREATE INDEX idx_webhook_events_processed ON webhook_events(processed);
CREATE INDEX idx_webhook_events_provider_external ON webhook_events(provider, external_id);
```

---

## API Integration

### NOWPayments API Example

#### Create Payment

```python
# app/services/payment_service.py

import httpx
from app.core.config import settings

async def create_nowpayments_invoice(
    amount_usd: Decimal,
    user_id: UUID,
    idempotency_key: str,
    currency: str = "btc"
) -> dict:
    """Create payment invoice via NOWPayments API."""
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.nowpayments.io/v1/payment",
            headers={
                "x-api-key": settings.CRYPTO_PAYMENT_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "price_amount": float(amount_usd),
                "price_currency": "usd",
                "pay_currency": currency,
                "ipn_callback_url": f"{settings.BACKEND_URL}/api/v1/payments/webhook",
                "order_id": idempotency_key,
                "order_description": f"Spetser AI Credits - ${amount_usd}",
            },
            timeout=30.0,
        )
        
        response.raise_for_status()
        data = response.json()
        
        return {
            "external_invoice_id": data["payment_id"],
            "crypto_address": data["pay_address"],
            "crypto_amount": Decimal(data["pay_amount"]),
            "payment_url": data["invoice_url"],
            "qr_code_url": f"https://api.qrserver.com/v1/create-qr-code/?data={data['pay_address']}&size=300x300",
            "expires_at": datetime.utcnow() + timedelta(hours=1),
        }
```

#### Verify Webhook Signature

```python
import hmac
import hashlib

def verify_nowpayments_signature(payload: bytes, signature: str) -> bool:
    """Verify NOWPayments IPN signature."""
    expected = hmac.new(
        settings.CRYPTO_PAYMENT_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha512
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)
```

---

## API Endpoints

### User Endpoints

#### POST /api/v1/payments/create-invoice

Create a new payment invoice.

**Request**:
```json
{
  "amount_usd": 10.00,
  "currency": "btc",  // Optional, defaults to 'btc'
  "idempotency_key": "uuid-v4-string"  // Client-generated
}
```

**Response** (201 Created):
```json
{
  "invoice_id": "550e8400-e29b-41d4-a716-446655440000",
  "payment_address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
  "crypto_amount": "0.00025",
  "currency": "BTC",
  "qr_code_url": "https://...",
  "payment_url": "bitcoin:1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa?amount=0.00025",
  "expires_at": "2026-10-04T17:30:00Z",
  "status": "pending"
}
```

**Errors**:
- `400`: Invalid amount or currency
- `401`: Unauthorized
- `409`: Duplicate idempotency_key

#### GET /api/v1/payments/invoices/{invoice_id}

Get invoice status.

**Response**:
```json
{
  "invoice_id": "...",
  "amount_usd": 10.00,
  "currency": "BTC",
  "crypto_amount": "0.00025",
  "status": "confirming",  // or 'pending', 'paid', 'expired', 'failed'
  "created_at": "2026-10-04T16:00:00Z",
  "paid_at": null,
  "expires_at": "2026-10-04T17:00:00Z"
}
```

#### GET /api/v1/payments/invoices

List user's payment history.

**Query Params**:
- `status`: Filter by status
- `limit`: Default 20, max 100
- `offset`: Pagination

**Response**:
```json
{
  "invoices": [
    {
      "invoice_id": "...",
      "amount_usd": 10.00,
      "status": "paid",
      "created_at": "2026-10-04T15:00:00Z",
      "paid_at": "2026-10-04T15:10:00Z"
    }
  ],
  "total": 5,
  "limit": 20,
  "offset": 0
}
```

### Webhook Endpoint

#### POST /api/v1/payments/webhook

Receive payment status updates from provider.

**Headers**:
- `x-nowpayments-sig`: HMAC signature (NOWPayments)
- `sign`: HMAC signature (Cryptomus)

**Request Body** (NOWPayments example):
```json
{
  "payment_id": "12345678",
  "payment_status": "finished",
  "pay_address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
  "price_amount": 10.00,
  "price_currency": "usd",
  "pay_amount": 0.00025,
  "pay_currency": "btc",
  "order_id": "uuid-idempotency-key",
  "order_description": "Spetser AI Credits - $10",
  "purchase_id": "12345678",
  "outcome_amount": 0.00025,
  "outcome_currency": "btc"
}
```

**Response**:
- `200 OK`: Webhook processed (or duplicate)
- `401 Unauthorized`: Invalid signature
- `500 Internal Server Error`: Processing failed (provider will retry)

---

## Payment Flow

### Step-by-Step Process

```
1. User clicks "Buy Credits" → selects $10 package

2. Frontend generates UUID for idempotency_key

3. Frontend: POST /api/v1/payments/create-invoice
   {
     "amount_usd": 10,
     "currency": "btc",
     "idempotency_key": "a1b2c3d4-..."
   }

4. Backend:
   - Validate user authenticated
   - Check idempotency_key not already used
   - Call NOWPayments API
   - Insert payment_invoices row (status: pending)
   - Return payment details

5. Frontend displays:
   - QR code
   - Payment address (with copy button)
   - Amount in crypto
   - "Open in Wallet" button (deep link)
   - Countdown timer (expires in 1 hour)

6. User sends Bitcoin to address using their wallet

7. Blockchain confirms transaction (0-60 minutes depending on coin)

8. NOWPayments detects payment:
   - First webhook: { payment_status: "confirming" }
   - Blockchain confirmations: 0/1, 1/1, 2/1, ...
   - Final webhook: { payment_status: "finished" }

9. Backend receives webhook:
   - Verify signature
   - Check webhook_events for duplicate (provider + external_id)
   - If duplicate: return 200 (already processed)
   - Insert webhook_events row
   - Find payment_invoice by external_invoice_id
   - Update invoice status
   - If status = "finished":
     * Calculate credits (amount_usd * 100 = credits)
     * Call credit_service.add_credits()
     * Create credit_transaction (type: topup)
     * Check if user has referrer → trigger referral reward
   - Mark webhook processed

10. Frontend polls GET /api/v1/payments/invoices/{id} every 10 seconds
    - When status changes to "paid":
      * Show success message
      * Update credit balance
      * Redirect to chat

11. If 1 hour passes with no payment:
    - NOWPayments sends webhook: { payment_status: "expired" }
    - Backend updates status to "expired"
    - Frontend shows "Payment expired" message
```

---

## Credit Packages

Suggested pricing (adjustable):

| Package | USD | Credits | Bonus | Total |
|---------|-----|---------|-------|-------|
| Starter | $5  | 500     | 0     | 500   |
| Basic   | $10 | 1,000   | 100   | 1,100 |
| Pro     | $25 | 2,500   | 500   | 3,000 |
| Ultra   | $50 | 5,000   | 1,500 | 6,500 |

**Credit Usage Examples**:
- Simple question (100 tokens): ~0.01 credits
- Math problem with explanation (500 tokens): ~0.05 credits
- Essay review (2,000 tokens): ~0.20 credits
- Code review (5,000 tokens): ~0.50 credits

**Pricing Formula**:
```
credits = amount_usd * 100 * (1 + bonus_percentage)
```

---

## Payment Security

### 1. Webhook Signature Verification

**Always verify** before processing:
```python
signature_header = request.headers.get("x-nowpayments-sig")
if not verify_nowpayments_signature(await request.body(), signature_header):
    raise HTTPException(status_code=401)
```

### 2. Idempotency

**Prevent double-crediting**:
```python
# Check if webhook already processed
existing = await session.execute(
    select(WebhookEvent).where(
        WebhookEvent.provider == "nowpayments",
        WebhookEvent.external_id == payment_id
    )
)
if existing.scalar_one_or_none():
    logger.info("Duplicate webhook ignored", payment_id=payment_id)
    return {"status": "ok"}  # Return 200 so provider stops retrying
```

### 3. Amount Validation

**Check paid amount**:
```python
paid = Decimal(webhook_data["outcome_amount"])
expected = invoice.crypto_amount
tolerance = Decimal("0.0001")  # Small tolerance for fees

if paid < (expected - tolerance):
    logger.error("Underpayment", expected=expected, paid=paid)
    # Mark for manual review, don't credit user
    invoice.status = "failed"
    return
```

### 4. Status Transition Validation

**Only allow valid transitions**:
```python
VALID_TRANSITIONS = {
    "pending": ["confirming", "expired", "failed"],
    "confirming": ["paid", "failed"],
    "paid": [],  # Terminal state
    "expired": [],  # Terminal state
    "failed": ["paid"],  # Allow manual recovery
}

if new_status not in VALID_TRANSITIONS[invoice.status]:
    logger.warning("Invalid status transition", 
                   from_status=invoice.status, 
                   to_status=new_status)
    raise ValueError(f"Cannot transition from {invoice.status} to {new_status}")
```

### 5. Rate Limiting

**Webhook endpoint**:
```python
@limiter.limit("1000/hour")  # High limit for legitimate webhooks
@router.post("/webhook")
async def payment_webhook(...):
    pass
```

### 6. IP Allowlisting (if provider supports)

```python
NOWPAYMENTS_IPS = [
    "209.250.228.68",  # Example - check NOWPayments docs
    "104.17.19.97",
]

if request.client.host not in NOWPAYMENTS_IPS:
    logger.warning("Webhook from unknown IP", ip=request.client.host)
    raise HTTPException(status_code=403)
```

---

## Error Handling

### Payment Creation Errors

- **Provider API down**: Show error, allow retry
- **Invalid currency**: Show supported currencies
- **Minimum amount**: Enforce $5 minimum (to cover transaction fees)

### Webhook Processing Errors

- **Invalid signature**: Log, return 401
- **Duplicate webhook**: Return 200 (idempotency)
- **Unknown invoice**: Log, return 404
- **Processing exception**: Log, return 500 (provider will retry)

### Refunds (Manual Process)

1. User requests refund
2. Admin reviews in admin panel
3. If approved:
   - Mark invoice status = "refunded"
   - Deduct credits from user (if not spent)
   - Process manual crypto refund via provider dashboard
   - Log to audit_logs

---

## Admin Endpoints (Phase 8)

```python
# GET /api/v1/admin/payments
# List all payments with filters (status, user, date range)

# GET /api/v1/admin/payments/{invoice_id}
# View full invoice details including webhook payload

# POST /api/v1/admin/payments/{invoice_id}/manual-confirm
# Manually mark payment as paid (requires superadmin, logs to audit)

# POST /api/v1/admin/payments/{invoice_id}/refund
# Mark as refunded (manual crypto refund via provider)

# GET /api/v1/admin/analytics/revenue
# Revenue charts and stats
```

---

## Testing

### Unit Tests

```python
async def test_create_invoice():
    """Test invoice creation."""
    invoice = await create_invoice(user_id, 10.00, "test-key-1")
    assert invoice.status == "pending"
    assert invoice.amount_usd == 10.00

async def test_duplicate_idempotency_key():
    """Test duplicate idempotency key rejected."""
    await create_invoice(user_id, 10.00, "test-key-2")
    with pytest.raises(HTTPException) as exc:
        await create_invoice(user_id, 10.00, "test-key-2")
    assert exc.value.status_code == 409

async def test_webhook_signature_verification():
    """Test webhook signature is verified."""
    payload = b'{"payment_id": "123"}'
    secret = "test_secret"
    
    # Generate valid signature
    valid_sig = hmac.new(secret.encode(), payload, hashlib.sha512).hexdigest()
    assert verify_nowpayments_signature(payload, valid_sig) == True
    
    # Invalid signature
    assert verify_nowpayments_signature(payload, "wrong_sig") == False

async def test_webhook_idempotency():
    """Test duplicate webhook ignored."""
    webhook_data = {"payment_id": "123", "payment_status": "finished"}
    
    # First webhook processes
    await process_webhook(webhook_data)
    invoice = await get_invoice_by_external_id("123")
    assert invoice.status == "paid"
    
    # Second webhook ignored
    await process_webhook(webhook_data)
    # Should still be paid, credits not doubled
```

### Integration Tests

Use provider sandbox/testnet:
- Create test invoice
- Use provider's test webhook simulator
- Verify credits added correctly

---

## Monitoring

### Key Metrics

- **Payment success rate**: % of invoices that reach "paid" status
- **Average time to payment**: From creation to confirmation
- **Expiration rate**: % of invoices that expire unpaid
- **Failed payments**: Track failure reasons
- **Revenue**: Daily/weekly/monthly totals in USD

### Alerts

- Webhook signature verification failures (potential attack)
- High expiration rate (UX issue or pricing problem)
- Processing errors (check logs immediately)
- Unusual payment patterns (fraud detection)

---

## Future Enhancements

- **Subscription Plans**: Recurring payments (monthly premium)
- **Fiat Payments**: Credit card via Stripe (if allowed in target market)
- **Gift Cards**: Prepaid codes for offline sale
- **Enterprise Invoicing**: Custom payment terms for universities
- **Multi-Currency Display**: Show amounts in user's local currency
- **Partial Payments**: Accept and credit underpayments proportionally

---

## Implementation Status (Phase 6)

### ✅ Completed Lessons

| Lesson | Description | Status |
|--------|-------------|--------|
| 6.1 | Payment provider abstraction (`PaymentGateway` protocol) | ✅ Done |
| 6.2 | MockCryptoProvider adapter (offline testing) | ✅ Done |
| 6.3 | Invoice creation endpoint (`POST /api/v1/payments/create-invoice`) | ✅ Done |
| 6.4 | Invoice storage & status tracking | ✅ Done (folded into 6.3) |
| 6.5 | Webhook endpoint (`POST /api/v1/payments/webhook`) | ✅ Done |
| 6.6 | Handle paid event (credit user, idempotent) | ✅ Done |
| 6.7 | Handle expired/failed events | ✅ Done |
| 6.8 | Amount validation (underpay/overpay policy) | ✅ Done |
| 6.9 | Idempotency (dedupe by provider+external_id) | ✅ Done |
| 6.10 | Tests & acceptance criteria | ✅ Done |

### Test Coverage

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `tests/unit/test_payment_service.py` | 12 | Unit: gateway, lifecycle, paid/closed events |
| `tests/integration/test_payment_endpoints.py` | 7 | Integration: create invoice, status, auth |
| `tests/integration/test_payment_webhook.py` | 5 | Integration: webhook verify, paid/expired/failed |
| `tests/integration/test_phase6_acceptance.py` | 6 | Acceptance: full flow, replay, underpay/overpay |

**Total**: 30 tests passing ✅

### Key Implementation Files

| File | Purpose |
|------|---------|
| `app/services/payment_service.py` | Gateway protocol, MockCryptoProvider, PaymentService lifecycle |
| `app/api/v1/routes/payments.py` | Invoice creation & status endpoints |
| `app/api/v1/routes/webhooks.py` | Webhook ingress with signature verification |
| `app/schemas/payment.py` | Request/response schemas |
| `tests/unit/test_payment_service.py` | Unit tests |
| `tests/integration/test_payment_*.py` | Integration & acceptance tests |

---

**End of Payment System Documentation**
