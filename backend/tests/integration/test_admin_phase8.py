"""
tests/integration/test_admin_phase8.py
──────────────────────────────────────
Lessons 8.4–8.6 — user management, payment management, analytics.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.payment_invoice import PaymentInvoice, PaymentStatus
from app.models.student import Student
from app.services.auth import (
    SESSION_COOKIE_NAME,
    create_session_token,
    hash_password,
)


async def _make_user(db, role: str = "student", **kw) -> Student:
    s = Student(
        id=uuid.uuid4(),
        email=f"{role}_{uuid.uuid4().hex[:6]}@t.com",
        display_name=role.title(),
        password_hash=hash_password("pass12345"),
        role=role,
        status=kw.get("status", "active"),
        credit_balance=kw.get("credit_balance", Decimal("100")),
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


def _client(app: FastAPI, user: Student) -> AsyncClient:
    token = create_session_token(user.id, user.role)
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={SESSION_COOKIE_NAME: token},
    )


# ── Lesson 8.4: User management ─────────────────────────────────────────────

class TestUserManagement:
    @pytest.mark.asyncio
    async def test_rbac(self, app, db, client):
        assert (await client.get("/api/v1/admin/users")).status_code == 401
        stu = await _make_user(db, "student")
        async with _client(app, stu) as c:
            assert (await c.get("/api/v1/admin/users")).status_code == 403

    @pytest.mark.asyncio
    async def test_list_and_search(self, app, db):
        admin = await _make_user(db, "admin")
        target = await _make_user(db, "student")
        async with _client(app, admin) as c:
            resp = await c.get("/api/v1/admin/users",
                               params={"q": target.email})
            assert resp.status_code == 200
            items = resp.json()["items"]
            assert any(i["id"] == str(target.id) for i in items)
            # API key / password hash never leaks.
            assert "password_hash" not in resp.text
            assert "pass12345" not in resp.text

    @pytest.mark.asyncio
    async def test_get_user_detail(self, app, db):
        admin = await _make_user(db, "admin")
        target = await _make_user(db, "student")
        async with _client(app, admin) as c:
            resp = await c.get(f"/api/v1/admin/users/{target.id}")
            assert resp.status_code == 200
            assert resp.json()["email"] == target.email
            assert (await c.get(
                f"/api/v1/admin/users/{uuid.uuid4()}")).status_code == 404

    @pytest.mark.asyncio
    async def test_adjust_credits_audited(self, app, db):
        admin = await _make_user(db, "admin")
        target = await _make_user(db, "student",
                                  credit_balance=Decimal("100"))
        async with _client(app, admin) as c:
            resp = await c.post(
                f"/api/v1/admin/users/{target.id}/adjust-credits",
                json={"amount": "25", "reason": "goodwill credit"})
            assert resp.status_code == 200
            assert Decimal(resp.json()["credit_balance"]) == Decimal("125")

            # Debit is allowed for admins (documented exception).
            resp = await c.post(
                f"/api/v1/admin/users/{target.id}/adjust-credits",
                json={"amount": "-150", "reason": "fraud clawback"})
            assert resp.status_code == 200
            assert Decimal(resp.json()["credit_balance"]) == Decimal("-25")

        logs = (await db.execute(
            select(AuditLog).where(AuditLog.action == "credit.admin_adjust")
        )).scalars().all()
        assert len(logs) >= 2

    @pytest.mark.asyncio
    async def test_zero_amount_rejected(self, app, db):
        admin = await _make_user(db, "admin")
        target = await _make_user(db, "student")
        async with _client(app, admin) as c:
            resp = await c.post(
                f"/api/v1/admin/users/{target.id}/adjust-credits",
                json={"amount": "0", "reason": "noop"})
            assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_ban_unban(self, app, db):
        admin = await _make_user(db, "admin")
        target = await _make_user(db, "student")
        async with _client(app, admin) as c:
            resp = await c.post(f"/api/v1/admin/users/{target.id}/ban")
            assert resp.status_code == 200
            assert resp.json()["status"] == "banned"

            # Banned user cannot use authenticated endpoints.
            # Ban bumps session_version, so the old token is dead (401).
            async with _client(app, target) as tc:
                r = await tc.get("/api/v1/credits/balance")
                assert r.status_code in (401, 403)

            resp = await c.post(f"/api/v1/admin/users/{target.id}/unban")
            assert resp.status_code == 200
            assert resp.json()["status"] == "active"

        logs = [r.action for r in (await db.execute(
            select(AuditLog).where(AuditLog.resource_type == "student",
                                   AuditLog.resource_id == str(target.id))
        )).scalars().all()]
        assert "user.banned" in logs and "user.unbanned" in logs

    @pytest.mark.asyncio
    async def test_admin_cannot_ban_self_or_superadmin(self, app, db):
        admin = await _make_user(db, "admin")
        sa = await _make_user(db, "superadmin")
        async with _client(app, admin) as c:
            assert (await c.post(
                f"/api/v1/admin/users/{admin.id}/ban")).status_code == 409
            assert (await c.post(
                f"/api/v1/admin/users/{sa.id}/ban")).status_code == 409

    @pytest.mark.asyncio
    async def test_transactions_endpoint(self, app, db):
        admin = await _make_user(db, "admin")
        target = await _make_user(db, "student")
        async with _client(app, admin) as c:
            resp = await c.get(f"/api/v1/admin/users/{target.id}/transactions")
            assert resp.status_code == 200
            assert "items" in resp.json()


# ── Lesson 8.5: Payment management ──────────────────────────────────────────

async def _make_invoice(db, user_id, status=PaymentStatus.PENDING,
                        amount="50") -> PaymentInvoice:
    inv = PaymentInvoice(
        id=uuid.uuid4(), user_id=user_id, provider="mock_crypto",
        external_invoice_id=f"ext-{uuid.uuid4().hex[:10]}",
        amount_usd=Decimal(amount), currency="USDT",
        status=status, idempotency_key=f"adm-{uuid.uuid4().hex}",
    )
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    return inv


class TestPaymentManagement:
    @pytest.mark.asyncio
    async def test_rbac(self, app, db, client):
        assert (await client.get("/api/v1/admin/payments")).status_code == 401
        stu = await _make_user(db, "student")
        async with _client(app, stu) as c:
            assert (await c.get("/api/v1/admin/payments")).status_code == 403

    @pytest.mark.asyncio
    async def test_list_and_detail(self, app, db):
        admin = await _make_user(db, "admin")
        buyer = await _make_user(db, "student")
        inv = await _make_invoice(db, buyer.id)
        async with _client(app, admin) as c:
            resp = await c.get("/api/v1/admin/payments",
                               params={"status": "pending"})
            assert resp.status_code == 200
            assert any(i["id"] == str(inv.id) for i in resp.json()["items"])

            resp = await c.get(f"/api/v1/admin/payments/{inv.id}")
            assert resp.status_code == 200
            body = resp.json()
            assert Decimal(body["amount_usd"]) == Decimal("50")
            assert body["webhook_events"] == []

    @pytest.mark.asyncio
    async def test_manual_confirm_superadmin_only(self, app, db):
        admin = await _make_user(db, "admin")
        buyer = await _make_user(db, "student",
                                 credit_balance=Decimal("0"))
        inv = await _make_invoice(db, buyer.id)
        async with _client(app, admin) as c:
            resp = await c.post(
                f"/api/v1/admin/payments/{inv.id}/manual-confirm",
                json={"reason": "gateway outage workaround"})
            assert resp.status_code == 403  # admin is not superadmin

    @pytest.mark.asyncio
    async def test_manual_confirm_credits_and_audits(self, app, db):
        sa = await _make_user(db, "superadmin")
        buyer = await _make_user(db, "student",
                                 credit_balance=Decimal("0"))
        inv = await _make_invoice(db, buyer.id)
        async with _client(app, sa) as c:
            resp = await c.post(
                f"/api/v1/admin/payments/{inv.id}/manual-confirm",
                json={"reason": "verified bank transfer"})
            assert resp.status_code == 200
            assert resp.json()["status"] == "paid"

        await db.refresh(inv)
        assert inv.status == PaymentStatus.PAID
        await db.refresh(buyer)
        assert Decimal(buyer.credit_balance) == Decimal("5000")  # 50 * 100

        # Second confirm is rejected (not PENDING anymore).
        async with _client(app, sa) as c:
            resp = await c.post(
                f"/api/v1/admin/payments/{inv.id}/manual-confirm",
                json={"reason": "retry attempt"})
            assert resp.status_code == 409

        log = (await db.execute(
            select(AuditLog).where(
                AuditLog.action == "payment.manual_confirmed")
        )).scalars().one()
        assert log.resource_id == str(inv.id)

    @pytest.mark.asyncio
    async def test_manual_confirm_rejects_short_reason(self, app, db):
        sa = await _make_user(db, "superadmin")
        buyer = await _make_user(db, "student")
        inv = await _make_invoice(db, buyer.id)
        async with _client(app, sa) as c:
            resp = await c.post(
                f"/api/v1/admin/payments/{inv.id}/manual-confirm",
                json={"reason": "x"})
            assert resp.status_code == 422


# ── Lesson 8.6: Analytics ───────────────────────────────────────────────────

class TestAnalytics:
    @pytest.mark.asyncio
    async def test_rbac(self, app, db, client):
        for path in ("overview", "llm-usage", "revenue", "referrals"):
            resp = await client.get(f"/api/v1/admin/analytics/{path}")
            assert resp.status_code == 401
        stu = await _make_user(db, "student")
        async with _client(app, stu) as c:
            resp = await c.get("/api/v1/admin/analytics/overview")
            assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_overview_shape(self, app, db):
        dev = await _make_user(db, "developer")
        async with _client(app, dev) as c:
            resp = await c.get("/api/v1/admin/analytics/overview")
            assert resp.status_code == 200
            body = resp.json()
            for section in ("users", "messages", "revenue", "referrals"):
                assert section in body
            assert body["users"]["total"] >= 1

    @pytest.mark.asyncio
    async def test_llm_usage_shape(self, app, db):
        dev = await _make_user(db, "developer")
        async with _client(app, dev) as c:
            resp = await c.get("/api/v1/admin/analytics/llm-usage")
            assert resp.status_code == 200
            body = resp.json()
            assert body["window_days"] == 30
            assert body["by_provider"] == []
            assert body["by_skill"] == []

    @pytest.mark.asyncio
    async def test_revenue_includes_paid_invoice(self, app, db):
        dev = await _make_user(db, "developer")
        buyer = await _make_user(db, "student")
        await _make_invoice(db, buyer.id, status=PaymentStatus.PAID,
                            amount="75")
        async with _client(app, dev) as c:
            resp = await c.get("/api/v1/admin/analytics/revenue")
            assert resp.status_code == 200
            body = resp.json()
            assert Decimal(body["paid"]["total_usd"]) >= Decimal("75")
            assert body["paid"]["count"] >= 1

    @pytest.mark.asyncio
    async def test_referral_analytics_shape(self, app, db):
        dev = await _make_user(db, "developer")
        async with _client(app, dev) as c:
            resp = await c.get("/api/v1/admin/analytics/referrals")
            assert resp.status_code == 200
            body = resp.json()
            assert "by_status" in body
            assert "rewards" in body
            assert "pending_amount_usd" in body["rewards"]


# ── Lesson 8.7: Audit logs ──────────────────────────────────────────────────

class TestAuditLogs:
    @pytest.mark.asyncio
    async def test_rbac(self, app, db, client):
        assert (await client.get("/api/v1/admin/audit-logs")).status_code == 401
        stu = await _make_user(db, "student")
        async with _client(app, stu) as c:
            assert (await c.get(
                "/api/v1/admin/audit-logs")).status_code == 403
            assert (await c.get(
                f"/api/v1/admin/audit-logs/{uuid.uuid4()}"
            )).status_code == 403

    @pytest.mark.asyncio
    async def test_list_shape_and_paging(self, app, db):
        dev = await _make_user(db, "developer")
        async with _client(app, dev) as c:
            resp = await c.get("/api/v1/admin/audit-logs",
                               params={"limit": 10, "offset": 0})
            assert resp.status_code == 200
            body = resp.json()
            assert set(body) >= {"items", "total", "limit", "offset"}
            assert isinstance(body["items"], list)

    @pytest.mark.asyncio
    async def test_list_is_desc_and_filterable_by_action(self, app, db):
        admin = await _make_user(db, "admin")
        target = await _make_user(db, "student")
        # Generate a known audit entry.
        async with _client(app, admin) as c:
            r = await c.post(f"/api/v1/admin/users/{target.id}/ban")
            assert r.status_code == 200

            resp = await c.get("/api/v1/admin/audit-logs",
                               params={"action": "user.banned"})
            assert resp.status_code == 200
            body = resp.json()
            assert body["total"] >= 1
            assert all(i["action"] == "user.banned" for i in body["items"])
            assert any(i["resource_id"] == str(target.id)
                       for i in body["items"])

            # Newest first.
            times = [i["created_at"] for i in body["items"]]
            assert times == sorted(times, reverse=True)

    @pytest.mark.asyncio
    async def test_filter_by_resource_type(self, app, db):
        admin = await _make_user(db, "admin")
        target = await _make_user(db, "student")
        async with _client(app, admin) as c:
            await c.post(f"/api/v1/admin/users/{target.id}/ban")
            resp = await c.get("/api/v1/admin/audit-logs",
                               params={"resource_type": "student",
                                       "resource_id": str(target.id)})
            assert resp.status_code == 200
            body = resp.json()
            assert body["total"] >= 1
            assert all(i["resource_type"] == "student"
                       for i in body["items"])

    @pytest.mark.asyncio
    async def test_get_single_entry(self, app, db):
        admin = await _make_user(db, "admin")
        target = await _make_user(db, "student")
        async with _client(app, admin) as c:
            await c.post(f"/api/v1/admin/users/{target.id}/ban")
            listing = await c.get("/api/v1/admin/audit-logs",
                                  params={"action": "user.banned"})
            log_id = listing.json()["items"][0]["id"]

            resp = await c.get(f"/api/v1/admin/audit-logs/{log_id}")
            assert resp.status_code == 200
            body = resp.json()
            assert body["id"] == log_id
            assert body["action"] == "user.banned"
            assert body["actor_id"] == str(admin.id)

            missing = await c.get(f"/api/v1/admin/audit-logs/{uuid.uuid4()}")
            assert missing.status_code == 404

    @pytest.mark.asyncio
    async def test_mutation_is_visible_in_audit_trail(self, app, db):
        """End-to-end: admin mutation → appears in the audit list."""
        admin = await _make_user(db, "admin")
        target = await _make_user(db, "student")
        async with _client(app, admin) as c:
            await c.post(f"/api/v1/admin/users/{target.id}/ban")
            await c.post(f"/api/v1/admin/users/{target.id}/unban")

            resp = await c.get("/api/v1/admin/audit-logs",
                               params={"resource_id": str(target.id)})
            actions = [i["action"] for i in resp.json()["items"]]
            assert "user.banned" in actions
            assert "user.unbanned" in actions
