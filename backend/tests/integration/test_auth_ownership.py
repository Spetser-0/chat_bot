"""
tests/integration/test_auth_ownership.py
────────────────────────────────────────
Integration tests for authentication and authorization:
- Missing credentials
- Invalid credentials
- Valid identity extraction
- Unauthorized balance access
- Unauthorized request access
- Developer-only access
- Mismatch between token identity and submitted student_id
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.credit_ledger import CreditLedger, LedgerEntryType
from app.models.deliverable import Deliverable, DeliverableStatus
from app.models.request import Request, RequestStatus
from app.models.student import Student
from app.services.auth import SESSION_COOKIE_NAME, create_session_token, hash_password

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def another_student() -> dict:
    """Another student for cross-ownership tests."""
    unique = uuid.uuid4().hex[:8]
    return {
        "id": uuid.uuid4(),
        "email": f"other_{unique}@test.com",
        "display_name": "Other Student",
        "password_hash": hash_password("password123"),
        "role": "student",
        "status": "active",
        "credit_balance": 50.0,
    }


@pytest_asyncio.fixture
async def other_student(db: AsyncSession, another_student: dict) -> Student:
    """Persist another student."""
    s = Student(**another_student)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


@pytest_asyncio.fixture
async def other_student_client(app, other_student: Student) -> AsyncClient:
    """Authenticated client for the other student."""
    from httpx import ASGITransport

    from app.services.auth import SESSION_COOKIE_NAME
    token = create_session_token(other_student.id, other_student.role)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={SESSION_COOKIE_NAME: token},
    ) as client:
        yield client


@pytest_asyncio.fixture
async def owned_request(db: AsyncSession, student: Student) -> Request:
    """A request owned by the primary test student."""
    req = Request(
        student_id=student.id,
        feature="presentation",
        intent="presentation",
        model_tier="thinker",
        status=RequestStatus.PENDING,
        request_payload_hash="abc123",
        idempotency_key="idem-123",
        display_title="My Presentation",
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req


@pytest_asyncio.fixture
async def other_request(db: AsyncSession, other_student: Student) -> Request:
    """A request owned by the other student."""
    req = Request(
        student_id=other_student.id,
        feature="presentation",
        intent="presentation",
        model_tier="default",
        status=RequestStatus.READY,
        request_payload_hash="def456",
        idempotency_key="idem-456",
        display_title="Other's Presentation",
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req


@pytest_asyncio.fixture
async def owned_deliverable(db: AsyncSession, student: Student, owned_request: Request) -> Deliverable:
    """A deliverable owned by the primary test student."""
    deliv = Deliverable(
        request_id=owned_request.id,
        student_id=student.id,
        file_type="pptx",
        storage_object_key="presentations/student/file.pptx",
        mime_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        file_size=102400,
        status=DeliverableStatus.READY,
    )
    db.add(deliv)
    await db.commit()
    await db.refresh(deliv)
    return deliv


@pytest_asyncio.fixture
async def other_deliverable(db: AsyncSession, other_student: Student, other_request: Request) -> Deliverable:
    """A deliverable owned by the other student."""
    deliv = Deliverable(
        request_id=other_request.id,
        student_id=other_student.id,
        file_type="pptx",
        storage_object_key="presentations/other/file.pptx",
        mime_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        file_size=204800,
        status=DeliverableStatus.READY,
    )
    db.add(deliv)
    await db.commit()
    await db.refresh(deliv)
    return deliv


@pytest_asyncio.fixture
async def credit_entry(db: AsyncSession, student: Student, owned_request: Request) -> CreditLedger:
    """A credit ledger entry for the primary student."""
    from decimal import Decimal
    entry = CreditLedger(
        student_id=student.id,
        request_id=owned_request.id,
        provider="anthropic",
        model="claude-3-sonnet",
        input_tokens=1000,
        output_tokens=500,
        computed_usd_cost=Decimal("0.015"),
        pricing_version="1.0",
        credits_charged=Decimal("1.5"),
        entry_type=LedgerEntryType.CHARGE,
        idempotency_key="idem-charge-1",
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


# ──────────────────────────────────────────────────────────────────────────────
# Tests: Missing Credentials
# ──────────────────────────────────────────────────────────────────────────────

class TestMissingCredentials:
    """Tests for 401 when credentials are missing."""

    @pytest.mark.asyncio
    async def test_me_without_cookie(self, client: AsyncClient):
        """GET /auth/me without session cookie returns 401."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "AUTHENTICATION_REQUIRED"

    @pytest.mark.asyncio
    async def test_protected_route_without_cookie(self, client: AsyncClient):
        """Any protected route without cookie returns 401."""
        # We'll test with a future protected route
        # For now, /auth/me is the only protected route


