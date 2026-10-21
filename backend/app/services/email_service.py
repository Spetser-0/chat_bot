"""
Email sending service for Spetser AI.
─────────────────────────────────────────
Sends emails asynchronously via SMTP with proper error handling.

In development (DEBUG=True or no SMTP_USER): prints to console
In production: sends via configured SMTP server
"""
from __future__ import annotations

import asyncio
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from fastapi import BackgroundTasks

from app.core.config import get_settings

logger = logging.getLogger("spetser.email")


async def _send_email_background_worker(
    to_email: str,
    subject: str,
    html_body: str,
) -> None:
    """Safely execute _send_email_task in background, suppressing uncaught exceptions."""
    try:
        await _send_email_task(to_email=to_email, subject=subject, html_body=html_body)
    except Exception as exc:
        logger.exception("Unexpected error in background email task for %s: %s", to_email, str(exc))


async def _dispatch_email_task(
    to_email: str,
    subject: str,
    html_body: str,
) -> None:
    """Dispatch email worker asynchronously on the running event loop without blocking response completion."""
    asyncio.create_task(_send_email_background_worker(to_email, subject, html_body))


async def send_email_background(
    to_email: str,
    subject: str,
    html_body: str,
    background_tasks: BackgroundTasks,
) -> None:
    """
    Queue email for background sending.

    This function returns immediately (doesn't block the HTTP response).
    The actual sending happens in a background task after the response is sent.

    Args:
        to_email: Recipient email address
        subject: Email subject line
        html_body: HTML content of the email
        background_tasks: FastAPI BackgroundTasks instance (injected via Depends)
    """
    background_tasks.add_task(
        _dispatch_email_task,
        to_email=to_email,
        subject=subject,
        html_body=html_body,
    )


async def _send_email_task(
    to_email: str,
    subject: str,
    html_body: str,
) -> None:
    """
    Background task that actually sends the email.

    This runs after the HTTP response is sent, so failures don't affect
    the user's experience but are logged for debugging.
    """
    settings = get_settings()

    # Development mode: print to console
    if settings.app_env == "development" or not settings.smtp_user:
        print(f"[DEV MODE] Email would be sent to {to_email}:\nSubject: {subject}\nBody:\n{html_body}")
        logger.info(
            "[DEV MODE] Email would be sent to %s:\nSubject: %s\nBody:\n%s",
            to_email,
            subject,
            html_body,
        )
        return

    # Production mode: send via SMTP
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        # Create SSL context for secure connection
        context = ssl.create_default_context()

        # Connect to SMTP server
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            if settings.smtp_use_tls:
                server.starttls(context=context)

            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)

        logger.info("Email sent successfully to %s", to_email)

    except smtplib.SMTPAuthenticationError as e:
        logger.error(
            "SMTP authentication failed for %s: %s",
            to_email,
            str(e),
        )
        # Don't raise — this is a background task, user already saw success

    except smtplib.SMTPException as e:
        logger.error(
            "SMTP error sending email to %s: %s",
            to_email,
            str(e),
        )

    except Exception as e:
        logger.exception(
            "Unexpected error sending email to %s: %s",
            to_email,
            str(e),
        )


async def send_verification_email(
    to_email: str,
    code: str,
    background_tasks: Optional[BackgroundTasks] = None,
) -> None:
    """
    Send OTP verification email.

    If background_tasks is provided, sends asynchronously (recommended).
    Otherwise, sends synchronously (legacy behavior, blocks response).
    """
    subject = "رمز التحقق - Spetser AI"

    html_body = f"""
    <div dir="rtl" style="font-family: 'Noto Sans Arabic', sans-serif; padding: 20px; max-width: 600px; margin: 0 auto;">
        <div style="background: #F9F8F4; border-radius: 12px; padding: 32px; border: 1px solid #E5E7EB;">
            <h2 style="color: #01696D; margin-top: 0;">مرحباً بك في Spetser AI</h2>
            <p style="font-size: 16px; line-height: 1.6; color: #1A1A1A;">
                رمز التحقق الخاص بك هو:
            </p>
            <div style="font-size: 32px; font-weight: bold; letter-spacing: 8px; 
                        color: #01696D; padding: 24px; background: #E6F4F4; 
                        border-radius: 12px; text-align: center; margin: 24px 0;
                        border: 2px solid #01696D;">
                {code}
            </div>
            <p style="color: #6B7280; font-size: 14px;">
                هذا الرمز صالح لمدة 15 دقيقة فقط.
            </p>
            <p style="color: #6B7280; font-size: 14px;">
                إذا لم تطلب هذا الرمز، يرجى تجاهل هذه الرسالة.
            </p>
            <hr style="border: none; border-top: 1px solid #E5E7EB; margin: 24px 0;">
            <p style="color: #9CA3AF; font-size: 12px; text-align: center;">
                © 2026 Spetser AI — منصة تعليمية ذكية للطلاب العرب
            </p>
        </div>
    </div>
    """

    if background_tasks is not None:
        # Async mode (recommended)
        await send_email_background(to_email, subject, html_body, background_tasks)
    else:
        # Sync mode (legacy, blocks)
        await _send_email_task(to_email, subject, html_body)


async def send_reset_email(
    to_email: str,
    code: str,
    background_tasks: Optional[BackgroundTasks] = None,
) -> None:
    """Send password reset email."""
    subject = "إعادة تعيين كلمة المرور - Spetser AI"

    html_body = f"""
    <div dir="rtl" style="font-family: 'Noto Sans Arabic', sans-serif; padding: 20px; max-width: 600px; margin: 0 auto;">
        <div style="background: #F9F8F4; border-radius: 12px; padding: 32px; border: 1px solid #E5E7EB;">
            <h2 style="color: #01696D; margin-top: 0;">إعادة تعيين كلمة المرور</h2>
            <p style="font-size: 16px; line-height: 1.6; color: #1A1A1A;">
                لقد طلبت إعادة تعيين كلمة المرور. رمز التحقق الخاص بك هو:
            </p>
            <div style="font-size: 32px; font-weight: bold; letter-spacing: 8px; 
                        color: #01696D; padding: 24px; background: #E6F4F4; 
                        border-radius: 12px; text-align: center; margin: 24px 0;
                        border: 2px solid #01696D;">
                {code}
            </div>
            <p style="color: #6B7280; font-size: 14px;">
                هذا الرمز صالح لمدة 15 دقيقة فقط.
            </p>
            <p style="color: #DC2626; font-size: 14px; font-weight: bold;">
                إذا لم تطلب هذا، يرجى تغيير كلمة المرور فوراً وتأمين حسابك.
            </p>
        </div>
    </div>
    """

    if background_tasks is not None:
        await send_email_background(to_email, subject, html_body, background_tasks)
    else:
        await _send_email_task(to_email, subject, html_body)
