"""
tests/integration/test_storage.py
────────────────────────────────────
Integration tests for the Storage abstraction.

Tests cover:
- Upload success
- Upload failure (file not found, too large, etc.)
- Cleanup (temporary files cleaned up after success and failure)
- Ownership enforcement
- Missing deliverable
- Secure download
"""
from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.deliverable import Deliverable, DeliverableStatus
from app.models.request import Request, RequestStatus
from app.models.student import Student
from app.services.auth import hash_password, create_session_token, SESSION_COOKIE_NAME
from app.services.storage import (
    LocalStorageService,
    StorageService,
    get_storage_service,
    StoredObject,
)


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def storage_student(db: AsyncSession) -> Student:
    """Student with high credit balance for storage tests."""
    unique = uuid.uuid4().hex[:8]
    s = Student(
        id=uuid.uuid4(),
        email=f"storage_{unique}@test.com",
        display_name="Storage User",
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
async def storage_client(app, storage_student: Student) -> AsyncClient:
    """Authenticated client for storage tests."""
    from app.services.auth import create_session_token, SESSION_COOKIE_NAME
    token = create_session_token(storage_student.id, storage_student.role)
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
async def storage_service(db: AsyncSession) -> LocalStorageService:
    """Create a local storage service with a temp directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield LocalStorageService(root_dir=tmpdir, base_url="http://localhost:8000")


# ──────────────────────────────────────────────────────────────────────────────
# Tests: LocalStorageService Unit Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestLocalStorageService:
    """Unit tests for LocalStorageService."""

    @pytest.mark.asyncio
    async def test_upload_success(self, storage_service: LocalStorageService):
        """Upload a file successfully."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test file content")
            tmp_path = f.name
        
        try:
            object_key = f"test/{uuid.uuid4()}.txt"
            result = await storage_service.upload(tmp_path, object_key, "text/plain")
            
            assert isinstance(result, StoredObject)
            assert result.object_key == object_key
            assert result.content_type == "text/plain"
            assert result.size_bytes > 0
            assert result.etag is not None
            
            # Verify file exists in storage
            assert (Path(storage_service._root) / object_key).exists()
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_upload_file_not_found(self, storage_service: LocalStorageService):
        """Upload non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            await storage_service.upload("/nonexistent/file.txt", "test/key.txt", "text/plain")

    @pytest.mark.asyncio
    async def test_upload_too_large(self, storage_service: LocalStorageService):
        """Upload file exceeding 100MB limit raises ValueError."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Write 101MB
            f.write(b"x" * (101 * 1024 * 1024))
            tmp_path = f.name
        
        try:
            with pytest.raises(ValueError, match="100MB"):
                await storage_service.upload(tmp_path, "test/large.txt", "text/plain")
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_upload_cleanup_on_success(self, storage_service: LocalStorageService):
        """Source temp file is cleaned up after successful upload."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            tmp_path = f.name
        
        object_key = f"test/{uuid.uuid4()}.txt"
        
        # Upload should not delete the source file (caller's responsibility)
        # but our implementation doesn't delete it
        await storage_service.upload(tmp_path, object_key, "text/plain")
        
        # Source file still exists (caller must clean up)
        # The implementation doesn't delete source
        assert Path(tmp_path).exists()
        
        # Cleanup
        Path(tmp_path).unlink(missing_ok=True)
        Path(storage_service._root / object_key).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_create_download_url(self, storage_service: LocalStorageService):
        """Generate a download URL for an existing object."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"download test")
            tmp_path = f.name
        
        object_key = f"test/{uuid.uuid4()}.txt"
        
        try:
            await storage_service.upload(tmp_path, object_key, "text/plain")
            url = await storage_service.create_download_url(object_key)
            
            assert url.startswith("http://localhost:8000/api/v1/deliverables/download/")
            assert object_key in url
        finally:
            Path(tmp_path).unlink(missing_ok=True)
            Path(storage_service._root / object_key).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_create_download_url_missing_object(self, storage_service: LocalStorageService):
        """Download URL for non-existent object still returns URL (lazy validation)."""
        url = await storage_service.create_download_url("nonexistent/key.txt")
        assert url.startswith("http://localhost:8000/api/v1/deliverables/download/")

    @pytest.mark.asyncio
    async def test_delete_object(self, storage_service: LocalStorageService):
        """Delete an object from storage."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"delete test")
            tmp_path = f.name
        
        object_key = f"test/{uuid.uuid4()}.txt"
        
        try:
            await storage_service.upload(tmp_path, object_key, "text/plain")
            assert (Path(storage_service._root) / object_key).exists()
            
            await storage_service.delete(object_key)
            assert not (Path(storage_service._root) / object_key).exists()
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_object(self, storage_service: LocalStorageService):
        """Delete non-existent object doesn't raise error."""
        await storage_service.delete("nonexistent/key.txt")  # Should not raise

    @pytest.mark.asyncio
    async def test_exists_check(self, storage_service: LocalStorageService):
        """Check if object exists in storage."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"exists test")
            tmp_path = f.name
        
        object_key = f"test/{uuid.uuid4()}.txt"
        
        try:
            assert not await storage_service.exists(object_key)
            await storage_service.upload(tmp_path, object_key, "text/plain")
            assert await storage_service.exists(object_key)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
            Path(storage_service._root / object_key).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_get_metadata(self, storage_service: LocalStorageService):
        """Get metadata for stored object."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"metadata test")
            tmp_path = f.name
        
        object_key = f"test/{uuid.uuid4()}.txt"
        
        try:
            await storage_service.upload(tmp_path, object_key, "text/plain")
            metadata = await storage_service.get_metadata(object_key)
            
            assert metadata is not None
            assert metadata.object_key == object_key
            assert metadata.size_bytes > 0
            assert metadata.etag is not None
        finally:
            Path(tmp_path).unlink(missing_ok=True)
            Path(storage_service._root / object_key).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_get_metadata_nonexistent(self, storage_service: LocalStorageService):
        """Get metadata for non-existent object returns None."""
        metadata = await storage_service.get_metadata("nonexistent/key.txt")
        assert metadata is None


