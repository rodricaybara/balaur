"""
Router de gestión de instaladores
"""
from fastapi import APIRouter, Depends, HTTPException, status
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
from app.middleware.audit import audit_service
from app.models import AuditAction

router = APIRouter(tags=["Installers"])


async def file_streamer(file_path: str, chunk_size: int = 1024 * 1024):
    """
    Generador para streaming de archivos grandes
    Lee el archivo en chunks para no cargar todo en memoria
    """
    async with aiofiles.open(file_path, mode='rb') as f:
        while True:
            chunk = await f.read(chunk_size)
            if not chunk:
                break
            yield chunk


@router.post("", response_model=InstallerResponse, status_code=status.HTTP_201_CREATED)
async def register_installer(
    installer_data: InstallerCreateRequest,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Registrar instalador después de subirlo vía FTP
    
    **Requiere:** Rol de Gestor o Administrador
    
    **Flujo:**
    1. Usuario sube archivo a FTP inbox
    2. Watcher procesa, valida SHA-256 y mueve a repository
    3. Usuario llama este endpoint para registrar en BD
    
    El campo `filename` debe corresponder al archivo procesado en repository
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
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Installer with SHA-256 hash {installer_data.sha256_hash} already exists"
        )
    
    # Construir path en FTP repository: repository/software_id/version/filename
    ftp_relative_path = f"{installer_data.software_id}/{installer_data.version}/{installer_data.filename}"
    
    # Verificar que el archivo existe en el FTP (opcional, depende de implementación)
    # ftp_full_path = Path(settings.ftp_repository) / ftp_relative_path
    # if not ftp_full_path.exists():
    #     raise HTTPException(
    #         status_code=status.HTTP_404_NOT_FOUND,
    #         detail=f"File not found in FTP repository: {ftp_relative_path}"
    #     )
    
    # Crear instalador
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
    
    return new_installer


@router.get("/{installer_id}", response_model=InstallerResponse)
async def get_installer(
    installer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener información del instalador
    
    **Público:** Todos los usuarios autenticados pueden consultar
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Descargar instalador mediante streaming
    
    **Requiere:** Rol de Usuario o superior (no Invitados)
    
    - Descarga archivo del FTP repository
    - Usa streaming para archivos grandes
    - Incrementa contador de descargas
    - Registra descarga en audit log (implementar en middleware)
    """
    # Verificar permisos (Usuario o superior)
    if not current_user.has_permission(UserRole.USER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Download requires User role or higher"
        )
    
    # Obtener instalador
    result = await db.execute(
        select(InstallerFile).where(InstallerFile.id == installer_id)
    )
    installer = result.scalar_one_or_none()
    
    if not installer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Installer with id {installer_id} not found"
        )
    
    # Construir path completo del archivo
    file_path = Path(settings.ftp_repository) / installer.ftp_path
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found in storage: {installer.filename}"
        )
    
    # Incrementar contador de descargas
    installer.download_count += 1
    await db.commit()
    
    # TODO: Registrar en audit log (implementar en middleware o aquí)
    # await audit_service.log_download(current_user, installer)
    
    # Retornar streaming response
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
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Eliminar instalador
    
    **Requiere:** Rol de Administrador
    
    - Elimina registro de BD
    - Elimina archivo físico del FTP repository
    """
    # Obtener instalador
    result = await db.execute(
        select(InstallerFile).where(InstallerFile.id == installer_id)
    )
    installer = result.scalar_one_or_none()
    
    if not installer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Installer with id {installer_id} not found"
        )
    
    # Construir path del archivo
    file_path = Path(settings.ftp_repository) / installer.ftp_path
    
    # Eliminar archivo físico si existe
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception as e:
            # Log error pero continuar con eliminación de BD
            print(f"Error deleting file {file_path}: {e}")
    
    # Eliminar de BD
    await db.delete(installer)
    await db.commit()
    
    return None