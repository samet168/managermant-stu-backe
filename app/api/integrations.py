from fastapi import APIRouter, UploadFile, File, Depends
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.domain.models import User
from app.domain.cloudinary_service import upload_file

router = APIRouter(prefix="/integrations", tags=["Integrations (Cloudinary / Telegram)"])

@router.get("/status")
def get_integrations_status():
    return {
        "cloudinary": {
            "status": "connected",
            "cloud_name": settings.CLOUDINARY_CLOUD_NAME,
        },
        "database": {
            "provider": "Neon PostgreSQL (SQLAlchemy)",
            "status": "online",
        },
        "brevo_smtp": {
            "status": "active",
            "server": settings.SMTP_SERVER,
        }
    }

@router.post("/upload")
async def upload_file_direct(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    file_bytes = await file.read()
    res = upload_file(file_bytes, file.filename, folder="school_assignments")
    return {
        "success": True,
        "file_url": res["url"],
        "file_name": file.filename
    }
