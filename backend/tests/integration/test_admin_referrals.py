"""
tests/integration/test_admin_referrals.py
────────────────────────────────────────
Lesson 7.6 — Admin referral management + user /me endpoint.

RBAC:
- anonymous → 401
- student   → 403
- developer → 200 reads, 403 mutations
- admin     → full management (revoke / force-release)
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.models.referral import Referral, ReferralStatus
from app.models.reward_transaction import RewardStatus, RewardTransaction
from app.models.student import Student
from app.services.auth import (
    SESSION_COOKIE_NAME,
    create_session_token,
    hash_password,
)
from app.services.referral_service import ReferralService


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
    await db.refresh(s)
    return s


def _client_for(app: FastAPI, student: Student) -> AsyncClient:
    token = create_session_token(student.id, student.role)
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={SESSION_COOKIE_NAME: token},
    )


@pytest_asyncio.fixture
async def admin_client(app: FastAPI, admin) -> AsyncClient:
    async with _client_for(app, admin) as c:
        yield c


@pytest_asyncio.fixture
async def developer_client(app: FastAPI, developer) -> AsyncClient:
    async with _client_for(app, developer) as c:
        yield c


@pytest_asyncio.fixture
async def student_client(app: FastAPI, student) -> AsyncClient:
    async with _client_for(app, student) as c:
        yield c


@pytest_asyncio.fixture
async def pending_referral(db, student) -> tuple[Referral, RewardTransaction]:
    """A QUALIFIED referral with a PENDING (held) reward."""
    referrer = Student(
        id=uuid.uuid4(),
        email=f"rf_{uuid.uuid4().hex[:6]}@t.com",
        display_name="Referrer",
        role="student",
        status="active",
        credit_balance=Decimal("0"),
    )
    referred = Student(
        id=uuid.uuid4(),
        email=f"rd_{uuid.uuid4().hex[:6]}@t.com",
        display_name="Referred",
        role="student",
        status="active",
        credit_balance=Decimal("0"),
        referred_by_user_id=referrer.id,
    )
    db.add_all([referrer, referred])
    await db.commit()
    await db.refresh(referrer)
    await db.refresh(referred)
    await ReferralService(db).ensure_referral_code(referrer)

    referral = Referral(
        id=uuid.uuid4(),
        referrer_user_id=referrer.id,
        referred_user_id=referred.id,
        referral_code=referrer.referral_code,
        status=ReferralStatus.QUALIFIED,
    )
    db.add(referral)
    await db.commit()
    await db.refresh(referral)

    reward = RewardTransaction(
        id=uuid.uuid4(),
        user_id=referrer.id,
        referral_id=referral.id,
        amount=Decimal("5.00"),
        type="subscription_commission",
        status=RewardStatus.PENDING,
    )
    db.add(reward)
    await db.commit()
    await db.refresh(reward)
    return referral, reward


class TestAdminReferralsRBAC:
    @pytest.mark.asyncio
    async def test_anonymous_401(self, client):
        resp = await client.get("/api/v1/admin/referrals")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_student_403(self, student_client):
        resp = await student_client.get("/api/v1/admin/referrals")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_developer_can_read(self, developer_client):
        resp = await developer_client.get("/api/v1/admin/referrals")
        assert resp.status_code == 200
        assert "items" in resp.json()

    @pytest.mark.asyncio
    async def test_developer_cannot_revoke(self, developer_client, pending_referral):
        referral, _ = pending_referral
        resp = await developer_client.post(
            f"/api/v1/admin/referrals/{referral.id}/revoke")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_cannot_revoke_unknown_404(self, admin_client):
        resp = await admin_client.post(
            f"/api/v1/admin/referrals/{uuid.uuid4()}/revoke")
        assert resp.status_code == 404


class TestAdminReferralMutations:
    @pytest.mark.asyncio
    async def test_admin_revoke_voids_pending_reward(
        self, admin_client, db, pending_referral
    ):
        referral, reward = pending_referral
        resp = await admin_client.post(
            f"/api/v1/admin/referrals/{referral.id}/revoke")
        assert resp.status_code == 200
        assert resp.json()["status"] == ReferralStatus.REVOKED

        await db.refresh(reward)
        assert reward.status == RewardStatus.REVOKED

    @pytest.mark.asyncio
    async def test_admin_force_release_credits_referrer(
        self, admin_client, db, pending_referral
    ):
        referral, reward = pending_referral
        referrer_id = reward.user_id

        resp = await admin_client.post(
            f"/api/v1/admin/referrals/{referral.id}/release")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == RewardStatus.PAID
        assert body["amount"] == "5.00"

        await db.refresh(reward)
        assert reward.status == RewardStatus.PAID
        referrer_bal = (await db.execute(
            select(Student.credit_balance).where(Student.id == referrer_id)
        )).scalar_one()
        assert Decimal(referrer_bal) == Decimal("5.00")

        # Second release: no PENDING reward left → 409.
        resp = await admin_client.post(
            f"/api/v1/admin/referrals/{referral.id}/release")
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_admin_release_due_endpoint(
        self, admin_client, db, pending_referral
    ):
        """POST /admin/referrals/release-due releases only matured rewards."""
        referral, reward = pending_referral
        # Backdate past the holding period.
        from datetime import datetime, timedelta, timezone
        reward.scheduled_release_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await db.commit()

        resp = await admin_client.post("/api/v1/admin/referrals/release-due")
        assert resp.status_code == 200
        body = resp.json()
        assert body["released_count"] >= 1

        await db.refresh(reward)
        assert reward.status == RewardStatus.PAID
        await db.refresh(referral)
        assert referral.status == ReferralStatus.REWARDED

        # Idempotent second call.
        resp = await admin_client.post("/api/v1/admin/referrals/release-due")
        assert resp.status_code == 200
        assert resp.json()["released_count"] == 0

    @pytest.mark.asyncio
    async def test_admin_list_shows_emails_and_reward(
        self, admin_client, pending_referral
    ):
        referral, reward = pending_referral
        resp = await admin_client.get(
            "/api/v1/admin/referrals", params={"status": "qualified"})
        assert resp.status_code == 200
        items = resp.json()["items"]
        match = [i for i in items if i["id"] == str(referral.id)]
        assert match, "created referral missing from admin list"
        item = match[0]
        assert item["referrer_email"] is not None
        assert item["referred_email"] is not None
        assert item["reward_amount"] == "5.00"
        assert item["reward_status"] == RewardStatus.PENDING


class TestUserReferralMe:
    @pytest.mark.asyncio
    async def test_me_returns_snapshot(self, authenticated_client, student):
        resp = await authenticated_client.get("/api/v1/referrals/me")
        assert resp.status_code == 200
        body = resp.json()
        for key in ("total_referrals", "qualified_referrals",
                    "rewarded_referrals", "total_earnings_usd",
                    "referral_link", "referral_code", "referred_by_user_id"):
            assert key in body
        assert body["referral_code"].startswith("SPETSER-")

    @pytest.mark.asyncio
    async def test_me_unauthenticated_401(self, client):
        resp = await client.get("/api/v1/referrals/me")
        assert resp.status_code == 401
