from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.auth.router import router as auth_router
from app.api_understanding.router import router as specs_router
from app.campaigns.router import router as campaigns_router
from app.findings.router import router as findings_router
from app.health_checks.router import router as health_checks_router
from app.projects.router import router as projects_router
from app.workspace.router import router as workspace_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(workspace_router)
api_router.include_router(specs_router)
api_router.include_router(health_checks_router)
api_router.include_router(campaigns_router)
api_router.include_router(findings_router)

health_router = APIRouter()


@health_router.get("/health/live")
def health_live() -> dict:
    return {"status": "alive"}


@health_router.get("/health/ready")
def health_ready() -> dict:
    try:
        from app.db.session import SessionLocal
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
        return {"status": "ready"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
