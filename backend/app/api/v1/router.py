"""
app/api/v1/router.py
─────────────────────
Assembles all v1 API routes under /api/v1/.
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.api.v1.routes.admin.analytics import router as admin_analytics_router
from app.api.v1.routes.admin.audit import router as admin_audit_router
from app.api.v1.routes.admin.metrics import router as admin_metrics_router
from app.api.v1.routes.admin.payments import router as admin_payments_router
from app.api.v1.routes.admin.providers import router as admin_providers_router
from app.api.v1.routes.admin.referrals import router as admin_referrals_router
from app.api.v1.routes.admin.users import router as admin_users_router
from app.api.v1.routes.admin.skills import router as admin_skills_router
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.chat import router as chat_router
from app.api.v1.routes.conversations import router as conversations_router
from app.api.v1.routes.credits import router as credits_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.payments import router as payments_router
from app.api.v1.routes.presentations import router as presentations_router
from app.api.v1.routes.referrals import router as referrals_router
from app.api.v1.routes.skills import router as skills_router
from app.api.v1.routes.webhooks import router as webhooks_router
from app.services.storage import LocalStorageService, get_storage_service

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(health_router)
api_v1_router.include_router(presentations_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(conversations_router)

# Admin endpoints share a stricter per-user rate limit (Phase 10, Lesson 10.2).
from fastapi import Depends as _Depends  # noqa: E402
from app.api.deps import rate_limit_admin as _rate_limit_admin  # noqa: E402

_admin_rl = [_Depends(_rate_limit_admin)]
api_v1_router.include_router(admin_skills_router, dependencies=_admin_rl)
api_v1_router.include_router(admin_providers_router, dependencies=_admin_rl)
api_v1_router.include_router(admin_referrals_router, dependencies=_admin_rl)
api_v1_router.include_router(admin_users_router, dependencies=_admin_rl)
api_v1_router.include_router(admin_payments_router, dependencies=_admin_rl)
api_v1_router.include_router(admin_analytics_router, dependencies=_admin_rl)
api_v1_router.include_router(admin_audit_router, dependencies=_admin_rl)
api_v1_router.include_router(admin_metrics_router, dependencies=_admin_rl)
api_v1_router.include_router(skills_router)
api_v1_router.include_router(credits_router)
api_v1_router.include_router(payments_router)
api_v1_router.include_router(referrals_router)
api_v1_router.include_router(webhooks_router)


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
