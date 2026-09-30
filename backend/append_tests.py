# Add idempotency tests to test_presentation.py
with open('C:/Users/Dell/Desktop/spetser-ai/backend/tests/integration/test_presentation.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Check if tests already exist
if 'class TestIdempotency:' in content:
    print('Tests already exist')
else:
    new_tests = '''

# ──────────────────────────────────────────────────────────────────────────────
# Tests: Idempotency
# ──────────────────────────────────────────────────────────────────────────────

class TestIdempotency:
    """Comprehensive tests for Idempotency-Key header."""

    @pytest.mark.asyncio
    async def test_same_key_after_success(
        self, presentation_client: AsyncClient, setup_routing_config: None
    ):
        """Same idempotency key after success returns existing request."""
        idempotency_key = "idem-success-123"
        
        # First request
        response1 = await presentation_client.post(
            "/api/v1/presentations",
            json={"topic": "Test Success", "language": "ar"},
            headers={"Idempotency-Key": idempotency_key},
        )
        assert response1.status_code == 201
        data1 = response1.json()["data"]
        request_id_1 = data1["request_id"]
        
        # Second request with same key - should return existing
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
        
        # First request
        response1 = await presentation_client.post(
            "/api/v1/presentations",
            json={"topic": "Test Processing", "language": "ar"},
            headers={"Idempotency-Key": idempotency_key},
        )
        assert response1.status_code == 201
        data1 = response1.json()["data"]
        request_id_1 = data1["request_id"]
        
        # Second request with same key while first is pending
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
        
        # First request
        response1 = await presentation_client.post(
            "/api/v1/presentations",
            json={"topic": "Original Topic", "language": "ar", "slide_count": 5},
            headers={"Idempotency-Key": idempotency_key},
        )
        assert response1.status_code == 201
        request_id_1 = response1.json()["data"]["request_id"]
        
        # Second request with SAME key but DIFFERENT payload
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
        self, presentation_client: AsyncClient, other_student: Student, 
        db: AsyncSession, setup_routing_config: None
    ):
        """Another student using the same idempotency key gets 409 Conflict."""
        idempotency_key = "idem-cross-student-123"
        
        # First student creates a request
        response1 = await presentation_client.post(
            "/api/v1/presentations",
            json={"topic": "Student 1 Topic", "language": "ar"},
            headers={"Idempotency-Key": idempotency_key},
        )
        assert response1.status_code == 201
        
        # Second student tries to use the SAME idempotency key
        from app.services.auth import create_session_token, SESSION_COOKIE_NAME
        token = create_session_token(other_student.id, other_student.role)
        
        async with AsyncClient(
            transport=ASGITransport(app=presentation_client.app),
            base_url="http://test",
            cookies={SESSION_COOKIE_NAME: token},
        ) as other_client:
            response2 = await other_client.post(
                "/api/v1/presentations",
                json={"topic": "Student 2 Topic", "language": "ar"},
                headers={"Idempotency-Key": idempotency_key},
            )
            assert response2.status_code == 409
            data2 = response2.json()
            assert data2["error"]["code"] == "CONFLICT"

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
        self, presentation_client: AsyncClient, setup_routing_config: None
    ):
        """Invalid idempotency key format returns 422."""
        invalid_keys = [
            "key with spaces",
            "key@with#special$chars",
            "",
            "a" * 256,
        ]
        
        for invalid_key in invalid_keys:
            response = await presentation_client.post(
                "/api/v1/presentations",
                json={"topic": "Test", "language": "ar"},
                headers={"Idempotency-Key": invalid_key} if invalid_key != "" else {},
            )
            assert response.status_code == 422, f"Key '{invalid_key}' should return 422"
            data = response.json()
            assert "error" in data
            assert data["error"]["code"] in (
                "IDEMPOTENCY_KEY_TOO_LONG",
                "IDEMPOTENCY_KEY_EMPTY",
                "IDEMPOTENCY_KEY_INVALID_FORMAT",
            )

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
        self, presentation_client: AsyncClient, setup_routing_config: None,
        presentation_student: Student, db: AsyncSession
    ):
        """Failed request can be retried with same idempotency key."""
        idempotency_key = "idem-retry-123"
        
        # Create a failed request directly in DB
        request = Request(
            student_id=presentation_student.id,
            feature="presentation",
            intent="presentation",
            model_tier="default",
            status=RequestStatus.FAILED,
            request_payload_hash="abc123",
            idempotency_key=idempotency_key,
        )
        db.add(request)
        await db.commit()
        await db.refresh(request)
        
        # Now try to create with same idempotency key - should succeed (retry)
        response = await presentation_client.post(
            "/api/v1/presentations",
            json={"topic": "Retry After Failure", "language": "ar"},
            headers={"Idempotency-Key": idempotency_key},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["status"] == "pending"

# Read current file
with open('C:/Users/Dell/Desktop/spetser-ai/backend/tests/integration/test_presentation.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Check if tests already exist
if 'class TestIdempotency:' in content:
    print('Tests already exist')
else:
    # Find the end of the file and append tests
    # Find the end of the TestPresentationAPI class
    marker = 'async def test_unauthorized_access_denied'
    idx = content.rfind(marker)
    if idx != -1:
        # Find the end of that test method
        idx2 = content.find('\n\n', idx)
        if idx2 != -1:
            content = content[:idx2+2] + new_tests
            with open('C:/Users/Dell/Desktop/spetser-ai/backend/tests/integration/test_presentation.py', 'w', encoding='utf-8') as f:
                f.write(content)
            print('Tests appended successfully!')
        else:
            print('Could not find end of test method')
    else:
        print('Could not find test_unauthorized_access_denied')