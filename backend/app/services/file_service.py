"""
Servicio de gestión de archivos y validación
"""
import hashlib
import aiofiles
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class FileService:
    """Servicio para operaciones con archivos"""
    
    @staticmethod
    async def calculate_sha256(file_path: Path, chunk_size: int = 8192) -> str:
        """
        Calcula hash SHA-256 de un archivo de forma asíncrona
        
        Args:
            file_path: Ruta del archivo
            chunk_size: Tamaño del chunk para lectura (bytes)
            
        Returns:
            str: Hash SHA-256 en hexadecimal (64 caracteres)
        """
        sha256_hash = hashlib.sha256()
        
        try:
            async with aiofiles.open(file_path, mode='rb') as f:
                while True:
                    chunk = await f.read(chunk_size)
                    if not chunk:
                        break
                    sha256_hash.update(chunk)
            
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating SHA-256 for {file_path}: {e}")
            raise
    
    @staticmethod
    def validate_file_extension(filename: str) -> bool:
        """
        Valida que la extensión del archivo esté permitida
        
        Args:
            filename: Nombre del archivo
            
        Returns:
            bool: True si la extensión es válida
        """
        file_ext = Path(filename).suffix.lower()
        return file_ext in settings.allowed_installer_extensions or file_ext in settings.allowed_doc_extensions
    
    @staticmethod
    def validate_file_size(file_size: int) -> bool:
        """
        Valida que el tamaño del archivo no exceda el máximo
        
        Args:
            file_size: Tamaño en bytes
            
        Returns:
            bool: True si el tamaño es válido
        """
        max_size_bytes = settings.max_file_size
        return file_size <= max_size_bytes
    
    @staticmethod
    async def validate_file(
        file_path: Path,
        expected_sha256: Optional[str] = None
    ) -> Tuple[bool, str, dict]:
        """
        Validación completa de archivo
        
        Args:
            file_path: Ruta del archivo
            expected_sha256: Hash SHA-256 esperado (opcional)
            
        Returns:
            Tuple[bool, str, dict]: (válido, mensaje, metadata)
        """
        metadata = {
            "filename": file_path.name,
            "validated_at": datetime.utcnow().isoformat(),
            "file_size": 0,
            "sha256_hash": None,
            "extension": None
        }
        
        # Verificar que el archivo existe
        if not file_path.exists():
            return False, f"File not found: {file_path}", metadata
        
        # Validar extensión
        if not FileService.validate_file_extension(file_path.name):
            return False, f"Invalid file extension: {file_path.suffix}", metadata
        
        metadata["extension"] = file_path.suffix.lower()
        
        # Obtener tamaño
        file_size = file_path.stat().st_size
        metadata["file_size"] = file_size
        
        # Validar tamaño
        if not FileService.validate_file_size(file_size):
            max_gb = settings.max_file_size / (1024 ** 3)   
            actual_gb = file_size / (1024 ** 3)
            return False, f"File too large: {actual_gb:.2f}GB (max: {max_gb}GB)", metadata
        
        # Calcular hash SHA-256
        try:
            sha256_hash = await FileService.calculate_sha256(file_path)
            metadata["sha256_hash"] = sha256_hash
        except Exception as e:
            return False, f"Error calculating hash: {str(e)}", metadata
        
        # Verificar hash si se proporcionó
        if expected_sha256 and sha256_hash != expected_sha256.lower():
            return False, f"SHA-256 mismatch. Expected: {expected_sha256}, Got: {sha256_hash}", metadata
        
        return True, "File validation successful", metadata
    
    @staticmethod
    async def move_file(source: Path, destination: Path) -> bool:
        """
        Mueve archivo de origen a destino de forma segura
        
        Args:
            source: Ruta origen
            destination: Ruta destino
            
        Returns:
            bool: True si fue exitoso
        """
        try:
            # Crear directorio destino si no existe
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            # Mover archivo
            source.rename(destination)
            logger.info(f"File moved: {source} -> {destination}")
            return True
            
        except Exception as e:
            logger.error(f"Error moving file {source} to {destination}: {e}")
            return False
    
    @staticmethod
    async def quarantine_file(file_path: Path, reason: str) -> bool:
        """
        Mueve archivo a cuarentena con metadata
        
        Args:
            file_path: Archivo a poner en cuarentena
            reason: Razón de la cuarentena
            
        Returns:
            bool: True si fue exitoso
        """
        try:
            # Construir path en quarantine
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            quarantine_filename = f"{timestamp}_{file_path.name}"
            quarantine_path = Path(settings.ftp_quarantine_path) / quarantine_filename
            
            # Mover archivo
            success = await FileService.move_file(file_path, quarantine_path)
            
            if success:
                # Crear archivo de metadata
                metadata_path = quarantine_path.with_suffix(quarantine_path.suffix + ".meta")
                async with aiofiles.open(metadata_path, mode='w') as f:
                    await f.write(f"Original: {file_path}\n")
                    await f.write(f"Timestamp: {timestamp}\n")
                    await f.write(f"Reason: {reason}\n")
                
                logger.warning(f"File quarantined: {file_path} -> {quarantine_path}")
                logger.warning(f"Quarantine reason: {reason}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error quarantining file {file_path}: {e}")
            return False
    
    @staticmethod
    def get_safe_filename(filename: str) -> str:
        """
        Sanitiza nombre de archivo para evitar path traversal
        
        Args:
            filename: Nombre original
            
        Returns:
            str: Nombre sanitizado
        """
        # Eliminar caracteres peligrosos
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
        sanitized = "".join(c if c in safe_chars else "_" for c in filename)
        
        # Eliminar múltiples puntos consecutivos (evitar ..)
        while ".." in sanitized:
            sanitized = sanitized.replace("..", ".")
        
        return sanitized

    @staticmethod
    async def save_web_upload(file: "UploadFile") -> dict:
        """
        Recibe un UploadFile de FastAPI, lo valida y lo deposita en
        inbox/processing/ con su fichero .sha256 adjunto.

        Reutiliza las reglas de validación existentes (extensión vía
        allowed_installer_extensions, límite vía web_upload_max_size).
        No usa max_file_size — ese límite es exclusivo del flujo FTP.

        Returns:
            dict con filename, sha256, size

        Raises:
            HTTPException 400 — extensión no permitida
            HTTPException 409 — fichero con ese nombre ya existe en processing/
            HTTPException 413 — supera web_upload_max_size
            HTTPException 500 — error de I/O
        """
        from fastapi import HTTPException, status  # import local para no crear dependencia circular

        filename = file.filename or ""

        # Sanitizar nombre — evita path traversal antes de tocar disco
        filename = FileService.get_safe_filename(filename)
        if not filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre del fichero no es válido."
            )

        # Validar extensión — mismas reglas que el watcher FTP
        if not FileService.validate_file_extension(filename):
            allowed = ", ".join(sorted(settings.allowed_installer_extensions))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Extensión no permitida. Extensiones válidas: {allowed}"
            )

        processing_dir = Path(settings.ftp_inbox_processing)
        dest_path      = processing_dir / filename
        sha256_path    = processing_dir / f"{filename}.sha256"

        # Conflicto de nombre — el usuario debe renombrar el fichero
        if dest_path.exists():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Ya existe un fichero llamado '{filename}' en la cola de procesado. "
                    f"Renombra el fichero e inténtalo de nuevo."
                )
            )

        # Escritura en streaming + cálculo SHA-256 simultáneo
        # Nunca cargamos el fichero entero en memoria
        hasher      = hashlib.sha256()
        total_bytes = 0
        chunk_size  = 1024 * 1024  # 1 MB por chunk

        try:
            async with aiofiles.open(dest_path, "wb") as out_file:
                while True:
                    chunk = await file.read(chunk_size)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > settings.web_upload_max_size:
                        # Limpiar el fichero parcial antes de rechazar
                        dest_path.unlink(missing_ok=True)
                        limit_mb = settings.web_upload_max_size // (1024 * 1024)
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=(
                                f"El fichero supera el límite de {limit_mb} MB "
                                f"permitido para subidas web. "
                                f"Para ficheros más grandes usa el acceso FTP."
                            )
                        )
                    hasher.update(chunk)
                    await out_file.write(chunk)

        except HTTPException:
            raise  # re-lanzar tal cual, ya tiene su HTTPException correcta
        except Exception as exc:
            dest_path.unlink(missing_ok=True)
            logger.error(f"Error writing uploaded file '{filename}': {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al escribir el fichero en el servidor."
            )

        sha256_hex = hasher.hexdigest()

        # Escribir .sha256 — misma convención que usa el watcher FTP
        try:
            sha256_path.write_text(sha256_hex)
        except Exception as exc:
            # Si falla el .sha256 el fichero queda huérfano — limpiamos ambos
            dest_path.unlink(missing_ok=True)
            logger.error(f"Error writing .sha256 for '{filename}': {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al escribir el fichero de verificación SHA-256."
            )

        logger.info(
            f"Web upload successful: '{filename}' "
            f"({total_bytes / (1024*1024):.1f} MB) sha256={sha256_hex[:16]}…"
        )

        return {
            "filename": filename,
            "sha256":   sha256_hex,
            "size":     total_bytes,
        }    
    
    @staticmethod
    async def get_file_info(file_path: Path) -> Optional[dict]:
        """
        Obtiene información detallada de un archivo
        
        Args:
            file_path: Ruta del archivo
            
        Returns:
            dict: Información del archivo o None si no existe
        """
        if not file_path.exists():
            return None
        
        stat = file_path.stat()
        
        return {
            "filename": file_path.name,
            "path": str(file_path),
            "size": stat.st_size,
            "size_mb": stat.st_size / (1024 * 1024),
            "size_gb": stat.st_size / (1024 * 1024 * 1024),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "extension": file_path.suffix.lower()
        }


# Instancia global del servicio
file_service = FileService()