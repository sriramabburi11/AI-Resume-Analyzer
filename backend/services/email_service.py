import os
import secrets
import hmac
import hashlib
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
import requests

logger = logging.getLogger("email_service")

# SMTP Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587").strip() or "587")
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "").strip() or SMTP_USER or "noreply@resumepulse.com"
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "AI Resume Analyzer").strip()
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

# Resend API Alternative
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "").strip() or "onboarding@resend.dev"

# HMAC Secret for OTP Hashing
OTP_HASH_SECRET = os.getenv("OTP_SECRET_KEY", "").strip() or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "resume_analyzer_secure_otp_salt_2026")


def generate_secure_otp(length: int = 6) -> str:
    """
    Generates a cryptographically secure numeric OTP using Python's secrets module.
    """
    return "".join(secrets.choice("0123456789") for _ in range(length))


def hash_otp(email: str, otp: str, purpose: str = "email_verification") -> str:
    """
    Generates a cryptographically secure HMAC-SHA256 digest of the OTP.
    Ensures that plain OTPs are never stored in the database.
    """
    message = f"{email.lower().strip()}:{otp.strip()}:{purpose}".encode("utf-8")
    key = OTP_HASH_SECRET.encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def verify_otp_hash(email: str, input_otp: str, stored_hash: str, purpose: str = "email_verification") -> bool:
    """
    Constant-time comparison of the computed OTP hash against the stored hash.
    Protects against timing attacks.
    """
    computed = hash_otp(email, input_otp, purpose)
    return hmac.compare_digest(computed, stored_hash)


