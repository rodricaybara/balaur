"""
Router de endpoints de sistema (watcher, health, etc.)
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from typing import List
from pathlib import Path
from datetime import datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.system import (
    PendingFileResponse,
    ProcessingFileResponse,
    WatcherStatsResponse,
    WebUploadResponse,          # ← nuevo
)
from app.models import User
from app.models.audit import AuditAction                     # ← nuevo
from app.dependencies.auth import require_manager
from app.database import get_db                              # ← nuevo
from app.config import settings
from app.services.ftp_watcher import ftp_watcher
from app.services.file_service import file_service           # ← nuevo
from app.middleware.audit import AuditService                # ← nuevo

logger = logging.getLogger(__name__)

router = APIRouter()


# Helper IP — mismo patrón que software.py, installers.py, users.py
def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    return request.client.host if request.client else "unknown"


@router.get("/watcher-stats", response_model=WatcherStatsResponse)
async def get_watcher_stats():
    """
    Obtener estadísticas del FTP Watcher
    
    Retorna información completa sobre el estado del watcher:
    - Contadores de archivos (pending, processing, quarantine)
    - Estado de ejecución
    - Última y próxima ejecución
    - Estadísticas de procesamiento
    - Errores recientes
    
    **Acceso:** Público (no requiere autenticación)
    """
    try:
        stats = await ftp_watcher.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting watcher stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve watcher statistics: {str(e)}"
        )


@router.get("/pending-files", response_model=List[PendingFileResponse])
async def list_pending_files(
    current_user: User = Depends(require_manager)
):
    """
    Listar archivos en inbox/pending
    
    Retorna lista de archivos que han sido subidos vía FTP
    pero aún no han sido procesados por el watcher.
    
    **Requiere:** Rol de Manager o Admin
    
    **Returns:**
    - Lista de archivos con nombre, tamaño y fecha de subida
    """
    try:
        pending_path = Path(settings.ftp_inbox_pending)
        
        # Verificar que el directorio existe
        if not pending_path.exists():
            logger.warning(f"Pending directory does not exist: {pending_path}")
            return []
        
        files = []
        
        # Escanear directorio
        for file_path in pending_path.iterdir():
            if file_path.is_file():
                # Ignorar archivos ocultos y temporales
                if file_path.name.startswith('.') or file_path.name.endswith('.tmp'):
                    continue
                
                try:
                    stat = file_path.stat()
                    
                    file_info = PendingFileResponse(
                        filename=file_path.name,
                        size=stat.st_size,
                        upload_date=datetime.fromtimestamp(stat.st_mtime).isoformat()
                    )
                    
                    files.append(file_info)
                    
                except Exception as e:
                    logger.error(f"Error reading file {file_path.name}: {e}")
                    continue
        
        # Ordenar por fecha de subida (más recientes primero)
        files.sort(key=lambda x: x.upload_date, reverse=True)
        
        logger.info(f"Listed {len(files)} pending files for user {current_user.username}")
        return files
        
    except Exception as e:
        logger.error(f"Error listing pending files: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list pending files: {str(e)}"
        )


@router.get("/processing-files", response_model=List[ProcessingFileResponse])
async def list_processing_files(
    current_user: User = Depends(require_manager)
):
    """
    Listar archivos en inbox/processing
    
    Retorna lista de archivos que han sido validados por el watcher
    y están listos para ser registrados en la base de datos.
    
    Incluye el hash SHA-256 calculado durante la validación.
    
    **Requiere:** Rol de Manager o Admin
    
    **Returns:**
    - Lista de archivos con nombre, tamaño, SHA-256 y fecha de validación
    """
    try:
        processing_path = Path(settings.ftp_inbox_processing)
        
        # Verificar que el directorio existe
        if not processing_path.exists():
            logger.warning(f"Processing directory does not exist: {processing_path}")
            return []
        
        files = []
        
        # Escanear directorio
        for file_path in processing_path.iterdir():
            if file_path.is_file():
                # Ignorar archivos .sha256 y otros metadatos
                if file_path.suffix in ['.sha256', '.meta', '.tmp']:
                    continue
                
                # Ignorar archivos ocultos
                if file_path.name.startswith('.'):
                    continue
                
                try:
                    stat = file_path.stat()
                    
                    # Buscar archivo SHA-256 correspondiente
                    sha256_file = file_path.with_suffix(file_path.suffix + '.sha256')
                    sha256_hash = None
                    
                    if sha256_file.exists():
                        try:
                            with open(sha256_file, 'r') as f:
                                sha256_hash = f.read().strip()
                        except Exception as e:
                            logger.error(f"Error reading SHA-256 file for {file_path.name}: {e}")
                    
                    # Si no hay hash, saltar este archivo (no está completamente procesado)
                    if not sha256_hash:
                        logger.warning(f"No SHA-256 hash found for {file_path.name}, skipping")
                        continue
                    
                    file_info = ProcessingFileResponse(
                        filename=file_path.name,
                        size=stat.st_size,
                        sha256=sha256_hash,
                        validated_date=datetime.fromtimestamp(stat.st_mtime).isoformat()
                    )
                    
                    files.append(file_info)
                    
                except Exception as e:
                    logger.error(f"Error reading file {file_path.name}: {e}")
                    continue
        
        # Ordenar por fecha de validación (más recientes primero)
        files.sort(key=lambda x: x.validated_date, reverse=True)
        
        logger.info(f"Listed {len(files)} processing files for user {current_user.username}")
        return files
        
    except Exception as e:
        logger.error(f"Error listing processing files: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list processing files: {str(e)}"
        )
    
@router.post(
    "/upload-installer",
    response_model=WebUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subir instalador vía web (máx. WEB_UPLOAD_MAX_SIZE)",
)
async def upload_installer_web(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    """
    Sube un fichero instalador desde el navegador y lo deposita en
    inbox/processing/ con su SHA-256 calculado.

    El fichero aparece de inmediato en GET /system/processing-files
    y puede registrarse con POST /installers sin ningún cambio
    en ese flujo existente.

    Límite: WEB_UPLOAD_MAX_SIZE (por defecto 1 GB).
    Para ficheros más grandes usar acceso FTP directo.

    **Requiere:** Rol de Manager o Admin
    """
    result = await file_service.save_web_upload(file)
    response = WebUploadResponse.from_upload_result(result)

    await AuditService.log_action(
        db=db,
        user=current_user,
        action=AuditAction.CREATE,
        resource_type="installer_upload",
        resource_id=None,
        ip_address=_get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        details={
            "filename": response.filename,
            "sha256":   response.sha256,
            "size":     response.size,
            "source":   "web_upload",
        },
    )
    try:
        request.state.audit_logged = True
    except Exception:
        pass

    logger.info(
        f"Web upload registered by {current_user.username}: "
        f"'{response.filename}' ({response.size_mb} MB)"
    )

    return response