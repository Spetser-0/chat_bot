import re

with open('C:/Users/Dell/Desktop/spetser-ai/backend/tests/integration/test_idempotency.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the invalid_keys list and the empty string test
old = '''            invalid_keys = [
                "key with spaces",
                "key@with#special$chars",
                "",
                "a" * 256,
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
            assert response.status_code == 201'''

new = '''            invalid_keys = [
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
        response = await client.post(
                "/api/v1/presentations",
                json={"topic": "Test", "language": "ar"},
                headers={"Idempotency-Key": "a" * 256},
            )
            assert response.status_code == 422, f"Key 'a' * 256 should return 422"
            data = response.json()
            assert data["error"]["code"] == "IDEMPOTENCY_KEY_TOO_LONG"'''

content = content.replace(
    '''            invalid_keys = [
                "key with spaces",
                "key@with#special$chars",
                "",
                "a" * 256,
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
            assert response.status_code == 201''',
    '''            invalid_keys = [
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
        response = await client.post(
                "/api/v1/presentations",
                json={"topic": "Test", "language": "ar"},
                headers={"Idempotency-Key": "a" * 256},
            )
            assert response.status_code == 422, f"Key 'a' * 256 should return 422"
            data = response.json()
            assert data["error"]["code"] == "IDEMPOTENCY_KEY_TOO_LONG"''',
    content)

with open('C:/Users/Dell/Desktop/spetser-ai/backend/tests/integration/test_idempotency.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed!')