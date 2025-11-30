"""
Router de consulta de logs de auditoría (solo administradores)
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime
from math import ceil
from app.database import get_db
from app.schemas import AuditLogListResponse, AuditLogResponse
from app.models import AuditLog, AuditAction
from app.dependencies.auth import require_admin
from app.config import settings

router = APIRouter(tags=["Audit"])


@router.get("/logs", response_model=AuditLogListResponse, dependencies=[Depends(require_admin)])
async def get_audit_logs(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(
        settings.default_page_size,
        ge=1,
        le=settings.max_page_size,
        description="Elementos por página"
    ),
    user_id: Optional[int] = Query(None, description="Filtrar por usuario"),
    action: Optional[AuditAction] = Query(None, description="Filtrar por acción"),
    resource_type: Optional[str] = Query(
        None,
        description="Tipo de recurso (software, installer, license, user)"
    ),
    date_from: Optional[datetime] = Query(None, description="Fecha desde (ISO 8601)"),
    date_to: Optional[datetime] = Query(None, description="Fecha hasta (ISO 8601)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Consultar logs de auditoría con filtros
    
    **Requiere:** Rol de Administrador
    
    **Filtros disponibles:**
    - `user_id`: Filtrar por usuario específico
    - `action`: Filtrar por tipo de acción (login, logout, create, update, delete, download, view_license)
    - `resource_type`: Filtrar por tipo de recurso afectado
    - `date_from`: Fecha inicio del rango
    - `date_to`: Fecha fin del rango
    
    **Ordenamiento:** Logs más recientes primero
    """
    # Construir query base
    query = select(AuditLog)
    
    # Aplicar filtros
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    
    if action:
        query = query.where(AuditLog.action == action)
    
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    
    if date_from:
        query = query.where(AuditLog.timestamp >= date_from)
    
    if date_to:
        query = query.where(AuditLog.timestamp <= date_to)
    
    # Obtener total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    # Aplicar paginación y ordenamiento
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(AuditLog.timestamp.desc())
    
    # Ejecutar query
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total > 0 else 0
    )