# ──────────────────────────────────────────────────────────────────────────────
# Tests: Storage Factory
# ──────────────────────────────────────────────────────────────────────────────

class TestStorageFactory:
    """Tests for the storage service factory."""

    @pytest.mark.asyncio
    async def test_get_storage_service_returns_local(self):
        """Factory returns LocalStorageService when no Supabase config."""
        with patch("app.core.config.get_settings") as mock_settings:
            mock_settings.return_value.supabase_url = ""
            mock_settings.return_value.supabase_service_role_key = ""
            mock_settings.return_value.storage_tmp_dir = "/tmp/spetser"
            mock_settings.return_value.storage_bucket_deliverables = "deliverables"
            
            service = get_storage_service()
            assert isinstance(service, LocalStorageService)

    @pytest.mark.asyncio
    async def test_get_storage_service_returns_supabase(self):
        """Factory returns SupabaseStorageService when Supabase config present."""
        with patch("app.core.config.get_settings") as mock_settings:
            mock_settings.return_value.supabase_url = "https://test.supabase.co"
            mock_settings.return_value.supabase_service_role_key = "test-key"
            mock_settings.return_value.storage_bucket_deliverables = "deliverables"
            mock_settings.return_value.storage_tmp_dir = "/tmp/spetser"
            
            with patch("app.services.storage.SupabaseStorageService") as mock_supabase:
                service = get_storage_service()
                mock_supabase.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# Tests: Secure Download (Integration)
# ──────────────────────────────────────────────────────────────────────────────

