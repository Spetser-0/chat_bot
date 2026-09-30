with open('C:/Users/Dell/Desktop/spetser-ai/backend/tests/integration/test_presentation.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix test_invalid_idempotency_key_format
old = '''    @pytest.mark.asyncio
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
            )'''

new = '''    @pytest.mark.asyncio
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
                )'''

content = content.replace(old, new)

with open('C:/Users/Dell/Desktop/spetser-ai/backend/tests/integration/test_presentation.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed test_invalid_idempotency_key_format')