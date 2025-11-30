"""
Modelo de Auditoría
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class AuditAction(str, enum.Enum):
    """Acciones auditables"""
    LOGIN = "login"
    LOGOUT = "logout"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    DOWNLOAD = "download"
    VIEW_LICENSE = "view_license"


class AuditLog(Base):
    """Registro de auditoría"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Usuario que realizó la acción
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    username = Column(String(100), nullable=False)  # Guardamos username para histórico
    
    # Acción realizada
    action = Column(
        SQLEnum(AuditAction, name="audit_action"),
        nullable=False,
        index=True
    )
    
    # Recurso afectado
    resource_type = Column(String(50), nullable=True, index=True)  # software, installer, license, user
    resource_id = Column(Integer, nullable=True)
    
    # Información de la petición
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    user_agent = Column(Text, nullable=True)
    
    # Detalles adicionales (JSON)
    details = Column(JSON, nullable=True)
    
    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog {self.action} by {self.username} at {self.timestamp}>"