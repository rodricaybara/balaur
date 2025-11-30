"""
Modelos de Usuario y Roles
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class UserRole(str, enum.Enum):
    """Roles de usuario del sistema"""
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    GUEST = "guest"


class User(Base):
    """Modelo de usuario"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    
    # Autenticación
    hashed_password = Column(String(255), nullable=True)  # Null si es LDAP
    is_ldap_user = Column(Boolean, default=True, nullable=False)
    
    # Autorización
    role = Column(
        SQLEnum(UserRole, name="user_role"),
        default=UserRole.GUEST,
        nullable=False,
        index=True
    )
    
    # Estado
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    software_created = relationship("Software", back_populates="creator", foreign_keys="Software.created_by")
    installers_uploaded = relationship("InstallerFile", back_populates="uploader")
    audit_logs = relationship("AuditLog", back_populates="user")
    
    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
    
    def has_permission(self, required_role: UserRole) -> bool:
        """Verifica si el usuario tiene el rol requerido o superior"""
        role_hierarchy = {
            UserRole.GUEST: 0,
            UserRole.USER: 1,
            UserRole.MANAGER: 2,
            UserRole.ADMIN: 3,
        }
        return role_hierarchy.get(self.role, 0) >= role_hierarchy.get(required_role, 0)