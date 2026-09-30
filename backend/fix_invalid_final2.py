with open('C:/Users/Dell/Desktop/spetser-ai/backend/tests/integration/test_presentation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the test_invalid_idempotency_key_format function and fix it
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    if 'async def test_invalid_idempotency_key_format(' in line:
        # Found the function, replace from here to the end of the function
        new_lines.append(line)
        i += 1
        # Skip until we find the end of the function (next async def or class)
        while i < len(lines):
            if lines[i].strip().startswith('async def test_') or lines[i].strip().startswith('class '):
                break
            i += 1
        # Insert the new test code
        new_lines.append('''    @pytest.mark.asyncio
    async def test_invalid_idempotency_key_format(
        self, app, presentation_student: Student, setup_routing_config: None
    ):
        """Invalid idempotency key format returns 422."""
        from httpx import AsyncClient, ASGITransport
        from app.services.auth import create_session_token, SESSION_COOKIE_NAME
        
        # Create authenticated client
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
            
            # Test empty string separately - send header as empty string explicitly
            # Use headers list to ensure empty header is sent
            response = await client.post(
                "/api/v1/presentations",
                json={"topic": "Test", "language": "ar"},
                headers=[("Idempotency-Key", "")],
            )
            assert response.status_code == 422, f"Empty string key should return 422"
            data = response.json()
            assert "error" in data
            assert data["error"]["code"] == "IDEMPOTENCY_KEY_EMPTY"
            
            # Test missing header (None)
            response = await client.post(
                "/api/v1/presentations",
                json={"topic": "Test", "language": "ar"},
                headers={},
            )
            # Missing header should work (no idempotency key)
            assert response.status_code == 201

''')
        # Skip to the next function/class
        while i < len(lines) and not (lines[i].strip().startswith('async def test_') or lines[i].strip().startswith('class ')):
            i += 1
        continue
    new_lines.append(line)
    i += 1

with open('C:/Users/Dell/Desktop/spetser-ai/backend/tests/integration/test_presentation.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('Fixed test_invalid_idempotency_key_format')