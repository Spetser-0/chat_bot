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

import httpx
from fastapi import BackgroundTasks

from app.core.config import get_settings

logger = logging.getLogger("spetser.email")
logger.setLevel(logging.INFO)


def _mask_email(email: str) -> str:
    """Mask email for privacy in logs (e.g. user@example.com -> u***@example.com)."""
    if "@" not in email:
        return "***"
    local_part, domain = email.split("@", 1)
    if not local_part:
        return f"***@{domain}"
    return f"{local_part[0]}***@{domain}"


async def _send_via_brevo(
    to_email: str,
    subject: str,
    html_body: str,
    *,
    client: Optional[httpx.AsyncClient] = None,
) -> None:
    """
    Send transactional email via Brevo HTTP API (HTTPS port 443).

    Bypasses outbound SMTP port blocks on platforms like Render free tier.
    """
    settings = get_settings()
    masked_email = _mask_email(to_email)
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "api-key": settings.brevo_api_key,
        "content-type": "application/json",
        "accept": "application/json",
    }
    payload = {
        "sender": {
            "name": settings.brevo_sender_name,
            "email": settings.smtp_from,
        },
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_body,
    }

    try:
        if client is not None:
            response = await client.post(url, headers=headers, json=payload)
        else:
            async with httpx.AsyncClient(timeout=settings.email_http_timeout_seconds) as http_client:
                response = await http_client.post(url, headers=headers, json=payload)

        if response.status_code == 201:
            message_id = None
            try:
                data = response.json()
                if isinstance(data, dict):
                    message_id = data.get("messageId")
            except Exception:
                pass
            logger.info(
                "Email sent successfully via Brevo to %s (messageId: %s)",
                masked_email,
                message_id,
            )
        else:
            body_preview = response.text[:200]
            logger.error(
                "Brevo email failed with status %d for %s: %s",
                response.status_code,
                masked_email,
                body_preview,
            )
    except httpx.TimeoutException as exc:
        logger.error(
            "Brevo HTTP request timed out for %s: %s",
            masked_email,
            str(exc),
        )
    except httpx.HTTPError as exc:
        logger.error(
            "Brevo HTTP error for %s: %s",
            masked_email,
            str(exc),
        )
    except Exception as exc:
        logger.exception(
            "Unexpected error sending email via Brevo to %s: %s",
            masked_email,
            str(exc),
        )


def _send_via_smtp_sync(to_email: str, subject: str, html_body: str) -> None:
    """Send email via legacy SMTP (synchronous, timeout=10s)."""
    settings = get_settings()
    masked_email = _mask_email(to_email)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
        if settings.smtp_use_tls:
            server.starttls(context=context)
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)

    logger.info("Email sent successfully via SMTP to %s", masked_email)


async def _send_via_smtp(to_email: str, subject: str, html_body: str) -> None:
    """Send email via SMTP in worker thread without blocking the event loop."""
    masked_email = _mask_email(to_email)
    try:
        await asyncio.to_thread(_send_via_smtp_sync, to_email, subject, html_body)
    except smtplib.SMTPAuthenticationError as exc:
        logger.error(
            "SMTP authentication failed for %s: %s",
            masked_email,
            str(exc),
        )
    except smtplib.SMTPException as exc:
        logger.error(
            "SMTP error sending email to %s: %s",
            masked_email,
            str(exc),
        )
    except Exception as exc:
        logger.exception(
            "Unexpected error sending email via SMTP to %s: %s",
            masked_email,
            str(exc),
        )


async def _send_email_background_worker(
    to_email: str,
    subject: str,
    html_body: str,
) -> None:
    """Safely execute _send_email_task in background, suppressing uncaught exceptions."""
    try:
        await _send_email_task(to_email=to_email, subject=subject, html_body=html_body)
    except Exception as exc:
        masked_email = _mask_email(to_email)
        logger.exception("Unexpected error in background email task for %s: %s", masked_email, str(exc))


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

    Provider selection precedence:
    1. Brevo HTTP API (if BREVO_API_KEY is configured)
    2. SMTP (if SMTP_USER is configured, offloaded to worker thread)
    3. Development mode (prints to console, logs delivery skipped)
    """
    settings = get_settings()

    # 1. Brevo HTTP API
    if settings.brevo_api_key and settings.brevo_api_key.strip():
        await _send_via_brevo(to_email, subject, html_body)
        return

    # 2. SMTP fallback
    if settings.smtp_user and settings.smtp_user.strip():
        await _send_via_smtp(to_email, subject, html_body)
        return

    # 3. Development mode
    masked_email = _mask_email(to_email)
    print(f"[DEV MODE] Email would be sent to {to_email}:\nSubject: {subject}\nBody:\n{html_body}")
    logger.info(
        "[DEV MODE] Email delivery skipped for %s (subject: %s). Configure BREVO_API_KEY or SMTP credentials.",
        masked_email,
        subject,
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
