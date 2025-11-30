"""
Servicio FTP Watcher - Monitoreo de inbox y procesamiento de archivos
"""
import asyncio
import aiofiles
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.config import settings
from app.services.file_service import FileService

logger = logging.getLogger(__name__)


class FTPWatcher:
    """
    Watcher que monitorea inbox FTP y procesa archivos nuevos
    
    Flujo:
    1. Escanea inbox/pending cada X minutos
    2. Mueve archivos a inbox/processing
    3. Valida archivo (extensión, tamaño, SHA-256)
    4. Si válido: mueve a repository/software_id/version/
    5. Si inválido: mueve a quarantine/
    """
    
    def __init__(self):
        self.scheduler: AsyncIOScheduler = None
        self.is_running = False
        self.file_service = FileService()
        
        # Tracking de ejecuciones
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.last_run_stats: dict = {
            "processed": 0,
            "failed": 0,
            "duration_seconds": 0
        }
        self.recent_errors: list = []  # Últimos 5 errores
        self.max_errors_stored: int = 5
        
        # Paths
        self.inbox_pending = Path(settings.ftp_inbox_pending)
        self.inbox_processing = Path(settings.ftp_inbox_processing)
        self.repository = Path(settings.ftp_repository)
        self.quarantine = Path(settings.ftp_quarantine)
        
        # Asegurar que los directorios existen
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Crea directorios FTP si no existen"""
        for directory in [self.inbox_pending, self.inbox_processing, 
                         self.repository, self.quarantine]:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured directory exists: {directory}")
    
    def _add_error(self, error_msg: str, file_name: Optional[str] = None):
        """Registra un error reciente"""
        error_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "message": error_msg,
            "file": file_name
        }
        
        self.recent_errors.insert(0, error_entry)
        
        # Mantener solo los últimos N errores
        if len(self.recent_errors) > self.max_errors_stored:
            self.recent_errors = self.recent_errors[:self.max_errors_stored]
    
    async def scan_pending_files(self) -> List[Path]:
        """
        Escanea inbox/pending en busca de archivos nuevos
        
        Returns:
            List[Path]: Lista de archivos encontrados
        """
        try:
            files = []
            for file_path in self.inbox_pending.iterdir():
                if file_path.is_file():
                    # Ignorar archivos ocultos y temporales
                    if not file_path.name.startswith('.') and not file_path.name.endswith('.tmp'):
                        files.append(file_path)
            
            return files
        except Exception as e:
            error_msg = f"Error scanning pending files: {e}"
            logger.error(error_msg)
            self._add_error(error_msg)
            return []
    
    async def process_file(self, file_path: Path) -> bool:
        """
        Procesa un archivo individual
        
        Args:
            file_path: Ruta del archivo en inbox/pending
            
        Returns:
            bool: True si el procesamiento fue exitoso
        """
        logger.info(f"Processing file: {file_path.name}")
        
        try:
            # 1. Mover a processing
            processing_path = self.inbox_processing / file_path.name
            move_success = await self.file_service.move_file(file_path, processing_path)
            
            if not move_success:
                error_msg = f"Failed to move file to processing: {file_path.name}"
                logger.error(error_msg)
                self._add_error(error_msg, file_path.name)
                return False
            
            # 2. Validar archivo
            is_valid, message, metadata = await self.file_service.validate_file(processing_path)
            
            if not is_valid:
                # Archivo inválido -> quarantine
                logger.warning(f"File validation failed: {message}")
                self._add_error(f"Validation failed: {message}", file_path.name)
                await self.file_service.quarantine_file(processing_path, message)
                return False
            
            # 3. Archivo válido - preparar para repository
            # NOTA: En esta versión, dejamos el archivo en processing
            # El usuario debe llamar POST /installers para registrarlo en BD
            # y especificar software_id/version para organizarlo correctamente
            
            logger.info(f"File validated successfully: {file_path.name}")
            logger.info(f"  - Size: {metadata['file_size'] / (1024*1024):.2f} MB")
            logger.info(f"  - SHA-256: {metadata['sha256_hash']}")
            logger.info(f"  - Location: {processing_path}")

            # NUEVO: Guardar SHA-256 en archivo para consultas posteriores
            sha256_file = processing_path.with_suffix(processing_path.suffix + '.sha256')
            try:
                async with aiofiles.open(sha256_file, 'w') as f:
                    await f.write(metadata['sha256_hash'])
                logger.info(f"  - SHA-256 saved to: {sha256_file.name}")
            except Exception as e:
                logger.error(f"Failed to save SHA-256 file: {e}")
                # No es crítico, continuar
            
            logger.info(f"  -> Ready for registration via API")
            
            return True
            
        except Exception as e:
            error_msg = f"Error processing file {file_path.name}: {e}"
            logger.error(error_msg)
            self._add_error(error_msg, file_path.name)
            
            # Intentar mover a quarantine
            if file_path.exists():
                await self.file_service.quarantine_file(file_path, f"Processing error: {str(e)}")
            
            return False
    
    async def process_all_pending(self):
        """Procesa todos los archivos pendientes"""
        if not settings.watcher_enabled:
            return
        
        # Registrar inicio
        start_time = datetime.utcnow()
        self.last_run = start_time
        
        logger.info("Starting FTP Watcher scan...")
        
        # Escanear archivos pendientes
        pending_files = await self.scan_pending_files()
        
        if not pending_files:
            logger.debug("No pending files found")
            
            # Actualizar stats incluso si no hay archivos
            end_time = datetime.utcnow()
            self.last_run_stats = {
                "processed": 0,
                "failed": 0,
                "duration_seconds": (end_time - start_time).total_seconds()
            }
            return
        
        logger.info(f"Found {len(pending_files)} pending files")
        
        # Procesar cada archivo
        results = {
            "processed": 0,
            "failed": 0
        }
        
        for file_path in pending_files:
            success = await self.process_file(file_path)
            if success:
                results["processed"] += 1
            else:
                results["failed"] += 1
        
        # Actualizar stats de última ejecución
        end_time = datetime.utcnow()
        self.last_run_stats = {
            "processed": results["processed"],
            "failed": results["failed"],
            "duration_seconds": (end_time - start_time).total_seconds()
        }
        
        logger.info(
            f"FTP Watcher scan completed: {results['processed']} processed, "
            f"{results['failed']} failed in {self.last_run_stats['duration_seconds']:.2f}s"
        )
    
    async def organize_file_in_repository(
        self,
        processing_file: Path,
        software_id: int,
        version: str,
        final_filename: str
    ) -> Path:
        """
        Mueve archivo de processing a repository con estructura organizacional
        
        Args:
            processing_file: Archivo en inbox/processing
            software_id: ID del software
            version: Versión del software
            final_filename: Nombre final del archivo
            
        Returns:
            Path: Ruta final en repository
        """
        # Construir path: repository/software_id/version/filename
        final_path = self.repository / str(software_id) / version / final_filename
        
        # Crear directorios
        final_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Mover archivo
        success = await self.file_service.move_file(processing_file, final_path)
        
        if success:
            logger.info(f"File organized in repository: {final_path}")
            return final_path
        else:
            raise Exception(f"Failed to move file to repository: {processing_file}")
    
    def start(self):
        """Inicia el watcher con scheduler"""
        if not settings.watcher_enabled:
            logger.info("FTP Watcher is disabled in configuration")
            return
        
        if self.is_running:
            logger.warning("FTP Watcher is already running")
            return
        
        logger.info("Starting FTP Watcher...")
        logger.info(f"  - Interval: {settings.watcher_interval} seconds")
        logger.info(f"  - Inbox: {self.inbox_pending}")
        logger.info(f"  - Repository: {self.repository}")
        
        # Crear scheduler
        self.scheduler = AsyncIOScheduler()
        
        # Agregar job
        self.scheduler.add_job(
            self.process_all_pending,
            trigger=IntervalTrigger(seconds=settings.watcher_interval),
            id="ftp_watcher",
            name="FTP Watcher - Process Pending Files",
            replace_existing=True
        )
        
        # Iniciar scheduler
        self.scheduler.start()
        self.is_running = True
        
        # Calcular próxima ejecución
        self.next_run = datetime.utcnow() + timedelta(seconds=settings.watcher_interval)
        
        logger.info("FTP Watcher started successfully")
        
        # Ejecutar primera vez inmediatamente
        asyncio.create_task(self.process_all_pending())
    
    def stop(self):
        """Detiene el watcher"""
        if not self.is_running:
            logger.warning("FTP Watcher is not running")
            return
        
        logger.info("Stopping FTP Watcher...")
        
        if self.scheduler:
            self.scheduler.shutdown(wait=True)
            self.scheduler = None
        
        self.is_running = False
        self.next_run = None
        logger.info("FTP Watcher stopped")
    
    async def get_stats(self) -> dict:
        """
        Obtiene estadísticas detalladas del watcher
        
        Returns:
            dict: Estadísticas completas del watcher
        """
        # Calcular próxima ejecución si está corriendo
        next_run_iso = None
        if self.is_running and self.scheduler:
            job = self.scheduler.get_job("ftp_watcher")
            if job and job.next_run_time:
                next_run_iso = job.next_run_time.isoformat()
        
        stats = {
            # Contadores de archivos
            "pending": len([f for f in self.inbox_pending.iterdir() if f.is_file() and not f.name.endswith('.sha256')]) if self.inbox_pending.exists() else 0,
            "processing": len([f for f in self.inbox_processing.iterdir() if f.is_file() and not f.name.endswith('.sha256')]) if self.inbox_processing.exists() else 0,
            "quarantine": len([f for f in self.quarantine.iterdir() if f.is_file() and not f.name.endswith('.sha256')]) if self.quarantine.exists() else 0,
            
            # Estado del watcher
            "is_running": self.is_running,
            "interval_seconds": settings.watcher_interval,
            
            # Información de ejecución
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": next_run_iso,
            
            # Estadísticas de última ejecución
            "last_run_stats": self.last_run_stats,
            
            # Errores recientes
            "recent_errors": self.recent_errors,
            
            # Rutas configuradas
            "paths": {
                "inbox_pending": str(self.inbox_pending),
                "inbox_processing": str(self.inbox_processing),
                "repository": str(self.repository),
                "quarantine": str(self.quarantine)
            }
        }
        
        return stats


# Instancia global del watcher
ftp_watcher = FTPWatcher()


async def start_ftp_watcher():
    """Helper para iniciar watcher desde main.py"""
    ftp_watcher.start()


async def stop_ftp_watcher():
    """Helper para detener watcher desde main.py"""
    ftp_watcher.stop()