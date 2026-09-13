import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests
from app.core.config import settings


def generate_otp_code() -> str:
    return str(random.randint(100000, 999999))


def _build_html_email(otp_code: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Smart School — OTP Code</title>
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #f8fafc; margin: 0; padding: 24px; }}
        .card {{ max-width: 480px; margin: 0 auto; background: #ffffff; border-radius: 20px;
                 padding: 36px 28px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.06), 0 8px 10px -6px rgba(0,0,0,0.04); border: 1px solid #e2e8f0; text-align: center; }}
        .badge {{ display: inline-block; padding: 6px 14px; background: #eff6ff; color: #2563eb; border-radius: 9999px; font-size: 12px; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 16px; }}
        .title {{ color: #0f172a; font-size: 22px; font-weight: 800; margin: 0 0 8px 0; }}
        .subtitle {{ color: #64748b; font-size: 14px; line-height: 1.5; margin: 0 0 24px 0; }}
        .otp-box {{ background: linear-gradient(135deg, #eff6ff 0%, #f0fdf4 100%); border: 2px dashed #3b82f6; border-radius: 16px;
                    padding: 24px 16px; margin: 20px 0; }}
        .otp {{ font-size: 42px; font-weight: 900; letter-spacing: 12px; color: #1d4ed8; font-family: Consolas, Monaco, monospace; text-indent: 12px; }}
        .validity {{ color: #475569; font-size: 13px; font-weight: 600; margin-top: 10px; }}
        .warn {{ color: #dc2626; font-size: 12px; margin-top: 16px; }}
        .footer {{ color: #94a3b8; font-size: 11px; margin-top: 24px; border-top: 1px solid #f1f5f9; padding-top: 16px; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="badge">សុវត្ថិភាពគណនី / Account Security</div>
        <h1 class="title">ប្រព័ន្ធគ្រប់គ្រងសាលារៀន</h1>
        <p class="subtitle">លេខកូដសម្ងាត់ OTP សម្រាប់ផ្ទៀងផ្ទាត់ និងចូលប្រើប្រាស់គណនីរបស់អ្នក</p>
        
        <div class="otp-box">
          <div class="otp">{otp_code}</div>
          <div class="validity">កូដនេះមានសុពលភាពរយៈពេល <strong>៥ នាទី</strong> (Valid for 5 min)</div>
        </div>

        <p class="warn">សូមកុំចែករំលែកលេខកូដនេះទៅកាន់អ្នកដទៃជាដាច់ខាត (Do not share this code)</p>
        
        <div class="footer">
          ប្រសិនបើអ្នកមិនបានស្នើសុំលេខកូដនេះទេ សូមមិនបាច់អើពើចំពោះអ៊ីមែលនេះឡើយ។<br>
          © 2026 Smart School Digital Portal
        </div>
      </div>
    </body>
    </html>
    """


def send_otp_via_brevo_api(recipient_email: str, otp_code: str, api_key: str) -> dict:
    """Send OTP email using Brevo REST API v3 over HTTPS (Port 443 — works 100% on Render)."""
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "sender": {
            "name": settings.SMTP_FROM_NAME or "Smart School",
            "email": settings.SMTP_FROM
        },
        "to": [{"email": recipient_email}],
        "subject": f"លេខកូដ OTP របស់អ្នក: {otp_code} — Smart School",
        "htmlContent": _build_html_email(otp_code),
        "textContent": f"លេខកូដ OTP របស់អ្នកគឺ: {otp_code} (មានសុពលភាព ៥ នាទី / Valid for 5 minutes)",
    }

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        if res.status_code in [200, 201, 202]:
            print(f"[BREVO_REST_OK] Sent OTP to {recipient_email}")
            return {"success": True, "error": None}
        else:
            err_msg = f"Brevo HTTP {res.status_code}: {res.text}"
            print(f"[BREVO_REST_ERR] {err_msg}")
            return {"success": False, "error": err_msg}
    except Exception as e:
        err_msg = f"Brevo REST request exception: {e}"
        print(f"[BREVO_REST_ERR] {err_msg}")
        return {"success": False, "error": err_msg}


def send_otp_via_smtp(recipient_email: str, otp_code: str) -> dict:
    """Send OTP email using SMTP relay (port 465 SSL or 587 STARTTLS)."""
    html_content = _build_html_email(otp_code)
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"លេខកូដ OTP របស់អ្នក: {otp_code} — Smart School"
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM}>"
    msg["To"] = recipient_email

    msg.attach(MIMEText(f"លេខកូដ OTP របស់អ្នកគឺ: {otp_code} (មានសុពលភាព ៥ នាទី)", "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    server_host = settings.SMTP_SERVER or "smtp-relay.brevo.com"
    configured_port = int(settings.SMTP_PORT or 465)
    
    # Try configured port first, then fallback port if first fails
    ports_to_try = [configured_port]
    if configured_port == 465 and 587 not in ports_to_try:
        ports_to_try.append(587)
    elif configured_port == 587 and 465 not in ports_to_try:
        ports_to_try.append(465)

    last_error = None
    for port in ports_to_try:
        try:
            print(f"[SMTP_TRY] Connecting to {server_host}:{port} for {recipient_email}...")
            if port == 465:
                with smtplib.SMTP_SSL(server_host, port, timeout=8) as server:
                    server.login(settings.SMTP_USER, settings.SMTP_KEY)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(server_host, port, timeout=8) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(settings.SMTP_USER, settings.SMTP_KEY)
                    server.send_message(msg)
            print(f"[SMTP_OK] Successfully sent OTP to {recipient_email} via port {port}")
            return {"success": True, "error": None}
        except smtplib.SMTPAuthenticationError as e:
            last_error = f"SMTP Auth failed (Check SMTP_USER & SMTP_KEY): {e}"
            print(f"[SMTP_ERR] {last_error}")
            break  # Don't retry another port if auth failed
        except Exception as e:
            last_error = f"SMTP error on port {port}: {e}"
            print(f"[SMTP_WARN] {last_error}")

    return {"success": False, "error": last_error}


def send_otp_via_brevo(recipient_email: str, otp_code: str) -> dict:
    """
    Main OTP dispatch method:
    1. First tries Brevo REST API over HTTPS (Port 443) - ideal for Render.
    2. Fallback to SMTP relay (Port 465 / 587).
    3. If neither is configured or both fail, returns status with dev_otp so development / fallback works.
    """
    # 1. Check for Brevo REST API Key (either BREVO_API_KEY or SMTP_KEY if it's an API key)
    brevo_api_key = settings.BREVO_API_KEY
    if not brevo_api_key and settings.SMTP_KEY and settings.SMTP_KEY.startswith("xkeysib-"):
        brevo_api_key = settings.SMTP_KEY

    if brevo_api_key and settings.SMTP_FROM:
        print(f"[OTP_DISPATCH] Trying Brevo HTTPS REST API to {recipient_email}...")
        api_res = send_otp_via_brevo_api(recipient_email, otp_code, brevo_api_key)
        if api_res.get("success"):
            return {
                "success": True,
                "dev_code": otp_code if settings.DEV_SHOW_OTP else None,
                "error": None
            }
        print(f"[OTP_DISPATCH] Brevo REST API returned error: {api_res.get('error')}. Trying SMTP...")

    # 2. Try SMTP if credentials are provided
    if settings.SMTP_KEY and settings.SMTP_USER and settings.SMTP_FROM:
        print(f"[OTP_DISPATCH] Trying SMTP Relay for {recipient_email}...")
        smtp_res = send_otp_via_smtp(recipient_email, otp_code)
        if smtp_res.get("success"):
            return {
                "success": True,
                "dev_code": otp_code if settings.DEV_SHOW_OTP else None,
                "error": None
            }
        error_detail = smtp_res.get("error")
    else:
        error_detail = "Neither BREVO_API_KEY nor SMTP credentials configured"
        print(f"[OTP_WARN] {error_detail}")

    # 3. Fallback / failure handling
    return {
        "success": False,
        "dev_code": otp_code if settings.DEV_SHOW_OTP else None,
        "error": error_detail,
    }
