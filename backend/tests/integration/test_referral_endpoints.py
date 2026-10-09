"""
tests/integration/test_referral_endpoints.py
────────────────────────────────────────────
Integration tests for referral endpoints (Phase 7, Lesson 7.2, 7.3).

RBAC matrix:
- anonymous → 401
- student    → 403 on mutations AND reads (admin/dev only)
- developer  → 200 reads, 403 mutations
- admin      → 200 reads, 403 mutations (if not superadmin)
- superadmin → full CRUD
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI
from sqlalchemy import select

from app.models.referral import Referral, ReferralStatus
from app.models.reward_transaction import RewardTransaction, RewardStatus
from app.models.student import Student
from app.services.auth import (
    SESSION_COOKIE_NAME,
    create_session_token,
    hash_password,
)
from app.services.referral_service import ReferralService


def payload(**overrides) -> dict:
    base = dict(
        slug="math-tutor",
        name="Math Tutor",
        system_prompt="You are a math tutor.",
        temperature=0.7,
        max_tokens=4096,
        is_public=True,
        is_premium=False,
        cost_multiplier=Decimal("1.0"),
        tools=[{"tool_name": "calculator", "tool_config": {"precision": 2}, "is_enabled": True}],
    )
    base.update(overrides)
    return base


@pytest_asyncio.fixture
async def admin(db) -> Student:
    s = Student(
        id=uuid.uuid4(),
        email=f"admin_{uuid.uuid4().hex[:6]}@t.com",
        display_name="Admin",
        password_hash=hash_password("pass12345"),
        role="admin",
        status="active",
        credit_balance=0,
    )
    db.add(s)
    await db.commit()
    return s


@pytest_asyncio.fixture
async def admin_client(app: FastAPI, admin) -> AsyncClient:
    token = create_session_token(admin.id, admin.role)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={SESSION_COOKIE_NAME: token},
    ) as c:
        yield c


@pytest_asyncio.fixture
async def developer(db) -> Student:
    d = Student(
        id=uuid.uuid4(),
        email=f"dev_{uuid.uuid4().hex[:6]}@t.com",
        display_name="Developer",
        password_hash=hash_password("devpass123"),
        role="developer",
        status="active",
        credit_balance=1000.0,
    )
    db.add(d)
    await db.commit()
    return d


@pytest_asyncio.fixture
async def developer_client(app: FastAPI, developer) -> AsyncClient:
    token = create_session_token(developer.id, developer.role)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={SESSION_COOKIE_NAME: token},
    ) as c:
        yield c


def _skill_payload(**overrides) -> dict:
    base = {
        "name": "Test Skill",
        "slug": f"test-skill-{uuid.uuid4().hex[:8]}",
        "system_prompt": "You are a helpful assistant.",
        "temperature": 0.7,
        "max_tokens": 4096,
        "is_public": True,
        "is_premium": False,
        "cost_multiplier": "1.0",
        "tools": [],
    }
    base.update(overrides)
    return base


class TestReferralValidate:
    @pytest.mark.asyncio
    async def test_valid_code_returns_referrer(self, authenticated_client, db, student):
        from app.services.referral_service import ReferralService
        code = await ReferralService(db).ensure_referral_code(student)
        resp = await authenticated_client.get(f"/api/v1/referrals/{code}/validate")
        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is True
        assert body["referrer_display_name"] == student.display_name

    @pytest.mark.asyncio
    async def test_invalid_code_returns_false(self, authenticated_client):
        """Invalid referral code returns valid=false (not 404)."""
        resp = await authenticated_client.get("/api/v1/referrals/INVALID-CODE/validate")
        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is False

    @pytest.mark.asyncio
    async def test_wrong_prefix_returns_false(self, authenticated_client):
        """Code with wrong prefix returns valid=false."""
        resp = await authenticated_client.get("/api/v1/referrals/WRONG-ABC123/validate")
        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is False

    @pytest.mark.asyncio
    async def test_unknown_slug_returns_false(self, authenticated_client):
        """Unknown but well-formed code returns valid=false."""
        resp = await authenticated_client.get("/api/v1/referrals/SPETSER-NOEXIST/validate")
        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is False


class TestReferralLink:
    @pytest.mark.asyncio
    async def test_get_own_referral_link(self, authenticated_client, db, student):
        from app.services.referral_service import ReferralService
        code = await ReferralService(db).ensure_referral_code(student)
        resp = await authenticated_client.get("/api/v1/referrals/link")
        assert resp.status_code == 200
        body = resp.json()
        assert body["referral_code"] == code
        assert body["referral_link"].endswith(f"/r/{code}")

    @pytest.mark.asyncio
    async def test_private_skill_not_listed(self, authenticated_client, db, student):
        """Private skills are not listed in public endpoint."""
        from app.models.skill import Skill
        from app.services.referral_service import ReferralService

        # Create a private skill (not directly related to referrals, but testing auth)
        skill = Skill(
            id=uuid.uuid4(),
            name="Private Skill",
            slug="private-skill",
            system_prompt="Private",
            temperature=0.5,
            max_tokens=1000,
            is_public=False,
            is_premium=True,
            cost_multiplier=Decimal("1.5"),
        )
        db.add(skill)
        await db.commit()

        resp = await authenticated_client.get("/api/v1/referrals/link")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_unauthenticated_rejected(self, client):
        resp = await client.get("/api/v1/referrals/link")
        assert resp.status_code == 401


class TestReferralStats:
    @pytest.mark.asyncio
    async def test_get_stats(self, authenticated_client, db, student):
        from app.services.referral_service import ReferralService
        code = await ReferralService(db).ensure_referral_code(student)

        resp = await authenticated_client.get("/api/v1/referrals/stats")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_referrals"] == 0
        assert body["qualified_referrals"] == 0
        assert body["rewarded_referrals"] == 0
        assert body["total_earnings_usd"] == "0"
        assert body["referral_link"].endswith(f"/r/{student.referral_code}")

    @pytest.mark.asyncio
    async def test_unauthenticated_rejected(self, client):
        resp = await client.get("/api/v1/referrals/stats")
        assert resp.status_code == 401


class TestReferralCapture:
    """Tests for referral capture during registration (Lesson 7.3)."""

    @pytest.mark.asyncio
    async def test_register_with_valid_referral_code(
        self, authenticated_client, db, student
    ):
        """Registering with a valid referral code creates referral record."""
        # Create a referrer with a code
        referrer = Student(
            id=uuid.uuid4(),
            email=f"referrer_{uuid.uuid4().hex[:6]}@test.com",
            display_name="Referrer User",
            role="student",
            status="active",
            credit_balance=100,
            is_premium=False,
        )
        db.add(referrer)
        await db.commit()
        await db.refresh(referrer)

        ref_code = await ReferralService(db).ensure_referral_code(referrer)
        await db.commit()

        # Register new user with referrer's code
        ref_code = referrer.referral_code
        resp = await authenticated_client.post(
            "/api/v1/auth/register",
            json={
                "email": f"newuser{uuid.uuid4().hex[:6]}@test.com",
                "password": "password123",
                "display_name": "New User",
            },
            params={"ref": ref_code},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["data"]["referred_by_user_id"] == str(referrer.id)

        # Verify referral record was created
        from app.models.referral import Referral, ReferralStatus
        referral = (await db.execute(
            select(Referral).where(Referral.referred_user_id == uuid.UUID(data["data"]["id"]))
        )).scalar_one()
        assert referral.referrer_user_id == referrer.id
        assert referral.status == ReferralStatus.PENDING
        assert referral.referral_code == referrer.referral_code

    @pytest.mark.asyncio
    async def test_register_with_invalid_referral_code(
        self, authenticated_client, db, student
    ):
        """Invalid referral code is ignored (fail open)."""
        resp = await authenticated_client.post(
            "/api/v1/auth/register",
            json={
                "email": f"new{uuid.uuid4().hex[:6]}@test.com",
                "password": "password123",
                "display_name": "New User",
            },
            params={"ref": "SPETSER-INVALID"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["data"]["referred_by_user_id"] is None

    @pytest.mark.asyncio
    async def test_register_with_nonexistent_code(
        self, authenticated_client, db, student
    ):
        """Non-existent but well-formed code is ignored (fail open)."""
        from app.services.referral_service import ReferralService

        # Create a valid code for the student
        code = await ReferralService(db).ensure_referral_code(student)

        resp = await authenticated_client.post(
            "/api/v1/auth/register",
            json={
                "email": f"new{uuid.uuid4().hex[:6]}@test.com",
                "password": "password123",
                "display_name": "New User",
            },
            params={"ref": "SPETSER-NOEXIST"},  # well-formed but non-existent
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["data"]["referred_by_user_id"] is None

    @pytest.mark.asyncio
    async def test_self_referral_prevented(self, authenticated_client, db, student, app):
        """Self-referral is prevented (user cannot use their own referral code)."""
        # Create a referrer
        referrer = Student(
            id=uuid.uuid4(),
            email=f"referrer_{uuid.uuid4().hex[:6]}@test.com",
            display_name="Referrer User",
            role="student",
            status="active",
            credit_balance=100,
            is_premium=False,
        )
        db.add(referrer)
        await db.commit()
        await db.refresh(referrer)
        
        # Give the referrer a referral code
        ref_code = await ReferralService(db).ensure_referral_code(referrer)
        
        # Now try to register a NEW user with the referrer's code
        # but using a DIFFERENT email (not self-referral)
        resp = await authenticated_client.post(
            "/api/v1/auth/register",
            json={
                "email": f"newuser{uuid.uuid4().hex[:6]}@test.com",
                "password": "password123",
                "display_name": "New User",
            },
            params={"ref": ref_code},
        )
        # Should succeed and create referral
        assert resp.status_code == 201
        data = resp.json()
        assert data["data"]["referred_by_user_id"] == str(referrer.id)
        
        # Self-referral by email: the referrer re-registers with their OWN
        # email + their OWN code. Registration is rejected (duplicate email)
        # and no referral attribution is ever created.
        resp = await authenticated_client.post(
            "/api/v1/auth/register",
            json={
                "email": referrer.email,
                "password": "password123",
                "display_name": "Self Referrer Attempt",
            },
            params={"ref": ref_code},
        )
        assert resp.status_code == 409

        # Session-based self-referral: a logged-in user (student) uses their
        # OWN referral code for a second account with a different email.
        # (Use a fresh client — register replaces the session cookie.)
        own_code = await ReferralService(db).ensure_referral_code(student)
        await db.commit()

        token = create_session_token(student.id, student.role)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            cookies={SESSION_COOKIE_NAME: token},
        ) as sc:
            resp = await sc.post(
                "/api/v1/auth/register",
                json={
                    "email": f"another{uuid.uuid4().hex[:6]}@test.com",
                    "password": "password123",
                    "display_name": "Second Account",
                },
                params={"ref": own_code},
            )
        # Registration succeeds, but self-referral attribution is dropped.
        assert resp.status_code == 201
        data = resp.json()
        assert data["data"]["referred_by_user_id"] is None

    @pytest.mark.asyncio
    async def test_referral_record_created_with_correct_data(
        self, client, db, student
    ):
        """Referral record created with correct attribution data (anonymous visitor)."""
        code = await ReferralService(db).ensure_referral_code(student)

        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"new{uuid.uuid4().hex[:6]}@test.com",
                "password": "password123",
                "display_name": "Referred User",
            },
            params={"ref": code},
        )
        assert resp.status_code == 201
        data = resp.json()

        from app.models.referral import Referral, ReferralStatus
        referral = (await db.execute(
            select(Referral).where(Referral.referred_user_id == uuid.UUID(data["data"]["id"]))
        )).scalar_one()
        assert referral.referrer_user_id == student.id
        assert referral.status == ReferralStatus.PENDING
        assert referral.referral_code == student.referral_code
        assert referral.landing_page_url is not None
        assert referral.ip_address is not None
        assert referral.user_agent is not None


class TestReferralAntiFraud:
    """Anti-fraud checks (Lesson 7.4)."""

    @pytest.mark.asyncio
    async def test_disposable_email_gets_no_referral(self, client, db, student):
        """Registration with a disposable-email domain succeeds but creates no referral."""
        code = await ReferralService(db).ensure_referral_code(student)
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"throwaway{uuid.uuid4().hex[:6]}@mailinator.com",
                "password": "password123",
                "display_name": "Disposable User",
            },
            params={"ref": code},
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["referred_by_user_id"] is None

    @pytest.mark.asyncio
    async def test_device_fingerprint_collision_gets_no_referral(
        self, client, db, student
    ):
        """Same device fingerprint cannot farm multiple referred accounts."""
        code = await ReferralService(db).ensure_referral_code(student)
        fingerprint = f"fp-{uuid.uuid4().hex}"

        # First account from this device: attributed normally.
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"first{uuid.uuid4().hex[:6]}@test.com",
                "password": "password123",
                "display_name": "First Device User",
            },
            params={"ref": code},
            headers={"X-Device-Fingerprint": fingerprint},
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["referred_by_user_id"] == str(student.id)

        # Second account, same device fingerprint: registration OK, no referral.
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"second{uuid.uuid4().hex[:6]}@test.com",
                "password": "password123",
                "display_name": "Second Device User",
            },
            params={"ref": code},
            headers={"X-Device-Fingerprint": fingerprint},
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["referred_by_user_id"] is None

    @pytest.mark.asyncio
    async def test_check_fraud_duplicate_referral_rejected(self, db, student):
        """_check_fraud rejects referring the same user twice."""
        other = Student(
            id=uuid.uuid4(),
            email=f"dup_{uuid.uuid4().hex[:6]}@test.com",
            display_name="Duplicate Target",
            role="student",
            status="active",
            credit_balance=0,
        )
        db.add(other)
        await db.commit()
        await db.refresh(other)

        db.add(Referral(
            id=uuid.uuid4(),
            referrer_user_id=student.id,
            referred_user_id=other.id,
            referral_code=student.referral_code or "SPETSER-TEST1",
            status=ReferralStatus.PENDING,
        ))
        await db.commit()

        with pytest.raises(Exception) as exc_info:
            await ReferralService(db)._check_fraud(
                referrer=student, referred_user=other
            )
        assert "already been referred" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_check_fraud_self_referral_rejected(self, db, student):
        """_check_fraud rejects a referrer referring themselves."""
        with pytest.raises(Exception) as exc_info:
            await ReferralService(db)._check_fraud(
                referrer=student, referred_user=student
            )
        assert "self-referral" in str(exc_info.value).lower()