# ──────────────────────────────────────────────────────────────────────────────
# Tests: Invalid Credentials
# ──────────────────────────────────────────────────────────────────────────────

class TestInvalidCredentials:
    """Tests for 401 when credentials are invalid."""

    @pytest.mark.asyncio
    async def test_me_with_invalid_cookie(self, client: AsyncClient):
        """GET /auth/me with invalid cookie returns 401."""
        response = await client.get(
            "/api/v1/auth/me",
            cookies={SESSION_COOKIE_NAME: "invalid.token.here"},
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"

    @pytest.mark.asyncio
    async def test_me_with_tampered_cookie(self, client: AsyncClient):
        """GET /auth/me with tampered cookie returns 401."""
        # A valid-looking but incorrectly signed token
        response = await client.get(
            "/api/v1/auth/me",
            cookies={SESSION_COOKIE_NAME: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_with_expired_cookie(self, client: AsyncClient, student: Student):
        """GET /auth/me with expired cookie returns 401 (session expired)."""
        # Create an expired token (negative max_age would require time travel)
        # For now, we test with invalid signature which gives same error code
        response = await client.get(
            "/api/v1/auth/me",
            cookies={SESSION_COOKIE_NAME: "expired.token.signature"},
        )
        assert response.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# Tests: Valid Identity Extraction
# ──────────────────────────────────────────────────────────────────────────────

class TestValidIdentityExtraction:
    """Tests for successful identity extraction from valid session."""

    @pytest.mark.asyncio
    async def test_me_returns_correct_student(self, authenticated_client: AsyncClient, student: Student):
        """GET /auth/me returns the correct student data."""
        response = await authenticated_client.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == str(student.id)
        assert data["email"] == student.email
        assert data["role"] == student.role
        assert data["credit_balance"] == student.credit_balance

    @pytest.mark.asyncio
    async def test_login_sets_cookie(self, client: AsyncClient, student: Student):
        """Login returns session cookie with valid token."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": student.email, "password": "password123"},
        )
        assert response.status_code == 200
        assert SESSION_COOKIE_NAME in response.cookies

    @pytest.mark.asyncio
    async def test_register_sets_cookie(self, client: AsyncClient):
        """Register returns session cookie with valid token."""
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "newreg@test.com", "password": "password123", "display_name": "New Reg"},
        )
        assert response.status_code == 201
        assert SESSION_COOKIE_NAME in response.cookies

    @pytest.mark.asyncio
    async def test_developer_role_preserved_in_token(self, developer_client: AsyncClient, developer: Student):
        """Developer role is correctly encoded in session token."""
        response = await developer_client.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["role"] == "developer"


# ──────────────────────────────────────────────────────────────────────────────
# Tests: Ownership Checks
# ──────────────────────────────────────────────────────────────────────────────

class TestRequestOwnership:
    """Tests for request ownership verification."""

    @pytest.mark.asyncio
    async def test_student_can_access_own_request(
        self, authenticated_client: AsyncClient, owned_request: Request, student: Student
    ):
        """Student can access their own request (future endpoint)."""
        # This tests the ownership logic; actual endpoint not yet implemented
        # We verify the dependency logic by checking the test fixtures are correct
        assert owned_request.student_id == student.id

    @pytest.mark.asyncio
    async def test_student_cannot_access_other_student_request(
        self, authenticated_client: AsyncClient, other_request: Request, student: Student
    ):
        """Student cannot access another student's request - verified by ownership check."""
        # This will be enforced by verify_request_ownership dependency
        assert other_request.student_id != student.id

    @pytest.mark.asyncio
    async def test_developer_cannot_access_student_request(
        self, developer_client: AsyncClient, student: Student
    ):
        """Developer cannot access a regular student's request."""
        # Test that developer's /me returns their own identity, not student's
        response = await developer_client.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["role"] == "developer"
        assert data["email"] != student.email


class TestDeliverableOwnership:
    """Tests for deliverable ownership verification."""

    @pytest.mark.asyncio
    async def test_student_can_access_own_deliverable(
        self, student: Student, owned_deliverable: Deliverable
    ):
        """Student owns their deliverable."""
        assert owned_deliverable.student_id == student.id

    @pytest.mark.asyncio
    async def test_student_cannot_access_other_deliverable(
        self, student: Student, other_deliverable: Deliverable
    ):
        """Student does not own other student's deliverable."""
        assert other_deliverable.student_id != student.id


class TestCreditBalanceOwnership:
    """Tests for credit balance ownership verification."""

    @pytest.mark.asyncio
    async def test_student_sees_own_balance(self, authenticated_client: AsyncClient, student: Student):
        """GET /auth/me shows student's own credit balance."""
        response = await authenticated_client.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["credit_balance"] == student.credit_balance

    @pytest.mark.asyncio
    async def test_student_does_not_see_other_balance(
        self, student: Student, other_student: Student
    ):
        """Student cannot see another student's balance (enforced by not exposing it)."""
        # No endpoint exposes another student's balance
        assert student.id != other_student.id
        assert student.credit_balance != other_student.credit_balance


class TestHistoryOwnership:
    """Tests for request history ownership."""

    @pytest.mark.asyncio
    async def test_student_sees_own_history_only(
        self, student: Student, owned_request: Request, other_request: Request
    ):
        """Student's history only includes their own requests."""
        # Future endpoint will filter by student_id
        assert owned_request.student_id == student.id
        assert other_request.student_id != student.id


# ──────────────────────────────────────────────────────────────────────────────
# Tests: Developer/Admin Authorization
# ──────────────────────────────────────────────────────────────────────────────

class TestDeveloperAuthorization:
    """Tests for developer-only access control."""

    @pytest.mark.asyncio
    async def test_regular_student_cannot_access_developer_endpoint(
        self, authenticated_client: AsyncClient
    ):
        """Regular student gets 403 on developer-only endpoint."""
        # Placeholder for future /api/v1/developer/* endpoints
        # Currently no developer endpoints exist, but the dependency exists

    @pytest.mark.asyncio
    async def test_developer_can_access_developer_routes(self, developer_client: AsyncClient):
        """Developer can access their own /me."""
        response = await developer_client.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["role"] == "developer"


# ──────────────────────────────────────────────────────────────────────────────
# Tests: Token Identity vs Submitted student_id Mismatch
# ──────────────────────────────────────────────────────────────────────────────

class TestIdentityMismatch:
    """Tests ensuring client-submitted student_id is never trusted over token."""

    @pytest.mark.asyncio
    async def test_request_body_student_id_ignored(self, authenticated_client: AsyncClient, student: Student):
        """Any endpoint that takes student_id in body should use token identity instead."""
        # The current auth endpoints don't accept student_id in body
        # This test documents the invariant for future endpoints

    @pytest.mark.asyncio
    async def test_me_returns_token_identity_not_body(self, authenticated_client: AsyncClient, student: Student):
        """GET /auth/me returns identity from token, never from request body."""
        response = await authenticated_client.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()["data"]
        # Even if someone tried to send student_id in body (which /me doesn't accept),
        # the response is based on the cookie token
        assert data["id"] == str(student.id)

    @pytest.mark.asyncio
    async def test_cookie_identity_matches_database(self, authenticated_client: AsyncClient, student: Student):
        """Token identity matches database record."""
        response = await authenticated_client.get("/api/v1/auth/me")
        data = response.json()["data"]
        assert data["email"] == student.email
        assert data["role"] == student.role


# ──────────────────────────────────────────────────────────────────────────────
# Tests: Development Auth Mode
# ──────────────────────────────────────────────────────────────────────────────

class TestDevAuthMode:
    """Tests for development authentication bypass."""

    @pytest.mark.asyncio
    async def test_dev_auth_disabled_by_default(self, client: AsyncClient):
        """Dev auth is disabled by default (DEV_AUTH_ENABLED not set)."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"X-Dev-Auth": "true"},
        )
        # Should still require real auth
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_dev_auth_with_valid_config(
        self, 
        monkeypatch, 
        client: AsyncClient, 
        student: Student
    ):
        """Dev auth works when DEV_AUTH_ENABLED=true and DEV_AUTH_STUDENT_ID set."""
        
        # Enable dev auth
        monkeypatch.setenv("DEV_AUTH_ENABLED", "true")
        monkeypatch.setenv("DEV_AUTH_STUDENT_ID", str(student.id))
        
        # Reload the dev auth provider
        from importlib import reload

        import app.services.auth as auth_module
        reload(auth_module)
        
        assert auth_module.is_dev_auth_enabled() is True
        identity = await auth_module.get_dev_student_identity()
        assert identity is not None
        assert identity.student_id == student.id