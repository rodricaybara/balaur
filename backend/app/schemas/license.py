"""
Schemas Pydantic para licencias
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, date
from app.models import LicenseType


class LicenseBase(BaseModel):
    """Base schema para licencia"""
    software_id: int
    license_type: LicenseType
    max_activations: Optional[int] = Field(None, ge=1)
    expiration_date: Optional[date] = None
    notes: Optional[str] = None


class LicenseCreateRequest(LicenseBase):
    """Request para crear licencia"""
    license_key: str = Field(..., min_length=1, description="Será cifrada con AES-GCM")


class LicenseUpdateRequest(BaseModel):
    """Request para actualizar licencia"""
    license_type: Optional[LicenseType] = None
    license_key: Optional[str] = Field(None, min_length=1, description="Nueva clave (será cifrada)")
    max_activations: Optional[int] = Field(None, ge=1)
    expiration_date: Optional[date] = None
    notes: Optional[str] = None


class LicenseResponse(LicenseBase):
    """Response con datos de licencia (sin clave descifrada)"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class LicenseDetailResponse(LicenseResponse):
    """Response detallada con clave descifrada (solo GET individual)"""
    license_key: str = Field(..., description="Clave descifrada (solo en GET individual)")


class LicenseListResponse(BaseModel):
    """Response para lista de licencias"""
    items: list[LicenseResponse]
    total: int
    page: int
    page_size: int
    pages: int