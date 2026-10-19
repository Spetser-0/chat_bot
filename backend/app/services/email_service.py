"""
app/services/email_service.py
─────────────────────────────
Email sending service for Spetser AI.
Handles OTP emails and password reset emails with fallback for local development.
"""
from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def send_verification_email(to_email: str, code: str) -> None:
    """Send OTP verification email for account activation."""
    settings = get_settings()
    subject = "رمز التحقق - Spetser AI"
    body = f"""
    <div dir="rtl" style="font-family: 'Noto Sans Arabic', 'Segoe UI', Tahoma, sans-serif; padding: 24px; max-width: 500px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #E5E7EB;">
        <div style="text-align: center; margin-bottom: 24px;">
            <h1 style="color: #01696D; font-size: 24px; margin: 0;">Spetser AI</h1>
            <p style="color: #6B7280; font-size: 14px; margin-top: 4px;">مرحباً بك في منصتك التعليمية الذكية</p>
        </div>
        <h2 style="color: #111827; font-size: 18px; margin-bottom: 12px;">رمز تأكيد الحساب</h2>
        <p style="color: #4B5563; font-size: 15px; line-height: 1.6;">
            شكراً لانضمامك إلى Spetser AI. يرجى استخدام رمز التحقق التالي لتفعيل حسابك:
        </p>
        <div style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #01696D; padding: 20px; background: #E6F4F4; border-radius: 12px; text-align: center; margin: 24px 0;">
            {code}
        </div>
        <p style="color: #6B7280; font-size: 13px; line-height: 1.5; margin-bottom: 8px;">
            ⏱️ هذا الرمز صالح لمدة <strong>15 دقيقة</strong> فقط.
        </p>
        <p style="color: #9CA3AF; font-size: 12px; border-top: 1px solid #F3F4F6; padding-top: 16px; margin-top: 24px;">
            إذا لم تطلب هذا الرمز، يمكنك تجاهل هذه الرسالة بأمان.
        </p>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg.attach(MIMEText(body, "html", "utf-8"))

    # For development or test without SMTP credentials:
    if settings.DEBUG or not settings.SMTP_USER:
        print(f"[DEV] Verification code for {to_email}: {code}")
        logger.info("email_verification_dev_mode", to_email=to_email, code=code)
        return

    # Production: Send via SMTP
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            if settings.smtp_tls:
                server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
            logger.info("verification_email_sent", to_email=to_email)
    except Exception as exc:
        logger.error("failed_to_send_verification_email", to_email=to_email, error=str(exc))
        raise


async def send_reset_email(to_email: str, code: str) -> None:
    """Send OTP verification email for password reset."""
    settings = get_settings()
    subject = "إعادة تعيين كلمة المرور - Spetser AI"
    body = f"""
    <div dir="rtl" style="font-family: 'Noto Sans Arabic', 'Segoe UI', Tahoma, sans-serif; padding: 24px; max-width: 500px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #E5E7EB;">
        <div style="text-align: center; margin-bottom: 24px;">
            <h1 style="color: #01696D; font-size: 24px; margin: 0;">Spetser AI</h1>
            <p style="color: #6B7280; font-size: 14px; margin-top: 4px;">إعادة تعيين كلمة المرور</p>
        </div>
        <h2 style="color: #111827; font-size: 18px; margin-bottom: 12px;">رمز استعادة الحساب</h2>
        <p style="color: #4B5563; font-size: 15px; line-height: 1.6;">
            لقد تلقينا طلباً لإعادة تعيين كلمة المرور لحسابك. استخدم الرمز التالي للمتابعة:
        </p>
        <div style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #01696D; padding: 20px; background: #E6F4F4; border-radius: 12px; text-align: center; margin: 24px 0;">
            {code}
        </div>
        <p style="color: #6B7280; font-size: 13px; line-height: 1.5; margin-bottom: 8px;">
            ⏱️ هذا الرمز صالح لمدة <strong>15 دقيقة</strong> فقط.
        </p>
        <p style="color: #9CA3AF; font-size: 12px; border-top: 1px solid #F3F4F6; padding-top: 16px; margin-top: 24px;">
            إذا لم تطلب إعادة تعيين كلمة المرور، يرجى تجاهل هذه الرسالة والتأكد من أمان حسابك.
        </p>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg.attach(MIMEText(body, "html", "utf-8"))

    if settings.DEBUG or not settings.SMTP_USER:
        print(f"[DEV] Reset code for {to_email}: {code}")
        logger.info("email_reset_dev_mode", to_email=to_email, code=code)
        return

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            if settings.smtp_tls:
                server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
            logger.info("reset_email_sent", to_email=to_email)
    except Exception as exc:
        logger.error("failed_to_send_reset_email", to_email=to_email, error=str(exc))
        raise
