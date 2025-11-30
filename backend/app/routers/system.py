"""
Router de endpoints de sistema (watcher, health, etc.)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from pathlib import Path
from datetime import datetime
import logging

from app.schemas.system import (
    PendingFileResponse,
    ProcessingFileResponse,
    WatcherStatsResponse
)
from app.models import User
from app.dependencies.auth import require_manager
from app.config import settings
from app.services.ftp_watcher import ftp_watcher

logger = logging.getLogger(__name__)

router = APIRouter()


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