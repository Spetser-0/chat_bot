"""
app/services/storage.py
──────────────────────────
Storage abstraction for deliverable files.

Provides a clean interface for uploading, downloading, and deleting
generated files (PPTX, PDF, etc.) with support for multiple backends.

Key rules:
- Never expose local filesystem paths
- Use UUID-based object keys
- Generate short-lived signed download URLs
- Validate before upload
- Clean up temp files automatically
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from uuid import UUID


@dataclass(frozen=True)
class StoredObject:
    """Metadata for a stored object."""
    object_key: str
    content_type: str
    size_bytes: int
    etag: str | None = None


class StorageService(ABC):
    """
    Abstract storage interface for deliverable files.
    
    Implementations must:
    - Use UUID-based object keys (never user-provided filenames)
    - Validate content before upload
    - Generate signed download URLs with expiration
    - Clean up temporary files
    """
    
    @abstractmethod
    async def upload(
        self,
        file_path: Path | str,
        object_key: str,
        content_type: str,
    ) -> StoredObject:
        """
        Upload a file to storage.
        
        Args:
            file_path: Local path to file (will be cleaned up after)
            object_key: Server-generated UUID-based key
            content_type: MIME type
            
        Returns:
            StoredObject with metadata
        """
        ...

    @abstractmethod
    async def create_download_url(
        self,
        object_key: str,
        expires_in_seconds: int = 3600,
    ) -> str:
        """
        Generate a signed download URL.
        
        Args:
            object_key: Storage object key
            expires_in_seconds: URL validity period
            
        Returns:
            Signed URL string
        """
        ...

    @abstractmethod
    async def delete(self, object_key: str) -> None:
        """Delete an object from storage."""
        ...

    @abstractmethod
    async def exists(self, object_key: str) -> bool:
        """Check if object exists."""
        ...

    @abstractmethod
    async def get_metadata(self, object_key: str) -> StoredObject | None:
        """Get object metadata without downloading."""
        ...


# ──────────────────────────────────────────────────────────────────────────────
# Local Filesystem Implementation (for development/tests)
# ──────────────────────────────────────────────────────────────────────────────

import os
import shutil
import hashlib
from datetime import datetime, timedelta
from urllib.parse import urljoin


class LocalStorageService(StorageService):
    """
    Local filesystem storage for development and testing.
    
    Stores files under a configured root directory with UUID-based names.
    Generates file:// URLs for download (works in local dev).
    """
    
    def __init__(self, root_dir: str, base_url: str = "http://localhost:8000") -> None:
        self._root = Path(root_dir).resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._base_url = base_url.rstrip("/")
    
    async def upload(
        self,
        file_path: Path | str,
        object_key: str,
        content_type: str,
    ) -> StoredObject:
        src = Path(file_path)
        if not src.exists():
            raise FileNotFoundError(f"Source file not found: {src}")
        
        # Validate file size (max 100MB)
        size = src.stat().st_size
        if size > 100 * 1024 * 1024:
            raise ValueError("File exceeds 100MB limit")
        
        # Copy to storage with UUID-based name
        dest = self._root / object_key
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        
        # Calculate ETag (MD5 for simplicity)
        with open(dest, "rb") as f:
            etag = hashlib.md5(f.read()).hexdigest()
        
        return StoredObject(
            object_key=object_key,
            content_type=content_type,
            size_bytes=size,
            etag=etag,
        )
    
    async def create_download_url(
        self,
        object_key: str,
        expires_in_seconds: int = 3600,
    ) -> str:
        # In local dev, return a direct URL to the file
        # In production, this would be a signed URL (Supabase, S3, etc.)
        return f"{self._base_url}/api/v1/deliverables/download/{object_key}"
    
    async def delete(self, object_key: str) -> None:
        dest = self._root / object_key
        if dest.exists():
            dest.unlink()
    
    async def exists(self, object_key: str) -> bool:
        return (self._root / object_key).exists()
    
    async def get_metadata(self, object_key: str) -> StoredObject | None:
        dest = self._root / object_key
        if not dest.exists():
            return None
        
        stat = dest.stat()
        with open(dest, "rb") as f:
            etag = hashlib.md5(f.read()).hexdigest()
        
        return StoredObject(
            object_key=object_key,
            content_type="application/octet-stream",  # Would be stored in metadata
            size_bytes=stat.st_size,
            etag=etag,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Supabase Storage Implementation (production)
# ──────────────────────────────────────────────────────────────────────────────

class SupabaseStorageService(StorageService):
    """
    Supabase Storage implementation for production.
    
    Requires:
    - SUPABASE_URL
    - SUPABASE_SERVICE_ROLE_KEY
    - Storage bucket created in Supabase
    """
    
    def __init__(
        self,
        supabase_url: str,
        service_role_key: str,
        bucket: str,
        base_url: str = "",
    ) -> None:
        self._supabase_url = supabase_url.rstrip("/")
        self._service_key = service_role_key
        self._bucket = bucket
        self._base_url = base_url or supabase_url
        self._client = None
    
    def _get_client(self):
        """Lazy-initialize Supabase client."""
        if self._client is None:
            from supabase import create_client
            self._client = create_client(self._supabase_url, self._service_key)
        return self._client
    
    async def upload(
        self,
        file_path: Path | str,
        object_key: str,
        content_type: str,
    ) -> StoredObject:
        client = self._get_client()
        src = Path(file_path)
        
        if not src.exists():
            raise FileNotFoundError(f"Source file not found: {src}")
        
        size = src.stat().st_size
        if size > 100 * 1024 * 1024:
            raise ValueError("File exceeds 100MB limit")
        
        with open(src, "rb") as f:
            data = f.read()
        
        # Upload to Supabase Storage
        response = self._client.storage.from_(self._bucket).upload(
            path=object_key,
            file=data,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        
        if hasattr(response, "error") and response.error:
            raise RuntimeError(f"Supabase upload failed: {response.error}")
        
        etag = hashlib.md5(data).hexdigest()
        
        return StoredObject(
            object_key=object_key,
            content_type=content_type,
            size_bytes=size,
            etag=etag,
        )
    
    async def create_download_url(
        self,
        object_key: str,
        expires_in_seconds: int = 3600,
    ) -> str:
        client = self._get_client()
        
        response = self._client.storage.from_(self._bucket).create_signed_url(
            object_key, expires_in_seconds
        )
        
        if hasattr(response, "error") and response.error:
            raise RuntimeError(f"Signed URL creation failed: {response.error}")
        
        return response["signedURL"]
    
    async def delete(self, object_key: str) -> None:
        client = self._get_client()
        response = self._client.storage.from_(self._bucket).remove([object_key])
        if hasattr(response, "error") and response.error:
            raise RuntimeError(f"Delete failed: {response.error}")
    
    async def exists(self, object_key: str) -> bool:
        client = self._get_client()
        try:
            response = self._client.storage.from_(self._bucket).list(
                path=os.path.dirname(object_key) or ""
            )
            files = [f["name"] for f in response] if isinstance(response, list) else []
            return os.path.basename(object_key) in files
        except Exception:
            return False
    
    async def get_metadata(self, object_key: str) -> StoredObject | None:
        client = self._get_client()
        try:
            # Supabase doesn't have a direct metadata API for single file
            # Would need to list and find
            return None
        except Exception:
            return None


# ──────────────────────────────────────────────────────────────────────────────
# Factory
# ──────────────────────────────────────────────────────────────────────────────

def get_storage_service() -> StorageService:
    """
    Factory returning the configured StorageService implementation.
    
    Uses SupabaseStorageService if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
    are configured, otherwise falls back to LocalStorageService.
    """
    from app.core.config import get_settings
    
    settings = get_settings()
    
    if settings.supabase_url and settings.supabase_service_role_key:
        return SupabaseStorageService(
            supabase_url=settings.supabase_url,
            service_role_key=settings.supabase_service_role_key,
            bucket=settings.storage_bucket_deliverables,
        )
    
    # Development fallback
    return LocalStorageService(
        root_dir=settings.storage_tmp_dir,
        base_url="http://localhost:8000",
    )