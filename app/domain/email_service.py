import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.core.config import settings

def generate_otp_code() -> str:
    return str(random.randint(100000, 999999))

def send_otp_via_brevo(recipient_email: str, otp_code: str) -> dict:
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>លេខកូដសម្ងាត់ OTP</title>
      <style>
        body {{ font-family: 'Kantumruy Pro', Arial, sans-serif; background-color: #f1f5f9; margin: 0; padding: 20px; }}
        .card {{ max-width: 480px; margin: 20px auto; background: #ffffff; border-radius: 20px; padding: 32px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); text-align: center; }}
        .badge {{ background: #eff6ff; color: #2563eb; font-weight: 700; font-size: 12px; padding: 6px 14px; border-radius: 9999px; }}
        .otp-container {{ background: #f8fafc; border: 2px dashed #3b82f6; border-radius: 16px; padding: 20px; margin: 20px 0; }}
        .otp-digits {{ font-size: 38px; font-weight: 900; letter-spacing: 10px; color: #1d4ed8; }}
      </style>
    </head>
    <body>
      <div class="card">
        <span class="badge">ប្រព័ន្ធសាលារៀនឌីជីថល (Neon PostgreSQL)</span>
        <h1 style="color:#0f172a; margin-top: 15px;">🔑 លេខកូដសម្ងាត់ OTP</h1>
        <p style="color:#64748b;">សូមប្រើលេខកូដ ៦ ខ្ទង់នេះ ដើម្បីចូលប្រើប្រាស់គណនីរបស់អ្នក</p>
        <div class="otp-container">
          <div class="otp-digits">{otp_code}</div>
        </div>
        <p style="color:#ef4444; font-size: 13px;">⏳ លេខកូដនេះផុតកំណត់ក្នុងរយៈពេល ៥ នាទី!</p>
      </div>
    </body>
    </html>
    """

    success = False
    error_detail = None

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🔐 លេខកូដ OTP: {otp_code} - ប្រព័ន្ធគ្រប់គ្រងសាលារៀន"
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM}>"
        msg["To"] = recipient_email

        msg.attach(MIMEText(f"លេខកូដ OTP: {otp_code} (សុពលភាព ៥ នាទី)", "plain"))
        msg.attach(MIMEText(html_content, "html"))

        if int(settings.SMTP_PORT) == 465:
            with smtplib.SMTP_SSL(settings.SMTP_SERVER, int(settings.SMTP_PORT), timeout=12) as server:
                server.login(settings.SMTP_USER, settings.SMTP_KEY)
                server.send_message(msg)
                success = True
                print(f"[BREVO_SMTP_SUCCESS] Dispatched to {recipient_email} via SSL:465")
        else:
            with smtplib.SMTP(settings.SMTP_SERVER, int(settings.SMTP_PORT), timeout=12) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_KEY)
                server.send_message(msg)
                success = True
                print(f"[BREVO_SMTP_SUCCESS] Dispatched to {recipient_email} via TLS:{settings.SMTP_PORT}")
    except Exception as e:
        error_detail = str(e)
        safe_err = error_detail.encode('ascii', errors='replace').decode('ascii')
        print(f"[BREVO_SMTP_NOTICE] {recipient_email}: {safe_err}")

    return {
        "success": success,
        "dev_code": otp_code if settings.DEV_SHOW_OTP else None,
        "error": error_detail
    }
