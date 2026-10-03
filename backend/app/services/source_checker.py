"""
app/services/source_checker.py
────────────────────────────────
Abstract source verification service.

Verifies that citations in a presentation correspond to real, accessible sources.
Returns verification status per source without modifying the presentation content.

Design principles:
- Never silently turn unverified → verified
- Distinguish: unverified (not checked) vs verified (confirmed) vs broken (checked, failed)
- Pluggable implementations: mock (tests), web search, DOI resolver, etc.
- Returns structured results for audit trail
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from app.schemas.presentation import SourceCitation


@dataclass(frozen=True)
class VerifiedSource:
    """A source with its verification result."""
    claim: str
    citation: str
    original_status: str  # "verified" | "unverified"
    verification_status: str  # "verified" | "unverified" | "broken" | "disputed"
    check_details: str | None = None
    metadata: dict | None = None


@dataclass(frozen=True)
class VerificationResult:
    """Result of verifying all sources in a presentation."""
    verified_count: int
    unverified_count: int
    broken_count: int
    disputed_count: int
    sources: list[VerifiedSource]
    warnings: list[str]


class SourceChecker(ABC):
    """
    Abstract source verification interface.
    
    Implementations must:
    - Check if a citation corresponds to a real, accessible source
    - Return verification status without modifying original content
    - Be idempotent and safe to retry
    """
    
    @abstractmethod
    async def verify_sources(
        self,
        sources: list[SourceCitation],
        *,
        deliverable_id: UUID | None = None,
    ) -> VerificationResult:
        """
        Verify a list of source citations.
        
        Args:
            sources: List of SourceCitation objects from the presentation
            deliverable_id: Optional ID for audit logging
            
        Returns:
            VerificationResult with per-source status and aggregate counts
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the verification service is operational."""
        ...


# ──────────────────────────────────────────────────────────────────────────────
# Mock Implementation (for tests)
# ──────────────────────────────────────────────────────────────────────────────

class MockSourceChecker(SourceChecker):
    """
    Deterministic mock source checker for testing.
    
    Behavior controlled by constructor:
    - If a citation contains "verified" (case-insensitive) → VERIFIED
    - If a citation contains "broken" → BROKEN
    - If a citation contains "disputed" → DISPUTED
    - Otherwise → UNVERIFIED
    """
    
    def __init__(
        self,
        *,
        default_status: str = "unverified",
        raise_on_verify: Exception | None = None,
    ) -> None:
        self._default_status = default_status
        self._raise = raise_on_verify
        self.call_count = 0
        self.last_sources: list[SourceCitation] | None = None

    async def verify_sources(
        self,
        sources: list[SourceCitation],
        *,
        deliverable_id: UUID | None = None,
    ) -> VerificationResult:
        if self._raise:
            raise self._raise
        
        self.call_count += 1
        self.last_sources = sources
        
        verified = []
        warnings = []
        
        for src in sources:
            citation_lower = src.citation.lower()
            
            if "verified" in citation_lower:
                status = "verified"
            elif "broken" in citation_lower:
                status = "broken"
            elif "disputed" in citation_lower:
                status = "disputed"
            else:
                status = "unverified"
            
            if src.verification_status == "verified" and status != "verified":
                warnings.append(
                    f"Model marked source as verified but checker found '{status}': "
                    f"'{src.citation[:80]}...'"
                )
            
            verified.append(VerifiedSource(
                claim=src.claim,
                citation=src.citation,
                original_status=src.verification_status,
                verification_status=status,
                metadata=src.metadata,
            ))
        
        return VerificationResult(
            verified_count=sum(1 for v in verified if v.verification_status == "verified"),
            unverified_count=sum(1 for v in verified if v.verification_status == "unverified"),
            broken_count=sum(1 for v in verified if v.verification_status == "broken"),
            disputed_count=sum(1 for v in verified if v.verification_status == "disputed"),
            sources=verified,
            warnings=warnings,
        )

    async def health_check(self) -> bool:
        return True


# ──────────────────────────────────────────────────────────────────────────────
# Factory
# ──────────────────────────────────────────────────────────────────────────────

def get_source_checker() -> SourceChecker:
    """
    Factory returning the configured SourceChecker implementation.
    
    Currently returns MockSourceChecker.
    Future: can return WebSearchSourceChecker, DOISourceChecker, etc.
    """
    return MockSourceChecker()