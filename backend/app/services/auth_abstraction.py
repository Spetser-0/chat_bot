"""
app/services/auth_abstraction.py
────────────────────────────────
Authentication abstraction layer.

Provides a protocol that can be implemented by different auth backends:
- Local session-based auth (current implementation)
- Supabase Auth (future)
- Custom OAuth/OIDC providers

Feature services depend ONLY on this abstraction, not on concrete implementations.
"""
from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class AuthIdentity:
    """
    Verified identity extracted from a trusted authentication source.
    Never construct this from untrusted client input.
    """
    student_id: UUID
    role: str
    email: str | None = None
    display_name: str | None = None


class AuthProvider(Protocol):
    """
    Protocol for authentication providers.
    
    All implementations must:
    - Verify credentials/tokens from trusted sources only
    - Return AuthIdentity with verified student_id
    - Raise AuthError on any verification failure
    """
    
    @abstractmethod
    async def verify_credentials(
        self,
        *,
        email: str,
        password: str,
    ) -> AuthIdentity:
        """Verify email/password credentials. Used for local auth."""
        ...

    @abstractmethod
    async def verify_token(self, token: str) -> AuthIdentity:
        """Verify a session/bearer token and return identity."""
        ...

    @abstractmethod
    async def create_session(self, identity: AuthIdentity) -> str:
        """Create a new session token for the given identity."""
        ...

    @abstractmethod
    async def revoke_session(self, token: str) -> None:
        """Revoke/invalidate a session token."""
        ...


class AuthError(Exception):
    """Base exception for authentication failures."""


class InvalidCredentialsError(AuthError):
    """Raised when credentials are invalid."""


class TokenExpiredError(AuthError):
    """Raised when token/session has expired."""


class TokenInvalidError(AuthError):
    """Raised when token is malformed or tampered."""


class AccountDisabledError(AuthError):
    """Raised when account is suspended/disabled."""
