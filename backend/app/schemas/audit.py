"""
Schemas Pydantic para auditoría
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any
from datetime import datetime
from app.models import AuditAction


class AuditLogResponse(BaseModel):
    """Response con datos de log de auditoría"""
    id: int
    user_id: Optional[int] = None
    username: str
    action: AuditAction
    resource_type: Optional[str] = Field(None, description="software, installer, license, user")
    resource_id: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Optional[dict[str, Any]] = Field(
        None,
        description="JSON con información adicional del evento"
    )
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    """Response para lista de logs de auditoría"""
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
    pages: int


class AuditLogCreate(BaseModel):
    """Schema interno para crear logs de auditoría"""
    user_id: Optional[int] = None
    username: str
    action: AuditAction
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Optional[dict[str, Any]] = None