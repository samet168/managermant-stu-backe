from fastapi import APIRouter
from app.api.auth import router as auth_router
from app.api.teacher import router as teacher_router
from app.api.student import router as student_router
from app.api.homework import router as homework_router
from app.api.integrations import router as integrations_router
from app.api.billing import router as billing_router
from app.api.notifications import router as notifications_router
from app.api.admin import router as admin_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(teacher_router)
api_router.include_router(student_router)
api_router.include_router(homework_router)
api_router.include_router(integrations_router)
api_router.include_router(billing_router)
api_router.include_router(notifications_router)

__all__ = ["api_router"]
