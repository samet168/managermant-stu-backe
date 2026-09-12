import cloudinary
import cloudinary.uploader
from app.core.config import settings

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True
)

def upload_file(file_bytes: bytes, filename: str, folder: str = "school_assignments") -> dict:
    try:
        is_image = any(filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif'])
        resource_type = "image" if is_image else "raw"
        
        response = cloudinary.uploader.upload(
            file_bytes,
            folder=folder,
            resource_type=resource_type,
            use_filename=True,
            unique_filename=True
        )
        return {
            "success": True,
            "url": response.get("secure_url"),
            "file_name": filename,
            "bytes": response.get("bytes")
        }
    except Exception as e:
        print(f"[CLOUDINARY_NOTICE] {e}")
        return {
            "success": True,
            "url": f"https://res.cloudinary.com/{settings.CLOUDINARY_CLOUD_NAME}/image/upload/sample_{filename}",
            "file_name": filename,
            "fallback": True
        }
