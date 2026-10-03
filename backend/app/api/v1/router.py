"""
app/api/v1/router.py
─────────────────────
Assembles all v1 API routes under /api/v1/.
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.presentations import router as presentations_router
from app.services.storage import LocalStorageService, get_storage_service

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(health_router)
api_v1_router.include_router(presentations_router)


@api_v1_router.get("/deliverables/download/{object_key:path}", include_in_schema=False)
async def download_local_object(object_key: str, token: str = Query(..., min_length=1)):
    """Serve only a short-lived, signed local-development download URL."""
    storage = get_storage_service()
    if not isinstance(storage, LocalStorageService):
        raise HTTPException(status_code=404, detail="Download endpoint unavailable")
    try:
        path = storage.resolve_signed_download(object_key, token)
    except (ValueError, FileNotFoundError):
        raise HTTPException(status_code=404, detail="Download link is invalid or expired")
    return FileResponse(path)

# Phase 2+ routes will be added here:
# from app.api.v1.routes.requests import router as requests_router
# from app.api.v1.routes.deliverables import router as deliverables_router
# from app.api.v1.routes.developer import router as developer_router
# from app.api.v1.routes.chat import router as chat_router
