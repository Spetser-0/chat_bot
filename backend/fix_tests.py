# Fix tests in test_presentation.py
with open('C:/Users/Dell/Desktop/spetser-ai/backend/tests/integration/test_presentation.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix test_same_key_another_student - use app fixture instead of presentation_client.app
content = content.replace(
'''    @pytest.mark.asyncio
    async def test_same_key_another_student(
        self, presentation_client: AsyncClient, other_student: Student, 
        db: AsyncSession, setup_routing_config: None
    ):
        """Another student using the same idempotency key gets 409 Conflict."""
        idempotency_key = "idem-cross-student-123"
        
        response1 = await presentation_client.post(
            "/api/v1/presentations",
            json={"topic": "Student 1 Topic", "language": "ar"},
            headers={"Idempotency-Key": idempotency_key},
        )
        assert response1.status_code == 201
        
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
            assert response2.json()["error"]["code"] == "CONFLICT"''',
'''    @pytest.mark.asyncio
    async def test_same_key_another_student(
        self, app, other_student: Student, 
        db: AsyncSession, setup_routing_config: None
    ):
        """Another student using the same idempotency key gets 409 Conflict."""
        idempotency_key = "idem-cross-student-123"
        
        # First student creates a request via app
        from httpx import AsyncClient, ASGITransport
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client1:
            response1 = await client1.post(
                "/api/v1/presentations",
                json={"topic": "Student 1 Topic", "language": "ar"},
                headers={"Idempotency-Key": idempotency_key},
            )
            assert response1.status_code == 201
        
        # Second student tries to use the SAME idempotency key
        from app.services.auth import create_session_token, SESSION_COOKIE_NAME
        token = create_session_token(other_student.id, other_student.role)
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            cookies={SESSION_COOKIE_NAME: token},
        ) as other_client:
            response2 = await other_client.post(
                "/api/v1/presentations",
                json={"topic": "Student 2 Topic", "language": "ar"},
                headers={"Idempotency-Key": idempotency_key},
            )
            assert response2.status_code == 409
            assert response2.json()["error"]["code"] == "CONFLICT"''',
content)

# Fix test_invalid_idempotency_key_format - use correct fixture
content = content.replace(
'''    @pytest.mark.asyncio
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
            )''',
'''    @pytest.mark.asyncio
    async def test_invalid_idempotency_key_format(
        self, app, setup_routing_config: None
    ):
        """Invalid idempotency key format returns 422."""
        invalid_keys = [
            "key with spaces",
            "key@with#special$chars",
            "",
            "a" * 256,
        ]
        
        from httpx import AsyncClient, ASGITransport
        for invalid_key in invalid_keys:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
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
                )''',
content)

# Fix test_idempotency_with_failed_request_retry - use different idempotency key for new request
content = content.replace(
'''    @pytest.mark.asyncio
    async def test_idempotency_with_failed_request_retry(
        self, presentation_client: AsyncClient, setup_routing_config: None,
        presentation_student: Student, db: AsyncSession
    ):
        """Failed request can be retried with same idempotency key."""
        idempotency_key = "idem-retry-123"
        
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
        
        response = await presentation_client.post(
            "/api/v1/presentations",
            json={"topic": "Retry After Failure", "language": "ar"},
            headers={"Idempotency-Key": idempotency_key},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["status"] == "pending"''',
'''    @pytest.mark.asyncio
    async def test_idempotency_with_failed_request_retry(
        self, app, presentation_student: Student, db: AsyncSession, setup_routing_config: None
    ):
        """Failed request can be retried with same idempotency key."""
        idempotency_key = "idem-retry-123"
        
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
        
        # Use app fixture to create new client (since presentation_client has the session)
        from httpx import AsyncClient, ASGITransport
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/presentations",
                json={"topic": "Retry After Failure", "language": "ar"},
                headers={"Idempotency-Key": idempotency_key},
            )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["status"] == "pending"''',
content)

with open('C:/Users/Dell/Desktop/spetser-ai/backend/tests/integration/test_presentation.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Tests fixed!')