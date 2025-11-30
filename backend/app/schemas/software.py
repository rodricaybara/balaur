"""
Schemas Pydantic para software
"""
from pydantic import BaseModel, Field, HttpUrl, ConfigDict
from typing import Optional
from datetime import datetime


class SoftwareBase(BaseModel):
    """Base schema para software"""
    name: str = Field(..., min_length=1, max_length=200)
    vendor: str = Field(..., max_length=200)
    category: str = Field(..., max_length=100)
    description: Optional[str] = None
    website: Optional[HttpUrl] = None


class SoftwareCreateRequest(SoftwareBase):
    """Request para crear software"""
    pass


class SoftwareUpdateRequest(BaseModel):
    """Request para actualizar software"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    vendor: Optional[str] = Field(None, max_length=200)
    category: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    website: Optional[HttpUrl] = None


class SoftwareResponse(SoftwareBase):
    """Response con datos de software"""
    id: int
    created_by: int = Field(..., description="ID del usuario creador")
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class SoftwareDetailResponse(SoftwareResponse):
    """Response detallada con instaladores y licencias"""
    installers: list["InstallerResponse"] = []
    licenses: Optional[list["LicenseResponse"]] = Field(
        None,
        description="Solo visible para administradores"
    )


class SoftwareListResponse(BaseModel):
    """Response para lista de software"""
    items: list[SoftwareResponse]
    total: int
    page: int
    page_size: int
    pages: int


# Import necesario para referencias forward
from app.schemas.installer import InstallerResponse
from app.schemas.license import LicenseResponse

# Actualizar referencias forward
SoftwareDetailResponse.model_rebuild()