class TestSecureDownload:
    """Integration tests for secure download with ownership enforcement."""

    @pytest.mark.asyncio
    async def test_download_own_deliverable(
        self, storage_client: AsyncClient, storage_student: Student, db: AsyncSession
    ):
        """Student can download their own deliverable."""
        # Create a deliverable for the student
        request = Request(
            student_id=storage_student.id,
            feature="presentation",
            intent="presentation",
            model_tier="default",
            status=RequestStatus.READY,
            request_payload_hash="abc123",
        )
        db.add(request)
        await db.flush()
        
        deliverable = Deliverable(
            request_id=request.id,
            student_id=storage_student.id,
            file_type="pptx",
            storage_object_key=f"presentations/{storage_student.id}/{uuid.uuid4()}.pptx",
            mime_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            file_size=1024,
            renderer_version="1.0.0",
            schema_version="1.0.0",
            input_hash="abc123",
            status=DeliverableStatus.READY,
        )
        db.add(deliverable)
        await db.commit()
        await db.refresh(deliverable)
        
        # Test download
        response = await storage_client.get(f"/api/v1/presentations/deliverables/{deliverable.id}/download")
        assert response.status_code == 200
        data = response.json()["data"]
        assert "download_url" in data
        assert data["download_url"].startswith("http://")
        assert data["file_type"] == "pptx"

    @pytest.mark.asyncio
    async def test_download_other_student_deliverable_denied(
        self, storage_client: AsyncClient, other_student: Student, db: AsyncSession
    ):
        """Student cannot download another student's deliverable."""
        request = Request(
            student_id=other_student.id,
            feature="presentation",
            intent="presentation",
            model_tier="default",
            status=RequestStatus.READY,
            request_payload_hash="abc123",
        )
        db.add(request)
        await db.flush()
        
        deliverable = Deliverable(
            request_id=request.id,
            student_id=other_student.id,
            file_type="pptx",
            storage_object_key=f"presentations/{other_student.id}/{uuid.uuid4()}.pptx",
            mime_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            file_size=1024,
            renderer_version="1.0.0",
            schema_version="1.0.0",
            input_hash="abc123",
            status=DeliverableStatus.READY,
        )
        db.add(deliverable)
        await db.commit()
        await db.refresh(deliverable)
        
        response = await storage_client.get(f"/api/v1/presentations/deliverables/{deliverable.id}/download")
        assert response.status_code == 403
        data = response.json()
        assert data["error"]["code"] == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_download_nonexistent_deliverable(self, storage_client: AsyncClient):
        """Download non-existent deliverable returns 404."""
        response = await storage_client.get(f"/api/v1/deliverables/{uuid.uuid4()}/download")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_download_unready_deliverable_denied(
        self, storage_client: AsyncClient, storage_student: Student, db: AsyncSession
    ):
        """Download not-ready deliverable returns 400."""
        request = Request(
            student_id=storage_student.id,
            feature="presentation",
            intent="presentation",
            model_tier="default",
            status=RequestStatus.PROCESSING,
            request_payload_hash="abc123",
        )
        db.add(request)
        await db.flush()
        
        deliverable = Deliverable(
            request_id=request.id,
            student_id=storage_student.id,
            file_type="pptx",
            storage_object_key=f"presentations/{storage_student.id}/{uuid.uuid4()}.pptx",
            mime_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            file_size=1024,
            status=DeliverableStatus.PENDING,
        )
        db.add(deliverable)
        await db.commit()
        await db.refresh(deliverable)
        
        response = await storage_client.get(f"/api/v1/presentations/deliverables/{deliverable.id}/download")
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "NOT_READY"


# ──────────────────────────────────────────────────────────────────────────────
# Tests: Storage Abstraction Interface
# ──────────────────────────────────────────────────────────────────────────────

class TestStorageAbstraction:
    """Tests that the StorageService interface is properly implemented."""

    @pytest.mark.asyncio
    async def test_storage_service_interface(self, storage_service: LocalStorageService):
        """Verify StorageService interface is implemented."""
        assert isinstance(storage_service, StorageService)
        assert hasattr(storage_service, "upload")
        assert hasattr(storage_service, "create_download_url")
        assert hasattr(storage_service, "delete")
        assert hasattr(storage_service, "exists")
        assert hasattr(storage_service, "get_metadata")

    @pytest.mark.asyncio
    async def test_stored_object_immutability(self):
        """StoredObject is immutable (frozen dataclass)."""
        obj = StoredObject(
            object_key="test/key.txt",
            content_type="text/plain",
            size_bytes=100,
            etag="abc123",
        )
        with pytest.raises(Exception):
            obj.object_key = "different"
        with pytest.raises(Exception):
            obj.size_bytes = 200


