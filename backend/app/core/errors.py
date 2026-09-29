"""
app/core/errors.py
───────────────────
Typed application error hierarchy.
All HTTP-facing exceptions are raised as SpetserError subclasses so the
global exception handler can produce consistent, safe response envelopes.
"""
from __future__ import annotations

from typing import Any


class SpetserError(Exception):
    """Base class for all application errors."""

    http_status: int = 500
    error_code: str = "INTERNAL_ERROR"
    safe_message: str = "حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى."  # Arabic default

    def __init__(
        self,
        safe_message: str | None = None,
        *,
        detail: Any = None,
        error_code: str | None = None,
    ) -> None:
        super().__init__(safe_message or self.safe_message)
        self.safe_message = safe_message or self.__class__.safe_message
        self.detail = detail
        if error_code:
            self.error_code = error_code


# ── Authentication & Authorization ──────────────────────────────────────────

class AuthenticationError(SpetserError):
    http_status = 401
    error_code = "AUTHENTICATION_REQUIRED"
    safe_message = "المصادقة مطلوبة. يرجى تسجيل الدخول."


class AuthorizationError(SpetserError):
    http_status = 403
    error_code = "FORBIDDEN"
    safe_message = "ليس لديك إذن للوصول إلى هذا المورد."


class SessionExpiredError(AuthenticationError):
    error_code = "SESSION_EXPIRED"
    safe_message = "انتهت صلاحية الجلسة. يرجى تسجيل الدخول مجدداً."


# ── Resource Errors ──────────────────────────────────────────────────────────

class NotFoundError(SpetserError):
    http_status = 404
    error_code = "NOT_FOUND"
    safe_message = "المورد المطلوب غير موجود."


class ConflictError(SpetserError):
    http_status = 409
    error_code = "CONFLICT"
    safe_message = "طلب مكرر."


# ── Validation ───────────────────────────────────────────────────────────────

class ValidationError(SpetserError):
    http_status = 422
    error_code = "VALIDATION_ERROR"
    safe_message = "البيانات المُرسلة غير صحيحة."


class SchemaValidationError(ValidationError):
    error_code = "SCHEMA_VALIDATION_ERROR"
    safe_message = "استجابة النموذج لم تجتز التحقق من الصحة."


# ── Rate Limiting ────────────────────────────────────────────────────────────

class RateLimitError(SpetserError):
    http_status = 429
    error_code = "RATE_LIMIT_EXCEEDED"
    safe_message = "تجاوزت الحد المسموح به من الطلبات. يرجى الانتظار قليلاً."


# ── Credit / Billing ─────────────────────────────────────────────────────────

class InsufficientCreditsError(SpetserError):
    http_status = 402
    error_code = "INSUFFICIENT_CREDITS"
    safe_message = "رصيدك غير كافٍ لإتمام هذا الطلب."


# ── Provider / AI Errors ─────────────────────────────────────────────────────

class ProviderError(SpetserError):
    http_status = 502
    error_code = "PROVIDER_ERROR"
    safe_message = "خدمة الذكاء الاصطناعي غير متاحة حالياً. يرجى المحاولة لاحقاً."


class ProviderTimeoutError(ProviderError):
    error_code = "PROVIDER_TIMEOUT"
    safe_message = "استغرق النموذج وقتاً طويلاً. يرجى المحاولة مجدداً."


class ProviderRateLimitError(ProviderError):
    http_status = 429
    error_code = "PROVIDER_RATE_LIMIT"
    safe_message = "تم تجاوز حد الاستخدام مع مزود النموذج. يرجى الانتظار."


class ProviderAuthError(ProviderError):
    http_status = 503
    error_code = "PROVIDER_AUTH_ERROR"
    safe_message = "خطأ في إعداد مزود النموذج. يرجى التواصل مع الدعم."


class ProviderInvalidResponseError(ProviderError):
    error_code = "PROVIDER_INVALID_RESPONSE"
    safe_message = "استجابة غير صالحة من النموذج. يرجى المحاولة مجدداً."


class ProviderUnsupportedModelError(ProviderError):
    http_status = 400
    error_code = "PROVIDER_UNSUPPORTED_MODEL"
    safe_message = "النموذج المطلوب غير مدعوم."


# ── Feature / Service Errors ─────────────────────────────────────────────────

class FeatureDisabledError(SpetserError):
    http_status = 503
    error_code = "FEATURE_DISABLED"
    safe_message = "هذه الميزة غير متاحة حالياً."


class RoutingError(SpetserError):
    http_status = 500
    error_code = "ROUTING_ERROR"
    safe_message = "تعذّر توجيه طلبك. يرجى المحاولة مجدداً."


# ── Storage Errors ───────────────────────────────────────────────────────────

class StorageError(SpetserError):
    http_status = 500
    error_code = "STORAGE_ERROR"
    safe_message = "فشل في حفظ الملف. يرجى المحاولة مجدداً."


class StorageUploadError(StorageError):
    error_code = "STORAGE_UPLOAD_ERROR"


class StorageDownloadError(StorageError):
    error_code = "STORAGE_DOWNLOAD_ERROR"


# ── Idempotency ───────────────────────────────────────────────────────────────

class IdempotencyConflictError(ConflictError):
    error_code = "IDEMPOTENCY_CONFLICT"
    safe_message = "طلب مكرر بنفس المفتاح."
