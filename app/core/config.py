import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env", override=True)


class Settings:
    PROJECT_NAME: str = "ប្រព័ន្ធគ្រប់គ្រងសាលារៀន (Smart School System)"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # ── Database ────────────────────────────────────────────────────────────
    # Set DATABASE_URL in .env / Render Environment Variables
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # ── JWT & Auth ──────────────────────────────────────────────────────────
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))
    DEV_SHOW_OTP: bool = os.getenv("DEV_SHOW_OTP", "true").lower() == "true"

    # ── Brevo / SMTP ────────────────────────────────────────────────────────
    # Set these in .env / Render Environment Variables
    BREVO_API_KEY: str = os.getenv("BREVO_API_KEY", "")
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp-relay.brevo.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "465"))
    SMTP_KEY: str = os.getenv("SMTP_KEY", "")
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "សាលារៀនឌីជីថល (Smart School)")

    # ── Cloudinary ──────────────────────────────────────────────────────────
    # Set these in .env / Render Environment Variables
    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "")
    CLOUDINARY_URL: str = os.getenv("CLOUDINARY_URL", "")


settings = Settings()
