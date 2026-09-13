import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.core.config import settings


def generate_otp_code() -> str:
    return str(random.randint(100000, 999999))


def send_otp_via_brevo(recipient_email: str, otp_code: str) -> dict:
    """
    Send OTP via Brevo SMTP relay.

    Render environment requires:
      SMTP_SERVER  = smtp-relay.brevo.com
      SMTP_PORT    = 587
      SMTP_USER    = your Brevo SMTP login  (from Brevo dashboard → SMTP & API)
      SMTP_KEY     = your Brevo SMTP password / API key
      SMTP_FROM    = verified sender email
      DEV_SHOW_OTP = false  (true only for local dev)
    """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>OTP Code</title>
      <style>
        body {{ font-family: Arial, sans-serif; background: #f1f5f9; margin: 0; padding: 20px; }}
        .card {{ max-width: 480px; margin: 20px auto; background: #fff; border-radius: 16px;
                 padding: 32px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); text-align: center; }}
        .otp-box {{ background: #eff6ff; border: 2px dashed #3b82f6; border-radius: 12px;
                    padding: 20px; margin: 20px 0; }}
        .otp {{ font-size: 40px; font-weight: 900; letter-spacing: 12px; color: #1d4ed8; }}
        .warn {{ color: #ef4444; font-size: 13px; }}
      </style>
    </head>
    <body>
      <div class="card">
        <h2 style="color:#0f172a;">Smart School — OTP Code</h2>
        <p style="color:#64748b;">Use this code to sign in. Valid for <strong>5 minutes</strong>.</p>
        <div class="otp-box">
          <div class="otp">{otp_code}</div>
        </div>
        <p class="warn">Do not share this code with anyone.</p>
        <p style="color:#94a3b8;font-size:12px;">
          If you did not request this, please ignore this email.
        </p>
      </div>
    </body>
    </html>
    """

    # Debug: log config (mask key)
    key_preview = (settings.SMTP_KEY[:6] + "***") if settings.SMTP_KEY else "EMPTY"
    print(f"[OTP] Sending to={recipient_email} server={settings.SMTP_SERVER}:{settings.SMTP_PORT} "
          f"user={settings.SMTP_USER} from={settings.SMTP_FROM} key={key_preview}")

    # Guard: if SMTP not configured, fall back gracefully
    if not settings.SMTP_KEY or not settings.SMTP_USER or not settings.SMTP_FROM:
        print("[OTP_WARN] SMTP credentials not configured — OTP NOT sent by email")
        return {
            "success": False,
            "dev_code": otp_code,   # always expose when not configured so dev can still test
            "error": "SMTP not configured",
        }

    success = False
    error_detail = None

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Your OTP Code: {otp_code}"
        msg["From"]    = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM}>"
        msg["To"]      = recipient_email

        msg.attach(MIMEText(f"Your OTP code is: {otp_code} (valid 5 minutes)", "plain"))
        msg.attach(MIMEText(html_content, "html"))

        port = int(settings.SMTP_PORT)
        if port == 465:
            with smtplib.SMTP_SSL(settings.SMTP_SERVER, port, timeout=15) as server:
                server.login(settings.SMTP_USER, settings.SMTP_KEY)
                server.send_message(msg)
        else:
            with smtplib.SMTP(settings.SMTP_SERVER, port, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(settings.SMTP_USER, settings.SMTP_KEY)
                server.send_message(msg)

        success = True
        print(f"[OTP_OK] Sent to {recipient_email}")

    except smtplib.SMTPAuthenticationError as e:
        error_detail = f"SMTP Auth failed — check SMTP_USER and SMTP_KEY on Render: {e}"
        print(f"[OTP_ERR] {error_detail}")
    except smtplib.SMTPException as e:
        error_detail = f"SMTP error: {e}"
        print(f"[OTP_ERR] {error_detail}")
    except Exception as e:
        error_detail = str(e)
        print(f"[OTP_ERR] Unexpected: {error_detail}")

    return {
        "success": success,
        "dev_code": otp_code if settings.DEV_SHOW_OTP else None,
        "error": error_detail,
    }
