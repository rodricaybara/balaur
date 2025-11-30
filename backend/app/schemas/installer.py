"""
Schemas Pydantic para instaladores
"""
from pydantic import BaseModel, Field, ConfigDict, field_validator, computed_field
from typing import Optional
from datetime import datetime
import re


class InstallerBase(BaseModel):
    """Base schema para instalador"""
    software_id: int
    version: str = Field(..., min_length=1, max_length=50)
    filename: str = Field(..., description="Nombre del archivo en el FTP repository")
    architecture: Optional[str] = Field(None, description="x64, x86, arm64, universal")
    platform: Optional[str] = Field(None, description="Windows, Linux, macOS")
    notes: Optional[str] = None


class InstallerCreateRequest(InstallerBase):
    """Request para registrar instalador"""
    file_size: int = Field(..., ge=1, description="Tamaño en bytes")
    sha256_hash: str = Field(..., pattern=r"^[a-f0-9]{64}$")
    
    @field_validator('sha256_hash')
    @classmethod
    def validate_sha256(cls, v: str) -> str:
        """Valida formato SHA-256"""
        if not re.match(r'^[a-f0-9]{64}$', v):
            raise ValueError('Invalid SHA-256 hash format')
        return v.lower()


class InstallerResponse(InstallerBase):
    """Response con datos de instalador"""
    id: int
    file_size: int = Field(..., description="Tamaño en bytes")
    sha256_hash: str = Field(..., pattern=r"^[a-f0-9]{64}$")
    download_count: int = 0
    uploaded_by: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
    
    @computed_field
    @property
    def file_size_mb(self) -> float:
        """Tamaño en MB"""
        return round(self.file_size / (1024 * 1024), 2)
    
    @computed_field
    @property
    def file_size_gb(self) -> float:
        """Tamaño en GB"""
        return round(self.file_size / (1024 * 1024 * 1024), 3)


class InstallerListResponse(BaseModel):
    """Response para lista de instaladores"""
    items: list[InstallerResponse]
    total: int