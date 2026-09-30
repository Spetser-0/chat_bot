with open('C:/Users/Dell/Desktop/spetser-ai/backend/tests/integration/test_idempotency.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix test_same_key_another_student
old = '''    @pytest.mark.asyncio
    async def test_same_key_another_student(
        self, presentation_client: AsyncClient, other_student: Student, 
        setup_routing_config: None
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
        from httpx import AsyncClient, ASGITransport
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
            assert response2.json()["error"]["code"] == "CONFLICT"'''

new = '''    @pytest.mark.asyncio
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
            assert response2.json()["error"]["code"] == "CONFLICT"'''

content = content.replace(old, new)

with open('C:/Users/Dell/Desktop/spetser-ai/backend/tests/integration/test_idempotency.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed test_same_key_another_student')