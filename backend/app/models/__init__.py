"""
app/models/__init__.py
Export all ORM models so Alembic autogenerate can discover them.
"""
# Existing models
from app.models.audit_log import AuditLog
from app.models.credit_ledger import CreditLedger
from app.models.deliverable import Deliverable
from app.models.feature_configuration import FeatureConfiguration
from app.models.model_configuration import ModelConfiguration
from app.models.prompt_version import PromptVersion
from app.models.provider import ModelProvider
from app.models.request import Request
from app.models.routing_rule import RoutingRule
from app.models.source_record import SourceRecord
from app.models.student import Student

# Phase 1: New models
from app.models.ai_provider import AIProvider
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.payment_invoice import PaymentInvoice
from app.models.referral import Referral
from app.models.reward_transaction import RewardTransaction
from app.models.skill import Skill
from app.models.skill_tool import SkillTool
from app.models.webhook_event import WebhookEvent

__all__ = [
    # Existing models
    "AuditLog",
    "CreditLedger",
    "Deliverable",
    "FeatureConfiguration",
    "ModelConfiguration",
    "ModelProvider",
    "PromptVersion",
    "Request",
    "RoutingRule",
    "SourceRecord",
    "Student",
    # Phase 1: New models
    "AIProvider",
    "Conversation",
    "Message",
    "PaymentInvoice",
    "Referral",
    "RewardTransaction",
    "Skill",
    "SkillTool",
    "WebhookEvent",
]
