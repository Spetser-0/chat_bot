"""
app/models/user.py
──────────────────
Alias for Student model to support User terminology interchangeably.
"""
from app.models.student import Student, StudentRole, StudentStatus

User = Student
UserRole = StudentRole
UserStatus = StudentStatus

__all__ = ["User", "UserRole", "UserStatus"]
