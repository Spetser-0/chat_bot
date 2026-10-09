"""
app/core/logging.py
───────────────────
Structured logging using structlog.
Configures a processor chain for JSON or dev-friendly console output.
Request IDs are always bound to every log event automatically.

Security:
- A redaction processor scrubs any log value whose KEY looks like a
  secret (api_key, token, secret, password, authorization, private_key,
  webhook_secret, ...), even when logging the same event twice.
"""
from __future__ import annotations

import logging
import re
import sys
from typing import Any

import structlog

from app.core.config import get_settings

# Keys that must never appear in plaintext in logs.
_SECRET_KEY_PATTERN = re.compile(
    r"(api[_-]?key|secret|token|password|passwd|authorization|"
    r"private[_-]?key|webhook[_-]?secret|session|credentials)",
    re.IGNORECASE,
)

_REDACTED = "[REDACTED]"


def redact_secrets(
    logger: Any, method_name: str, event_dict: dict
) -> dict:
    """Replace values of secret-looking keys with [REDACTED]."""
    for key, value in list(event_dict.items()):
        if isinstance(key, str) and _SECRET_KEY_PATTERN.search(key) and value:
            event_dict[key] = _REDACTED
        # Scrub secret-looking values nested one level inside dicts
        elif isinstance(value, dict):
            for inner_key, inner_value in value.items():
                if (
                    isinstance(inner_key, str)
                    and _SECRET_KEY_PATTERN.search(inner_key)
                    and inner_value
                ):
                    value[inner_key] = _REDACTED
    return event_dict


def _add_app_info(
    logger: Any, method_name: str, event_dict: dict
) -> dict:
    settings = get_settings()
    event_dict.setdefault("app", settings.app_name)
    event_dict.setdefault("env", settings.app_env)
    return event_dict


def configure_logging() -> None:
    settings = get_settings()
    log_level = logging.getLevelName(settings.log_level.upper())

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        _add_app_info,
        structlog.processors.StackInfoRenderer(),
        redact_secrets,
    ]

    if settings.log_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Quiet noisy libraries
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
