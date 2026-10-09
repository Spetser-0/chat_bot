# Spetser AI - Testing Guide

**Last Updated**: 2026-10-04  
**Status**: Phase 0 - Initial Version

---

## Overview

Testing is mandatory for all features. Every completed lesson must have passing tests before being marked complete.

---

## Test Structure

```
backend/tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Fast, isolated tests
│   ├── test_models.py
│   ├── test_services.py
│   ├── test_security.py
│   └── test_utils.py
└── integration/             # API endpoint tests
    ├── test_auth_routes.py
    ├── test_chat_routes.py
    ├── test_payment_routes.py
    └── test_admin_routes.py
```

---

## Running Tests

### Backend Tests

```bash
# Run all tests
cd backend
python -m pytest -q

# Run specific test file
python -m pytest tests/unit/test_skill_model.py -v

# Run with coverage
python -m pytest --cov=app --cov-report=html

# Run only unit tests
python -m pytest tests/unit/

# Run only integration tests
python -m pytest tests/integration/
```

### Frontend Tests

```bash
cd frontend

# Lint
npm run lint

# Build (catches TypeScript errors)
npm run build

# Unit tests (if configured)
npm test
```

---

## Test Fixtures

```python
# tests/conftest.py

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from httpx import AsyncClient

@pytest.fixture
async def db_session():
    """Provide clean database session for each test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSession(engine) as session:
        yield session
    
    await engine.dispose()

@pytest.fixture
async def test_user(db_session):
    """Create test user."""
    user = Student(
        id=uuid4(),
        email="test@example.com",
        referral_code="TEST-123456",
        credit_balance=100.0
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.fixture
async def api_client():
    """Provide test API client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
async def auth_client(api_client, test_user):
    """Provide authenticated API client."""
    token = create_access_token(user_id=str(test_user.id))
    api_client.headers["Authorization"] = f"Bearer {token}"
    yield api_client
```

---

## Test Examples

### Model Tests

```python
# tests/unit/test_skill_model.py

async def test_skill_requires_unique_slug(db_session):
    """Test skill slug must be unique."""
    skill1 = Skill(slug="math-tutor", name="Math", system_prompt="Test")
    skill2 = Skill(slug="math-tutor", name="Math2", system_prompt="Test2")
    
    db_session.add(skill1)
    await db_session.commit()
    
    db_session.add(skill2)
    with pytest.raises(IntegrityError):
        await db_session.commit()

async def test_skill_temperature_range(db_session):
    """Test temperature constraint."""
    skill = Skill(slug="test", temperature=3.0)  # Invalid: > 2.0
    db_session.add(skill)
    
    with pytest.raises(IntegrityError):
        await db_session.commit()
```

### Service Tests

```python
# tests/unit/test_credit_service.py

async def test_spend_credits(db_session, test_user):
    """Test credit spending."""
    initial = test_user.credit_balance
    
    await credit_service.spend_credits(
        user_id=test_user.id,
        amount=Decimal("10.50"),
        description="Test message"
    )
    
    await db_session.refresh(test_user)
    assert test_user.credit_balance == initial - Decimal("10.50")

async def test_cannot_spend_more_than_balance(db_session, test_user):
    """Test insufficient credits error."""
    test_user.credit_balance = Decimal("5.00")
    
    with pytest.raises(HTTPException) as exc:
        await credit_service.spend_credits(
            user_id=test_user.id,
            amount=Decimal("10.00")
        )
    
    assert exc.value.status_code == 402
    assert "insufficient" in exc.value.detail.lower()
```

### API Tests

```python
# tests/integration/test_chat_routes.py

async def test_chat_requires_auth(api_client):
    """Test unauthenticated request rejected."""
    response = await api_client.post("/api/v1/chat/completions", json={
        "message": "Hello"
    })
    assert response.status_code == 401

async def test_chat_with_skill(auth_client, db_session):
    """Test chat with skill selection."""
    # Create skill
    skill = Skill(slug="test-skill", system_prompt="You are a test assistant.")
    db_session.add(skill)
    await db_session.commit()
    
    response = await auth_client.post("/api/v1/chat/completions", json={
        "message": "Hello",
        "skill_slug": "test-skill",
        "stream": False
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["skill_used"] == "test-skill"
```

### Security Tests

```python
# tests/unit/test_security.py

def test_encrypt_decrypt_roundtrip():
    """Test encryption/decryption works."""
    plaintext = "sk-ant-secret-key-12345"
    encrypted = encrypt_secret(plaintext)
    decrypted = decrypt_secret(encrypted)
    
    assert decrypted == plaintext
    assert encrypted != plaintext

def test_webhook_signature_verification():
    """Test webhook signature validation."""
    payload = b'{"payment_id": "123"}'
    secret = "test_secret"
    
    # Valid signature
    valid_sig = hmac.new(secret.encode(), payload, hashlib.sha512).hexdigest()
    assert verify_webhook_signature(payload, valid_sig, secret) == True
    
    # Invalid signature
    assert verify_webhook_signature(payload, "wrong", secret) == False
```

---

## Definition of Done

A feature is NOT complete until:

- [ ] Code implemented
- [ ] Type hints added
- [ ] Docstrings added
- [ ] Unit tests written and passing
- [ ] Integration tests written and passing (if API changes)
- [ ] Security tests written (if security-sensitive)
- [ ] Full test suite still passes
- [ ] No decrease in code coverage
- [ ] Frontend lint passes (if frontend changed)
- [ ] Frontend build passes (if frontend changed)

---

## CI/CD Integration (Phase 12)

```yaml
# .github/workflows/test.yml

name: Tests

on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
        working-directory: ./backend
      - run: pytest --cov=app
        working-directory: ./backend
  
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '20'
      - run: npm install
        working-directory: ./frontend
      - run: npm run lint
        working-directory: ./frontend
      - run: npm run build
        working-directory: ./frontend
```

---

**End of Testing Guide**
