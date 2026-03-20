"""
Router de gestión de licencias (solo administradores)
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from math import ceil
from app.database import get_db
from app.schemas import (
    LicenseResponse,
    LicenseDetailResponse,
    LicenseListResponse,
    LicenseCreateRequest,
    LicenseUpdateRequest
)
from app.models import License, Software, User
from app.dependencies.auth import require_admin
from app.services.crypto_service import crypto_service
from app.config import settings
from app.middleware.audit import AuditService
from app.models import AuditAction

router = APIRouter(tags=["Licenses"])


@router.get("", response_model=LicenseListResponse)
async def list_licenses(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(
        settings.default_page_size,
        ge=1,
        le=settings.max_page_size,
        description="Elementos por página"
    ),
    software_id: Optional[int] = Query(None, description="Filtrar por software"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Listar licencias (sin claves descifradas)

    **Requiere:** Rol de Administrador

    **Nota:** Las claves NO se descifran en el listado por seguridad.
    Use GET individual para obtener clave descifrada.
    """
    query = select(License)

    if software_id:
        query = query.where(License.software_id == software_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(License.created_at.desc())

    result = await db.execute(query)
    licenses = result.scalars().all()

    return LicenseListResponse(
        items=[LicenseResponse.model_validate(lic) for lic in licenses],
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total > 0 else 0
    )


@router.get("/{license_id}", response_model=LicenseDetailResponse)
async def get_license(
    license_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener licencia con clave descifrada

    **Requiere:** Rol de Administrador

    **IMPORTANTE:** Este endpoint descifra y retorna la clave de licencia.
    El acceso es auditado automáticamente.
    """
    result = await db.execute(
        select(License).where(License.id == license_id)
    )
    license_obj = result.scalar_one_or_none()

    if not license_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"License with id {license_id} not found"
        )

    # Descifrar clave
    try:
        decrypted_key = crypto_service.decrypt(license_obj.encrypted_key)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to decrypt license key: {str(e)}"
        )

    # Registrar acceso en audit log (CRÍTICO) — logging manual explícito
    forwarded = request.headers.get("X-Forwarded-For")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (
        request.headers.get("X-Real-IP") or
        (request.client.host if request.client else "unknown")
    )

    await AuditService.log_action(
        db=db,
        user=current_user,
        action=AuditAction.VIEW_LICENSE,
        resource_type="license",
        resource_id=license_id,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
        details={
            "software_id": license_obj.software_id,
            "license_type": license_obj.license_type.value
        }
    )

    # Marcar como ya logueado para que el middleware no duplique
    try:
        request.state.audit_logged = True
    except Exception:
        pass

    # Construir respuesta con clave descifrada
    response_data = LicenseDetailResponse.model_validate(license_obj)
    response_data.license_key = decrypted_key

    return response_data


@router.post("", response_model=LicenseResponse, status_code=status.HTTP_201_CREATED)
async def create_license(
    license_data: LicenseCreateRequest,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Crear licencia con cifrado automático de clave

    **Requiere:** Rol de Administrador

    - La clave se cifra automáticamente con AES-GCM
    - Solo se almacena la versión cifrada
    """
    result = await db.execute(
        select(Software).where(Software.id == license_data.software_id)
    )
    software = result.scalar_one_or_none()

    if not software:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Software with id {license_data.software_id} not found"
        )

    try:
        encrypted_key = crypto_service.encrypt(license_data.license_key)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to encrypt license key: {str(e)}"
        )

    new_license = License(
        software_id=license_data.software_id,
        license_type=license_data.license_type,
        encrypted_key=encrypted_key,
        max_activations=license_data.max_activations,
        expiration_date=license_data.expiration_date,
        notes=license_data.notes
    )

    db.add(new_license)
    await db.commit()
    await db.refresh(new_license)

    # Logging manual explícito — no depender del middleware para CREATE
    forwarded = request.headers.get("X-Forwarded-For")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (
        request.headers.get("X-Real-IP") or
        (request.client.host if request.client else "unknown")
    )

    await AuditService.log_action(
        db=db,
        user=current_user,
        action=AuditAction.CREATE,
        resource_type="license",
        resource_id=new_license.id,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
    )
    try:
        request.state.audit_logged = True
    except Exception:
        pass

    return new_license


@router.put("/{license_id}", response_model=LicenseResponse)
async def update_license(
    license_id: int,
    license_data: LicenseUpdateRequest,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Actualizar licencia

    **Requiere:** Rol de Administrador

    - Si se proporciona nueva clave, se cifra automáticamente
    """
    result = await db.execute(
        select(License).where(License.id == license_id)
    )
    license_obj = result.scalar_one_or_none()

    if not license_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"License with id {license_id} not found"
        )

    if license_data.license_type is not None:
        license_obj.license_type = license_data.license_type

    if license_data.license_key is not None:
        try:
            license_obj.encrypted_key = crypto_service.encrypt(license_data.license_key)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to encrypt license key: {str(e)}"
            )

    if license_data.max_activations is not None:
        license_obj.max_activations = license_data.max_activations

    if license_data.expiration_date is not None:
        license_obj.expiration_date = license_data.expiration_date

    if license_data.notes is not None:
        license_obj.notes = license_data.notes

    await db.commit()
    await db.refresh(license_obj)

    # Logging manual explícito
    forwarded = request.headers.get("X-Forwarded-For")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (
        request.headers.get("X-Real-IP") or
        (request.client.host if request.client else "unknown")
    )

    await AuditService.log_action(
        db=db,
        user=current_user,
        action=AuditAction.UPDATE,
        resource_type="license",
        resource_id=license_id,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
    )
    try:
        request.state.audit_logged = True
    except Exception:
        pass

    return license_obj


@router.delete("/{license_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_license(
    license_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Eliminar licencia

    **Requiere:** Rol de Administrador

    - Elimina permanentemente el registro
    - La clave cifrada se pierde irrecuperablemente
    """
    result = await db.execute(
        select(License).where(License.id == license_id)
    )
    license_obj = result.scalar_one_or_none()

    if not license_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"License with id {license_id} not found"
        )

    await db.delete(license_obj)
    await db.commit()

    # Logging manual explícito
    forwarded = request.headers.get("X-Forwarded-For")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (
        request.headers.get("X-Real-IP") or
        (request.client.host if request.client else "unknown")
    )

    await AuditService.log_action(
        db=db,
        user=current_user,
        action=AuditAction.DELETE,
        resource_type="license",
        resource_id=license_id,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
    )
    try:
        request.state.audit_logged = True
    except Exception:
        pass

    return None