def build_verification_html(otp: str, full_name: Optional[str] = None) -> str:
    """
    Builds a responsive, accessible HTML email template for the verification code.
    """
    greeting_name = full_name.strip() if full_name and full_name.strip() else "Job Seeker"
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Verify Your Email</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f8fafc; padding: 32px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width: 540px; background-color: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); overflow: hidden;">
          <!-- Header -->
          <tr>
            <td style="background-color: #2563eb; padding: 28px 32px; text-align: center;">
              <h1 style="margin: 0; color: #ffffff; font-size: 20px; font-weight: 700; letter-spacing: -0.5px;">AI Resume Analyzer & ATS Optimizer</h1>
              <p style="margin: 6px 0 0; color: #dbeafe; font-size: 13px;">Secure Email Verification</p>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding: 32px;">
              <h2 style="margin: 0 0 12px; font-size: 18px; color: #0f172a; font-weight: 600;">Welcome, {greeting_name}!</h2>
              <p style="margin: 0 0 20px; font-size: 14px; line-height: 1.6; color: #475569;">
                Thank you for creating an account with AI Resume Analyzer. To complete your registration and protect your account, please enter the following 6-digit verification code:
              </p>
              
              <!-- OTP Box -->
              <div style="background-color: #eff6ff; border: 1px solid #bfdbfe; border-radius: 12px; padding: 20px; text-align: center; margin: 24px 0;">
                <span style="font-family: 'Courier New', Courier, monospace; font-size: 34px; font-weight: 700; letter-spacing: 8px; color: #1d4ed8; display: inline-block;">{otp}</span>
                <p style="margin: 8px 0 0; font-size: 12px; color: #64748b; font-weight: 500;">
                  ⏳ This code expires in <strong>10 minutes</strong>.
                </p>
              </div>

              <p style="margin: 20px 0 0; font-size: 13px; line-height: 1.5; color: #64748b;">
                If you did not request this verification code or create an account, you can safely ignore this email.
              </p>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="background-color: #f8fafc; border-top: 1px solid #f1f5f9; padding: 20px 32px; text-align: center;">
              <p style="margin: 0; font-size: 11px; color: #94a3b8;">
                AI Resume Analyzer & ATS Optimizer • High-Impact Technical Applications<br>
                For security reasons, never share this verification code with anyone.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def send_verification_email(email: str, otp: str, full_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Dispatches the 6-digit OTP to the user's email address.
    Supports Resend API, SMTP delivery, and resilient sandbox fallback.
    Returns delivery status dictionary with provider details and preview code when in sandbox mode.
    """
    from dotenv import load_dotenv
    load_dotenv(override=False)

    clean_email = email.lower().strip()
    html_content = build_verification_html(otp, full_name)
    plain_content = f"Your AI Resume Analyzer verification code is: {otp}. This code expires in 10 minutes."
    subject = f"{otp} is your AI Resume Analyzer verification code"

    api_key = os.getenv("RESEND_API_KEY", "").strip() or RESEND_API_KEY
    from_email = os.getenv("RESEND_FROM_EMAIL", "").strip() or RESEND_FROM_EMAIL

    # 1. Try Resend API if configured
    if api_key:
        try:
            res = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": f"{SMTP_FROM_NAME} <{from_email}>",
                    "to": [clean_email],
                    "subject": subject,
                    "html": html_content,
                    "text": plain_content,
                },
                timeout=8,
            )
            if res.status_code in (200, 201):
                logger.info(f"Verification email delivered via Resend to {clean_email}")
                return {
                    "delivered": True,
                    "provider": "resend",
                    "notice": f"Verification code delivered to {clean_email}",
                    "preview_otp": None
                }
            else:
                err_text = res.text
                logger.warning(f"Resend delivery response ({res.status_code}): {err_text}")
                # Resend free sandbox limitation: only delivers to the Resend account owner's email
                is_sandbox_restricted = res.status_code == 403 or "only send testing emails" in err_text.lower()
                
                # If recipient was restricted by sandbox, attempt to notify owner account if different
                owner_email = "abburimohan2125@gmail.com"
                if is_sandbox_restricted and clean_email != owner_email:
                    try:
                        requests.post(
                            "https://api.resend.com/emails",
                            headers={
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json",
                            },
                            json={
                                "from": f"{SMTP_FROM_NAME} <{from_email}>",
                                "to": [owner_email],
                                "subject": f"Verification Code for {clean_email}: {otp}",
                                "html": f"<p>A verification code was requested for <strong>{clean_email}</strong>:<br><h2 style='font-size:28px;color:#2563eb;'>{otp}</h2></p>",
                            },
                            timeout=5,
                        )
                    except Exception:
                        pass

                return {
                    "delivered": False,
                    "provider": "resend_sandbox",
                    "notice": "Resend sandbox delivery active (only delivers directly to abburimohan2125@gmail.com without verified custom domain). Verification code is provided below for testing.",
                    "preview_otp": otp
                }
        except Exception as e:
            logger.warning(f"Resend API gateway unreachable ({type(e).__name__}): {e}")
            return {
                "delivered": False,
                "provider": "resend_timeout",
                "notice": "Resend gateway network unreachable. Verification code is provided below for instant testing.",
                "preview_otp": otp
            }

    # 2. Try Standard SMTP if host and credentials configured
    smtp_host = os.getenv("SMTP_HOST", "").strip() or SMTP_HOST
    smtp_user = os.getenv("SMTP_USER", "").strip() or SMTP_USER
    smtp_pwd = os.getenv("SMTP_PASSWORD", "").strip() or SMTP_PASSWORD
    if smtp_host and smtp_user and smtp_pwd:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
            msg["To"] = clean_email

            msg.attach(MIMEText(plain_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            if SMTP_PORT == 465:
                server = smtplib.SMTP_SSL(smtp_host, SMTP_PORT, timeout=10)
            else:
                server = smtplib.SMTP(smtp_host, SMTP_PORT, timeout=10)
                if SMTP_USE_TLS:
                    server.starttls()

            server.login(smtp_user, smtp_pwd)
            server.sendmail(SMTP_FROM_EMAIL, [clean_email], msg.as_string())
            server.quit()
            logger.info(f"Verification email delivered via SMTP to {clean_email}")
            return {
                "delivered": True,
                "provider": "smtp",
                "notice": f"Verification email sent via SMTP to {clean_email}",
                "preview_otp": None
            }
        except Exception as e:
            logger.error(f"SMTP delivery error for {clean_email}: {e}")

    # 3. Development / Safe Sandbox Fallback
    logger.info(f"Email service dispatched verification code to {clean_email} (sandbox fallback active)")
    return {
        "delivered": False,
        "provider": "sandbox",
        "notice": "Sandbox mode active. Your 6-digit verification code is provided below.",
        "preview_otp": otp
    }

