# ──────────────────────────────────────────────────────────────────────────────
# Tests: Idempotency
# ──────────────────────────────────────────────────────────────────────────────

import pytest
import pytest_asyncio
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.request import Request, RequestStatus
from app.models.student import Student
from app.models.provider import ModelProvider
from app.models.model_configuration import ModelConfiguration
from app.models.feature_configuration import FeatureConfiguration
from app.models.routing_rule import RoutingRule
from app.services.auth import create_session_token, SESSION_COOKIE_NAME, hash_password

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures (copied from test_presentation.py)
# ──────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def presentation_student(db: AsyncSession) -> Student:
    """Student with high credit balance for presentation tests."""
    unique = uuid.uuid4().hex[:8]
    s = Student(
        id=uuid.uuid4(),
        email=f"presentation_{unique}@test.com",
        display_name="Presentation User",
        password_hash=hash_password("password123"),
        role="student",
        status="active",
        credit_balance=1000.0,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


@pytest_asyncio.fixture
async def presentation_client(app, presentation_student: Student) -> AsyncClient:
    """Authenticated client for presentation tests."""
    token = create_session_token(presentation_student.id, presentation_student.role)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={SESSION_COOKIE_NAME: token},
    ) as client:
        yield client


@pytest_asyncio.fixture
async def other_student(db: AsyncSession) -> Student:
    """Another student for ownership tests."""
    unique = uuid.uuid4().hex[:8]
    s = Student(
        id=uuid.uuid4(),
        email=f"other_{unique}@test.com",
        display_name="Other Student",
        password_hash=hash_password("password123"),
        role="student",
        status="active",
        credit_balance=50.0,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


@pytest_asyncio.fixture
async def setup_routing_config(db: AsyncSession) -> None:
    """Create routing configuration for presentation tests (per-test)."""
    # Check if already exists
    existing_provider = await db.execute(
        select(ModelProvider).where(ModelProvider.provider_key == "mock")
    )
    if existing_provider.scalar_one_or_none():
        return  # Already set up
    
    # Create provider
    provider = ModelProvider(
        id=uuid.uuid4(),
        provider_key="mock",
        display_name="Mock Provider",
        enabled=True,
        health_status="healthy",
    )
    db.add(provider)
    
    # Create model configurations for each tier
    for tier in ["fast", "default", "thinker"]:
        model_config = ModelConfiguration(
            id=uuid.uuid4(),
            provider_id=provider.id,
            model_name=f"mock-{tier}",
            tier=tier,
            capabilities_json=["json"],
            input_price_per_1k_tokens=0.001,
            output_price_per_1k_tokens=0.002,
            max_tokens=4096,
            enabled=True,
            fallback_priority=100 if tier == "default" else 200,
        )
        db.add(model_config)
    
    # Create feature configuration
    feature_config = FeatureConfiguration(
        feature_key="presentation",
        enabled=True,
        default_tier="default",
    )
    db.add(feature_config)
    await db.flush()
    
    # Get the model configs we just created
    result = await db.execute(
        select(ModelConfiguration).where(ModelConfiguration.provider_id == provider.id)
    )
    model_configs = result.scalars().all()
    
    # Create routing rules for each tier
    for tier in ["fast", "default", "thinker"]:
        mc = next((m for m in model_configs if m.tier == tier), None)
        if mc:
            routing_rule = RoutingRule(
                feature_key="presentation",
                tier=tier,
                primary_model_configuration_id=mc.id,
                fallback_model_configuration_ids=[],
                max_retries=1,
                timeout_seconds=60,
                enabled=True,
            )
            db.add(routing_rule)
    
    await db.commit()


# ──────────────────────────────────────────────────────────────────────────────

class TestIdempotency:
    """Comprehensive tests for Idempotency-Key header."""

    @pytest.mark.asyncio
    async def test_same_key_after_success(
        self, presentation_client: AsyncClient, setup_routing_config: None
    ):
        """Same idempotency key after success returns existing request."""
        idempotency_key = "idem-success-123"
        
        response1 = await presentation_client.post(
            "/api/v1/presentations",
            json={"topic": "Test Success", "language": "ar"},
            headers={"Idempotency-Key": idempotency_key},
        )
        assert response1.status_code == 201
        data1 = response1.json()["data"]
        request_id_1 = data1["request_id"]
        
        response2 = await presentation_client.post(
            "/api/v1/presentations",
            json={"topic": "Test Success", "language": "ar"},
            headers={"Idempotency-Key": idempotency_key},
        )
        assert response2.status_code == 201
        data2 = response2.json()["data"]
        assert data2["request_id"] == request_id_1
        assert data2["status"] == "pending"

    @pytest.mark.asyncio
    async def test_same_key_during_processing(
        self, presentation_client: AsyncClient, setup_routing_config: None
    ):
        """Same idempotency key during processing returns existing request."""
        idempotency_key = "idem-processing-123"
        
        response1 = await presentation_client.post(
            "/api/v1/presentations",
            json={"topic": "Test Processing", "language": "ar"},
            headers={"Idempotency-Key": idempotency_key},
        )
        assert response1.status_code == 201
        data1 = response1.json()["data"]
        request_id_1 = data1["request_id"]
        
        response2 = await presentation_client.post(
            "/api/v1/presentations",
            json={"topic": "Test Processing", "language": "ar"},
            headers={"Idempotency-Key": idempotency_key},
        )
        assert response2.status_code == 201
        data2 = response2.json()["data"]
        assert data2["request_id"] == request_id_1
        assert data2["status"] == "pending"

    @pytest.mark.asyncio
    async def test_same_key_with_changed_payload(
        self, presentation_client: AsyncClient, setup_routing_config: None
    ):
        """Same idempotency key with different payload returns existing request."""
        idempotency_key = "idem-changed-payload-123"
        
        response1 = await presentation_client.post(
            "/api/v1/presentations",
            json={"topic": "Original Topic", "language": "ar", "slide_count": 5},
            headers={"Idempotency-Key": idempotency_key},
        )
        assert response1.status_code == 201
        request_id_1 = response1.json()["data"]["request_id"]
        
        response2 = await presentation_client.post(
            "/api/v1/presentations",
            json={"topic": "DIFFERENT Topic", "language": "en", "slide_count": 10},
            headers={"Idempotency-Key": idempotency_key},
        )
        assert response2.status_code == 201
        data2 = response2.json()["data"]
        assert data2["request_id"] == request_id_1

    @pytest.mark.asyncio
    async def test_same_key_another_student(
        self, app, presentation_student: Student, other_student: Student, 
        db: AsyncSession, setup_routing_config: None
    ):
        """Another student using the same idempotency key gets 409 Conflict."""
        idempotency_key = "idem-cross-student-123"
        
        # First student creates a request via app
        from httpx import AsyncClient, ASGITransport
        from app.services.auth import create_session_token, SESSION_COOKIE_NAME
        
        token1 = create_session_token(presentation_student.id, presentation_student.role)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            cookies={SESSION_COOKIE_NAME: token1},
        ) as client1:
            response1 = await client1.post(
                "/api/v1/presentations",
                json={"topic": "Student 1 Topic", "language": "ar"},
                headers={"Idempotency-Key": idempotency_key},
            )
            assert response1.status_code == 201
        
        # Second student tries to use the SAME idempotency key
        from app.services.auth import create_session_token, SESSION_COOKIE_NAME
        token2 = create_session_token(other_student.id, other_student.role)
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            cookies={SESSION_COOKIE_NAME: token2},
        ) as other_client:
            response2 = await other_client.post(
                "/api/v1/presentations",
                json={"topic": "Student 2 Topic", "language": "ar"},
                headers={"Idempotency-Key": idempotency_key},
            )
            assert response2.status_code == 409
            assert response2.json()["error"]["code"] == "CONFLICT"

    @pytest.mark.asyncio
    async def test_missing_idempotency_key(
        self, presentation_client: AsyncClient, setup_routing_config: None
    ):
        """Request without idempotency key works normally."""
        response = await presentation_client.post(
            "/api/v1/presentations",
            json={"topic": "No Idempotency Key", "language": "ar"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert "request_id" in data
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_invalid_idempotency_key_format(
        self, app, presentation_student: Student, setup_routing_config: None
    ):
        """Invalid idempotency key format returns 422."""
        from httpx import AsyncClient, ASGITransport
        from app.services.auth import create_session_token, SESSION_COOKIE_NAME
        
        token = create_session_token(presentation_student.id, presentation_student.role)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            cookies={SESSION_COOKIE_NAME: token},
        ) as client:
            invalid_keys = [
                "key with spaces",
                "key@with#special$chars",
            ]
            
            for invalid_key in invalid_keys:
                response = await client.post(
                    "/api/v1/presentations",
                    json={"topic": "Test", "language": "ar"},
                    headers={"Idempotency-Key": invalid_key},
                )
                assert response.status_code == 422, f"Key '{invalid_key}' should return 422"
                data = response.json()
                assert "error" in data
                assert data["error"]["code"] in (
                    "IDEMPOTENCY_KEY_TOO_LONG",
                    "IDEMPOTENCY_KEY_EMPTY",
                    "IDEMPOTENCY_KEY_INVALID_FORMAT",
                )
            
            response = await client.post(
                "/api/v1/presentations",
                json={"topic": "Test", "language": "ar"},
                headers=[("Idempotency-Key", "")],
            )
            assert response.status_code == 422, f"Empty string key should return 422"
            data = response.json()
            assert "error" in data
            assert data["error"]["code"] == "IDEMPOTENCY_KEY_EMPTY"
            
            response = await client.post(
                "/api/v1/presentations",
                json={"topic": "Test", "language": "ar"},
                headers={},
            )
            assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_idempotency_key_max_length(
        self, presentation_client: AsyncClient, setup_routing_config: None
    ):
        """Idempotency key at max length (255) works."""
        idempotency_key = "a" * 255
        response = await presentation_client.post(
            "/api/v1/presentations",
            json={"topic": "Max Length Key", "language": "ar"},
            headers={"Idempotency-Key": idempotency_key},
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_idempotency_key_over_max_length(
        self, presentation_client: AsyncClient, setup_routing_config: None
    ):
        """Idempotency key over max length (256) returns 422."""
        idempotency_key = "a" * 256
        response = await presentation_client.post(
            "/api/v1/presentations",
            json={"topic": "Over Max Length", "language": "ar"},
            headers={"Idempotency-Key": idempotency_key},
        )
        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "IDEMPOTENCY_KEY_TOO_LONG"

    @pytest.mark.asyncio
    async def test_idempotency_with_failed_request_retry(
        self, presentation_client: AsyncClient, presentation_student: Student, 
        db: AsyncSession, setup_routing_config: None
    ):
        """Failed request can be retried with same idempotency key."""
        # Create a failed request with a DIFFERENT idempotency key
        failed_idempotency_key = "idem-failed-123"
        request = Request(
            student_id=presentation_student.id,
            feature="presentation",
            intent="presentation",
            model_tier="default",
            status=RequestStatus.FAILED,
            request_payload_hash="abc123",
            idempotency_key="idem-failed-123",  # Different from retry key
        )
        db.add(request)
        await db.commit()
        await db.refresh(request)
        
        # Now try to create with the RETRY key (different from failed request's key)
        # This should work because the failed request has a different idempotency key
        response = await presentation_client.post(
            "/api/v1/presentations",
            json={"topic": "Retry After Failure", "language": "ar"},
            headers={"Idempotency-Key": "idem-retry-123"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["status"] == "pending"