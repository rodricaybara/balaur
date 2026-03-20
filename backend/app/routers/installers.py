"""
Router de gestión de instaladores
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pathlib import Path
import aiofiles
from app.database import get_db
from app.schemas import InstallerResponse, InstallerCreateRequest
from app.models import InstallerFile, Software, User, UserRole
from app.dependencies.auth import get_current_user, require_manager, require_admin
from app.config import settings
from app.services.ftp_watcher import ftp_watcher
from app.middleware.audit import AuditService
from app.models import AuditAction

router = APIRouter(tags=["Installers"])


async def file_streamer(file_path: str, chunk_size: int = 1024 * 1024):
    """
    Generador para streaming de archivos grandes.
    Lee el archivo en chunks para no cargar todo en memoria.
    """
    async with aiofiles.open(file_path, mode='rb') as f:
        while True:
            chunk = await f.read(chunk_size)
            if not chunk:
                break
            yield chunk


def _get_client_ip(request: Request) -> str:
    """Obtiene IP real del cliente considerando proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return (
        request.headers.get("X-Real-IP") or
        (request.client.host if request.client else "unknown")
    )


@router.get("", response_model=list[InstallerResponse])
async def list_installers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Listar todos los instaladores registrados.

    **Requiere:** Cualquier usuario autenticado
    """
    result = await db.execute(select(InstallerFile))
    installers = result.scalars().all()
    return installers


@router.post("", response_model=InstallerResponse, status_code=status.HTTP_201_CREATED)
async def register_installer(
    installer_data: InstallerCreateRequest,
    request: Request,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Registrar instalador después de subirlo vía FTP.

    **Requiere:** Rol de Gestor o Administrador

    **Flujo:**
    1. Usuario sube archivo a FTP inbox
    2. Watcher procesa, valida SHA-256 y mueve a processing
    3. Usuario llama este endpoint para registrar en BD y mover a repository

    El campo `filename` debe corresponder al archivo validado en processing.
    """
    # Verificar que el software existe
    result = await db.execute(
        select(Software).where(Software.id == installer_data.software_id)
    )
    software = result.scalar_one_or_none()

    if not software:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Software with id {installer_data.software_id} not found"
        )

    # Verificar que no exista instalador con mismo hash
    result = await db.execute(
        select(InstallerFile).where(InstallerFile.sha256_hash == installer_data.sha256_hash)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Installer with SHA-256 hash {installer_data.sha256_hash} already exists"
        )

    # Verificar que el archivo existe en processing
    processing_file = Path(settings.ftp_inbox_processing) / installer_data.filename
    if not processing_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found in processing: {installer_data.filename}"
        )

    # Mover archivo a repository
    try:
        await ftp_watcher.organize_file_in_repository(
            processing_file=processing_file,
            software_id=installer_data.software_id,
            version=installer_data.version,
            final_filename=installer_data.filename
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to organize file in repository: {str(e)}"
        )

    ftp_relative_path = f"{installer_data.software_id}/{installer_data.version}/{installer_data.filename}"

    new_installer = InstallerFile(
        software_id=installer_data.software_id,
        version=installer_data.version,
        filename=installer_data.filename,
        file_size=installer_data.file_size,
        sha256_hash=installer_data.sha256_hash,
        ftp_path=ftp_relative_path,
        architecture=installer_data.architecture,
        platform=installer_data.platform,
        notes=installer_data.notes,
        uploaded_by=current_user.id
    )

    db.add(new_installer)
    await db.commit()
    await db.refresh(new_installer)

    # Logging manual explícito — no depender del middleware para CREATE
    await AuditService.log_action(
        db=db,
        user=current_user,
        action=AuditAction.CREATE,
        resource_type="installer",
        resource_id=new_installer.id,
        ip_address=_get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    try:
        request.state.audit_logged = True
    except Exception:
        pass

    return new_installer


@router.get("/{installer_id}", response_model=InstallerResponse)
async def get_installer(
    installer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener información de un instalador.

    **Requiere:** Cualquier usuario autenticado
    """
    result = await db.execute(
        select(InstallerFile).where(InstallerFile.id == installer_id)
    )
    installer = result.scalar_one_or_none()

    if not installer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Installer with id {installer_id} not found"
        )

    return installer


@router.get("/{installer_id}/download")
async def download_installer(
    installer_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Descargar instalador mediante streaming.

    **Requiere:** Rol de Usuario o superior (no Invitados)

    - Descarga archivo del FTP repository
    - Usa streaming para archivos grandes
    - Incrementa contador de descargas
    - Registra descarga en audit log
    """
    if not current_user.has_permission(UserRole.USER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Download requires User role or higher"
        )

    result = await db.execute(
        select(InstallerFile).where(InstallerFile.id == installer_id)
    )
    installer = result.scalar_one_or_none()

    if not installer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Installer with id {installer_id} not found"
        )

    file_path = Path(settings.ftp_repository) / installer.ftp_path
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found in storage: {installer.filename}"
        )

    # Incrementar contador de descargas
    installer.download_count += 1
    await db.commit()

    # Logging manual explícito — crítico para trazabilidad de descargas
    await AuditService.log_action(
        db=db,
        user=current_user,
        action=AuditAction.DOWNLOAD,
        resource_type="installer",
        resource_id=installer.id,
        ip_address=_get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        details={"filename": installer.filename}
    )
    try:
        request.state.audit_logged = True
    except Exception:
        pass

    return StreamingResponse(
        file_streamer(str(file_path)),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{installer.filename}"',
            "Content-Length": str(installer.file_size),
            "X-SHA256": installer.sha256_hash
        }
    )


@router.delete("/{installer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_installer(
    installer_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Eliminar instalador.

    **Requiere:** Rol de Administrador

    - Elimina registro de BD
    - Elimina archivo físico del FTP repository
    """
    result = await db.execute(
        select(InstallerFile).where(InstallerFile.id == installer_id)
    )
    installer = result.scalar_one_or_none()

    if not installer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Installer with id {installer_id} not found"
        )

    # Guardar datos para el log antes de eliminar
    installer_id_for_log = installer.id
    installer_filename = installer.filename

    file_path = Path(settings.ftp_repository) / installer.ftp_path
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception as e:
            # Log error pero continuar con eliminación de BD (comportamiento existente)
            import logging as _logging
            _logging.getLogger(__name__).error(f"Error deleting file {file_path}: {e}")

    await db.delete(installer)
    await db.commit()

    # Logging manual explícito
    await AuditService.log_action(
        db=db,
        user=current_user,
        action=AuditAction.DELETE,
        resource_type="installer",
        resource_id=installer_id_for_log,
        ip_address=_get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        details={"filename": installer_filename}
    )
    try:
        request.state.audit_logged = True
    except Exception:
        pass

    return None