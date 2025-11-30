"""
Schemas Pydantic de la aplicación
"""
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from app.schemas.user import (
    UserCreateRequest,
    UserUpdateRequest,
    UserResponse,
    UserListResponse
)
from app.schemas.software import (
    SoftwareCreateRequest,
    SoftwareUpdateRequest,
    SoftwareResponse,
    SoftwareDetailResponse,
    SoftwareListResponse
)
from app.schemas.installer import (
    InstallerCreateRequest,
    InstallerResponse,
    InstallerListResponse
)
from app.schemas.license import (
    LicenseCreateRequest,
    LicenseUpdateRequest,
    LicenseResponse,
    LicenseDetailResponse,
    LicenseListResponse
)
from app.schemas.audit import (
    AuditLogResponse,
    AuditLogListResponse,
    AuditLogCreate
)

__all__ = [
    # Auth
    "LoginRequest",
    "RefreshRequest",
    "TokenResponse",
    # User
    "UserCreateRequest",
    "UserUpdateRequest",
    "UserResponse",
    "UserListResponse",
    # Software
    "SoftwareCreateRequest",
    "SoftwareUpdateRequest",
    "SoftwareResponse",
    "SoftwareDetailResponse",
    "SoftwareListResponse",
    # Installer
    "InstallerCreateRequest",
    "InstallerResponse",
    "InstallerListResponse",
    # License
    "LicenseCreateRequest",
    "LicenseUpdateRequest",
    "LicenseResponse",
    "LicenseDetailResponse",
    "LicenseListResponse",
    # Audit
    "AuditLogResponse",
    "AuditLogListResponse",
    "AuditLogCreate",
]