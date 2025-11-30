"""
Router de gestión de software
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
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
from app.models import Software, User, UserRole
from app.dependencies.auth import get_current_user, require_manager, require_admin
from app.config import settings

router = APIRouter(tags=["Software"])


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
    
    **Filtros:**
    - `category`: Filtrar por categoría exacta
    - `vendor`: Filtrar por proveedor
    - `search`: Búsqueda en nombre o descripción
    """
    # Construir query base
    query = select(Software)
    
    # Aplicar filtros
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
    
    # Obtener total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    # Aplicar paginación
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Software.name)
    
    # Ejecutar query
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
    # Cargar software con relaciones
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
    
    # Construir respuesta
    response_data = SoftwareDetailResponse.model_validate(software)
    
    # Ocultar licencias si no es admin
    if current_user.role != UserRole.ADMIN:
        response_data.licenses = None
    
    return response_data


@router.post("", response_model=SoftwareResponse, status_code=status.HTTP_201_CREATED)
async def create_software(
    software_data: SoftwareCreateRequest,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Crear nuevo software
    
    **Requiere:** Rol de Gestor o Administrador
    """
    # Verificar que no exista software con mismo nombre y vendor
    result = await db.execute(
        select(Software).where(
            Software.name == software_data.name,
            Software.vendor == software_data.vendor
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Software '{software_data.name}' from vendor '{software_data.vendor}' already exists"
        )
    
    # Crear software
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
    
    return new_software


@router.put("/{software_id}", response_model=SoftwareResponse)
async def update_software(
    software_id: int,
    software_data: SoftwareUpdateRequest,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Actualizar software existente
    
    **Requiere:** Rol de Gestor o Administrador
    """
    # Obtener software
    result = await db.execute(
        select(Software).where(Software.id == software_id)
    )
    software = result.scalar_one_or_none()
    
    if not software:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Software with id {software_id} not found"
        )
    
    # Actualizar campos
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
    
    return software


@router.delete("/{software_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_software(
    software_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Eliminar software
    
    **Requiere:** Rol de Administrador
    
    - Elimina software y todos sus instaladores/licencias asociados (cascade)
    - Los archivos físicos en FTP deben eliminarse manualmente o con tarea programada
    """
    # Obtener software
    result = await db.execute(
        select(Software).where(Software.id == software_id)
    )
    software = result.scalar_one_or_none()
    
    if not software:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Software with id {software_id} not found"
        )
    
    # Eliminar (cascade eliminará installers y licenses)
    await db.delete(software)
    await db.commit()
    
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
    # Verificar que el software existe
    result = await db.execute(
        select(Software).where(Software.id == software_id)
    )
    software = result.scalar_one_or_none()
    
    if not software:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Software with id {software_id} not found"
        )
    
    # Cargar instaladores
    query = select(Software).where(Software.id == software_id)
    query = query.options(selectinload(Software.installers))
    
    result = await db.execute(query)
    software = result.scalar_one()
    
    return {
        "items": [InstallerResponse.model_validate(i) for i in software.installers],
        "total": len(software.installers)
    }
