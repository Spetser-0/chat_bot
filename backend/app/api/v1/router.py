"""
app/api/v1/router.py
─────────────────────
Assembles all v1 API routes under /api/v1/.
"""
from fastapi import APIRouter

from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.health import router as health_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(health_router)

# Phase 2+ routes will be added here:
# from app.api.v1.routes.presentations import router as presentations_router
# from app.api.v1.routes.requests import router as requests_router
# from app.api.v1.routes.deliverables import router as deliverables_router
# from app.api.v1.routes.developer import router as developer_router
# from app.api.v1.routes.chat import router as chat_router