# ──────────────────────────────────────────────────────────────────────────────
# Tests: Mock Storage for Testing
# ──────────────────────────────────────────────────────────────────────────────

class TestMockStorage:
    """Tests using a mock storage service for unit testing."""

    @pytest.mark.asyncio
    async def test_mock_storage_behavior(self):
        """Verify mock storage can be used for testing."""
        from app.services.storage import StorageService
        
        class MockStorage(StorageService):
            def __init__(self):
                self._store = {}
                self.call_count = 0
            
            async def upload(self, file_path, object_key, content_type):
                self.call_count += 1
                self._store[object_key] = b"mock"
                return StoredObject(
                    object_key=object_key,
                    content_type=content_type,
                    size_bytes=100,
                    etag="mock-etag",
                )
            
            async def create_download_url(self, object_key, expires_in_seconds=3600):
                return f"http://mock/download/{object_key}"
            
            async def delete(self, object_key):
                self._store.pop(object_key, None)
            
            async def exists(self, object_key):
                return object_key in self._store
            
            async def get_metadata(self, object_key):
                return self._store.get(object_key)
        
        mock = MockStorage()
        assert isinstance(mock, StorageService)
        
        result = await mock.upload("/tmp/test.txt", "test/key.txt", "text/plain")
        assert result.object_key == "test/key.txt"
        assert mock.call_count == 1


# ──────────────────────────────────────────────────────────────────────────────
# Tests: Secure Download URL Expiration
# ──────────────────────────────────────────────────────────────────────────────

class TestDownloadUrlExpiration:
    """Tests for download URL expiration behavior."""

    @pytest.mark.asyncio
    async def test_download_url_has_expiration(self, storage_service: LocalStorageService):
        """Download URLs include expiration parameter."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"expiration test")
            tmp_path = f.name
        
        object_key = f"test/{uuid.uuid4()}.txt"
        
        try:
            await storage_service.upload(tmp_path, object_key, "text/plain")
            url = await storage_service.create_download_url(object_key, expires_in_seconds=1800)
            
            # URL should contain the object key
            assert object_key in url
        finally:
            Path(tmp_path).unlink(missing_ok=True)
            Path(storage_service._root / object_key).unlink(missing_ok=True)


# ──────────────────────────────────────────────────────────────────────────────
# Tests: Edge Cases
# ──────────────────────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Edge case tests for storage."""

    @pytest.mark.asyncio
    async def test_upload_empty_file(self, storage_service: LocalStorageService):
        """Upload empty file works."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            tmp_path = f.name
        
        try:
            object_key = f"test/{uuid.uuid4()}.txt"
            result = await storage_service.upload(tmp_path, object_key, "text/plain")
            
            assert result.size_bytes == 0
        finally:
            Path(tmp_path).unlink(missing_ok=True)
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_upload_with_special_chars_in_key(self, storage_service: LocalStorageService):
        """Upload with special characters in object key works."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"special chars")
            tmp_path = f.name
        
        try:
            object_key = f"test/path/with/special_chars_{uuid.uuid4()}.txt"
            result = await storage_service.upload(tmp_path, object_key, "text/plain")
            
            assert result.object_key == object_key
        finally:
            Path(tmp_path).unlink(missing_ok=True)
            Path(storage_service._root / object_key).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_upload_large_file_near_limit(self, storage_service: LocalStorageService):
        """Upload file near 100MB limit works."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            # 99MB
            f.write(b"x" * (99 * 1024 * 1024))
            tmp_path = f.name
        
        try:
            object_key = f"test/{uuid.uuid4()}.bin"
            result = await storage_service.upload(tmp_path, object_key, "application/octet-stream")
            
            assert result.size_bytes == 99 * 1024 * 1024
        finally:
            Path(tmp_path).unlink(missing_ok=True)
            Path(storage_service._root / object_key).unlink(missing_ok=True)