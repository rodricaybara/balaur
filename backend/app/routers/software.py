"""
Router de gestión de software
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional
from math import ceil
from app.database import get_db
from app.schemas import (
    SoftwareResponse,
    SoftwareDetailResponse,
    SoftwareListResponse,
    SoftwareCreateRequest,
    SoftwareUpdateRequest,
    InstallerResponse
)
from app.models import Software, User, UserRole, AuditAction
from app.dependencies.auth import get_current_user, require_manager, require_admin
from app.middleware.audit import AuditService
from app.config import settings

router = APIRouter(tags=["Software"])


def _get_client_ip(request: Request) -> str:
    """Obtiene IP real del cliente considerando proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return (
        request.headers.get("X-Real-IP") or
        (request.client.host if request.client else "unknown")
    )


@router.get("", response_model=SoftwareListResponse)
async def list_software(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(
        settings.default_page_size,
        ge=1,
        le=settings.max_page_size,
        description="Elementos por página"
    ),
    category: Optional[str] = Query(None, description="Filtrar por categoría"),
    search: Optional[str] = Query(None, description="Buscar en nombre o descripción"),
    vendor: Optional[str] = Query(None, description="Filtrar por proveedor"),
    db: AsyncSession = Depends(get_db)
):
    """
    Listar software disponible con filtros y paginación

    **Público:** Todos los usuarios pueden consultar
    """
    query = select(Software)

    if category:
        query = query.where(Software.category == category)

    if vendor:
        query = query.where(Software.vendor.ilike(f"%{vendor}%"))

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (Software.name.ilike(search_pattern)) |
            (Software.description.ilike(search_pattern))
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Software.name)

    result = await db.execute(query)
    software_list = result.scalars().all()

    return SoftwareListResponse(
        items=[SoftwareResponse.model_validate(s) for s in software_list],
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total > 0 else 0
    )


@router.get("/{software_id}", response_model=SoftwareDetailResponse)
async def get_software(
    software_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener detalles de software por ID

    - Incluye lista de instaladores
    - Licencias solo visibles para administradores
    """
    query = select(Software).where(Software.id == software_id)
    query = query.options(
        selectinload(Software.installers),
        selectinload(Software.licenses)
    )

    result = await db.execute(query)
    software = result.scalar_one_or_none()

    if not software:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Software with id {software_id} not found"
        )

    response_data = SoftwareDetailResponse.model_validate(software)

    if current_user.role != UserRole.ADMIN:
        response_data.licenses = None

    return response_data


@router.post("", response_model=SoftwareResponse, status_code=status.HTTP_201_CREATED)
async def create_software(
    software_data: SoftwareCreateRequest,
    request: Request,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Crear nuevo software

    **Requiere:** Rol de Gestor o Administrador
    """
    result = await db.execute(
        select(Software).where(
            Software.name == software_data.name,
            Software.vendor == software_data.vendor
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Software '{software_data.name}' from vendor '{software_data.vendor}' already exists"
        )

    new_software = Software(
        name=software_data.name,
        vendor=software_data.vendor,
        category=software_data.category,
        description=software_data.description,
        website=str(software_data.website) if software_data.website else None,
        created_by=current_user.id
    )

    db.add(new_software)
    await db.commit()
    await db.refresh(new_software)

    await AuditService.log_action(
        db=db,
        user=current_user,
        action=AuditAction.CREATE,
        resource_type="software",
        resource_id=new_software.id,
        ip_address=_get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    try:
        request.state.audit_logged = True
    except Exception:
        pass

    return new_software


@router.put("/{software_id}", response_model=SoftwareResponse)
async def update_software(
    software_id: int,
    software_data: SoftwareUpdateRequest,
    request: Request,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Actualizar software existente

    **Requiere:** Rol de Gestor o Administrador
    """
    result = await db.execute(
        select(Software).where(Software.id == software_id)
    )
    software = result.scalar_one_or_none()

    if not software:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Software with id {software_id} not found"
        )

    if software_data.name is not None:
        software.name = software_data.name

    if software_data.vendor is not None:
        software.vendor = software_data.vendor

    if software_data.category is not None:
        software.category = software_data.category

    if software_data.description is not None:
        software.description = software_data.description

    if software_data.website is not None:
        software.website = str(software_data.website)

    await db.commit()
    await db.refresh(software)

    await AuditService.log_action(
        db=db,
        user=current_user,
        action=AuditAction.UPDATE,
        resource_type="software",
        resource_id=software_id,
        ip_address=_get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    try:
        request.state.audit_logged = True
    except Exception:
        pass

    return software


@router.delete("/{software_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_software(
    software_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Eliminar software

    **Requiere:** Rol de Administrador

    - Elimina software y todos sus instaladores/licencias asociados (cascade)
    - Los archivos físicos en FTP deben eliminarse manualmente o con tarea programada
    """
    result = await db.execute(
        select(Software).where(Software.id == software_id)
    )
    software = result.scalar_one_or_none()

    if not software:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Software with id {software_id} not found"
        )

    # Guardar ID antes de eliminar para el log
    software_id_for_log = software.id
    software_name = software.name

    await db.delete(software)
    await db.commit()

    await AuditService.log_action(
        db=db,
        user=current_user,
        action=AuditAction.DELETE,
        resource_type="software",
        resource_id=software_id_for_log,
        ip_address=_get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        details={"name": software_name}
    )
    try:
        request.state.audit_logged = True
    except Exception:
        pass

    return None


@router.get("/{software_id}/installers", response_model=dict)
async def list_software_installers(
    software_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Listar instaladores de un software específico

    **Público:** Todos los usuarios pueden consultar
    """
    result = await db.execute(
        select(Software).where(Software.id == software_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Software with id {software_id} not found"
        )

    query = select(Software).where(Software.id == software_id)
    query = query.options(selectinload(Software.installers))

    result = await db.execute(query)
    software = result.scalar_one()

    return {
        "items": [InstallerResponse.model_validate(i) for i in software.installers],
        "total": len(software.installers)
    }