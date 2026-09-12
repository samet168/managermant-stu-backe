import os
import uuid
from pathlib import Path
import cloudinary
import cloudinary.uploader
from app.core.config import settings

UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

if settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET:
    try:
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True
        )
    except Exception as e:
        print(f"[CLOUDINARY_INIT_ERROR] {e}")

def upload_file(file_bytes: bytes, filename: str, folder: str = "school_assignments") -> dict:
    is_image = any(filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.svg'])
    
    # 1. Try Cloudinary if keys are present
    if settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET:
        try:
            resource_type = "image" if is_image else "raw"
            response = cloudinary.uploader.upload(
                file_bytes,
                folder=folder,
                resource_type=resource_type,
                use_filename=True,
                unique_filename=True
            )
            if response.get("secure_url"):
                return {
                    "success": True,
                    "url": response.get("secure_url"),
                    "file_name": filename,
                    "bytes": response.get("bytes")
                }
        except Exception as e:
            print(f"[CLOUDINARY_NOTICE] Cloudinary upload fallback to local: {e}")

    # 2. Local storage fallback (saved to /uploads/ and served via FastAPI StaticFiles)
    try:
        folder_dir = UPLOADS_DIR / folder
        folder_dir.mkdir(parents=True, exist_ok=True)
        
        unique_name = f"{uuid.uuid4().hex[:8]}_{filename.replace(' ', '_')}"
        file_path = folder_dir / unique_name
        
        with open(file_path, "wb") as f:
            f.write(file_bytes)
            
        file_url = f"http://localhost:8000/uploads/{folder}/{unique_name}"
        return {
            "success": True,
            "url": file_url,
            "file_name": filename,
            "bytes": len(file_bytes)
        }
    except Exception as err:
        print(f"[FILE_SAVE_ERROR] {err}")
        return {
            "success": False,
            "url": "",
            "file_name": filename,
            "error": str(err)
        }

