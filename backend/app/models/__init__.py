"""
app/models/__init__.py
Export all ORM models so Alembic autogenerate can discover them.
"""
from app.models.student import Student
from app.models.request import Request
from app.models.deliverable import Deliverable
from app.models.source_record import SourceRecord
from app.models.credit_ledger import CreditLedger
from app.models.provider import ModelProvider
from app.models.model_configuration import ModelConfiguration
from app.models.feature_configuration import FeatureConfiguration
from app.models.routing_rule import RoutingRule
from app.models.prompt_version import PromptVersion
from app.models.audit_log import AuditLog

__all__ = [
    "Student",
    "Request",
    "Deliverable",
    "SourceRecord",
    "CreditLedger",
    "ModelProvider",
    "ModelConfiguration",
    "FeatureConfiguration",
    "RoutingRule",
    "PromptVersion",
    "AuditLog",
]
