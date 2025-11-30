"""
Schemas Pydantic para endpoints de sistema
"""
from pydantic import BaseModel, Field, computed_field
from typing import Optional
from datetime import datetime


class PendingFileResponse(BaseModel):
    """Schema para archivos en inbox/pending"""
    filename: str = Field(..., description="Nombre del archivo")
    size: int = Field(..., description="Tamaño en bytes")
    upload_date: str = Field(..., description="Fecha de subida (ISO format)")
    
    @computed_field
    @property
    def size_mb(self) -> float:
        """Tamaño en MB"""
        return round(self.size / (1024 * 1024), 2)
    
    @computed_field
    @property
    def size_gb(self) -> float:
        """Tamaño en GB"""
        return round(self.size / (1024 * 1024 * 1024), 3)


class ProcessingFileResponse(BaseModel):
    """Schema para archivos en inbox/processing"""
    filename: str = Field(..., description="Nombre del archivo")
    size: int = Field(..., description="Tamaño en bytes")
    sha256: str = Field(..., description="Hash SHA-256 calculado")
    validated_date: str = Field(..., description="Fecha de validación (ISO format)")
    
    @computed_field
    @property
    def size_mb(self) -> float:
        """Tamaño en MB"""
        return round(self.size / (1024 * 1024), 2)
    
    @computed_field
    @property
    def size_gb(self) -> float:
        """Tamaño en GB"""
        return round(self.size / (1024 * 1024 * 1024), 3)


class WatcherStatsResponse(BaseModel):
    """Schema para estadísticas del watcher"""
    pending: int = Field(..., description="Archivos en pending")
    processing: int = Field(..., description="Archivos en processing")
    quarantine: int = Field(..., description="Archivos en quarantine")
    is_running: bool = Field(..., description="Estado del watcher")
    interval_seconds: int = Field(..., description="Intervalo de ejecución")
    last_run: Optional[str] = Field(None, description="Última ejecución (ISO)")
    next_run: Optional[str] = Field(None, description="Próxima ejecución (ISO)")
    last_run_stats: dict = Field(..., description="Estadísticas última ejecución")
    recent_errors: list = Field(default_factory=list, description="Errores recientes")
    paths: dict = Field(..., description="Rutas configuradas")