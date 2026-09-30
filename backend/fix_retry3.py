with open('C:/Users/Dell/Desktop/spetser-ai/backend/tests/integration/test_presentation.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix test_idempotency_with_failed_request_retry
old = '''    @pytest.mark.asyncio
    async def test_idempotency_with_failed_request_retry(
        self, presentation_client: AsyncClient, presentation_student: Student, 
        db: AsyncSession, setup_routing_config: None
    ):
        """Failed request can be retried with same idempotency key."""
        idempotency_key = "idem-retry-123"
        
        # Create a failed request with a DIFFERENT idempotency key
        # The retry should use the SAME idempotency key as the failed request
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
            headers={"Idempotency-Key": idempotency_key},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["status"] == "pending"'''

new = '''    @pytest.mark.asyncio
    async def test_idempotency_with_failed_request_retry(
        self, presentation_client: AsyncClient, presentation_student: Student, 
        db: AsyncSession, setup_routing_config: None
    ):
        """Failed request can be retried with same idempotency key."""
        idempotency_key = "idem-retry-123"
        
        # Create a failed request with the SAME idempotency key
        request = Request(
            student_id=presentation_student.id,
            feature="presentation",
            intent="presentation",
            model_tier="default",
            status=RequestStatus.FAILED,
            request_payload_hash="abc123",
            idempotency_key=idempotency_key,  # Same key as retry
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
        assert data["status"] == "pending"'''

content = content.replace(old, new)

with open('C:/Users/Dell/Desktop/spetser-ai/backend/tests/integration/test_presentation.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed test_idempotency_with_failed_request_retry')