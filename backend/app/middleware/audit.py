"""
Middleware de auditoría - Registro automático de operaciones
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Callable, Optional
import logging
from app.models import AuditLog, AuditAction, User
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware para registrar automáticamente operaciones en audit log
    
    Registra:
    - Logins/logouts
    - Operaciones CRUD en recursos críticos
    - Descargas de instaladores
    - Acceso a licencias
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Procesa request y registra en audit log si corresponde"""
        
        # Determinar acción candidata antes de ejecutar el request para diagnóstico
        audit_action = self._get_audit_action(request)
        if audit_action:
            logger.info(f"Audit action detected: {audit_action.value} for {request.method} {request.url.path}")
        else:
            logger.debug(f"No audit action for {request.method} {request.url.path}")
        
        # Ejecutar request
        response = await call_next(request)
        
        # Decidir si crear registro:
        # - Siempre registrar intentos de login/logout (incluso si fallaron)
        # - Para otras acciones registrar solo si la respuesta fue 2xx
        try:
            if audit_action in (AuditAction.LOGIN, AuditAction.LOGOUT):
                logger.info(f"Creating audit log for {audit_action.value} with status {response.status_code}")
                await self._log_request(request, response)
            elif 200 <= response.status_code < 300:
                await self._log_request(request, response)
            else:
                logger.debug(f"Skipping audit for {request.method} {request.url.path} with status {response.status_code}")
        except Exception as e:
            logger.error(f"Error while attempting to create audit log in dispatch: {e}", exc_info=True)
        
        return response
    
    async def _log_request(self, request: Request, response: Response):
        """
        Registra request en audit log si corresponde
        
        Args:
            request: Request de FastAPI
            response: Response generado
        """
        try:
            # Determinar si debe auditarse
            audit_action = self._get_audit_action(request)
            
            if not audit_action:
                logger.debug(f"_log_request: no audit_action for {request.method} {request.url.path}")
                return  # No auditar este request
            
            # Evitar duplicados si el handler ya registró el evento
            if getattr(request.state, "audit_logged", False):
                logger.debug("_log_request: request already logged by handler, skipping")
                return

            # Obtener usuario desde request state (inyectado por get_current_user)
            user = getattr(request.state, "user", None)
            
            if not user:
                # Intentar obtener usuario del token (para endpoints sin dependency explícito)
                user = await self._extract_user_from_request(request)
            
            # Si no hay usuario en endpoints protegidos, no auditar
            if not user and audit_action != AuditAction.LOGIN:
                logger.debug(f"_log_request: no user found and action {audit_action} requires authenticated user -> skipping")
                return
            
            # Extraer información del recurso
            resource_info = self._extract_resource_info(request)
            
            # Crear log de auditoría
            await self._create_audit_log(
                user=user,
                action=audit_action,
                resource_type=resource_info.get("type"),
                resource_id=resource_info.get("id"),
                ip_address=self._get_client_ip(request),
                user_agent=request.headers.get("user-agent"),
                details=resource_info.get("details")
            )
            
        except Exception as e:
            # No fallar el request si el audit falla
            logger.error(f"Error in audit middleware: {e}", exc_info=True)
    
    def _get_audit_action(self, request: Request) -> Optional[AuditAction]:
        """
        Determina la acción de auditoría según el request
        
        Args:
            request: Request de FastAPI
            
        Returns:
            AuditAction o None si no debe auditarse
        """
        path = request.url.path
        method = request.method
        
        # Login/Logout
        if path == "/api/v1/auth/login" and method == "POST":
            return AuditAction.LOGIN
        
        if path == "/api/v1/auth/logout" and method == "POST":
            return AuditAction.LOGOUT
        
        # Descargas de instaladores
        if "/installers/" in path and path.endswith("/download") and method == "GET":
            return AuditAction.DOWNLOAD
        
        # Acceso a licencias (GET individual con clave descifrada)
        if path.startswith("/api/v1/licenses/") and method == "GET" and path.count("/") == 4:
            return AuditAction.VIEW_LICENSE
        
        # CRUD Operations
        if method == "POST":
            return AuditAction.CREATE
        elif method == "PUT" or method == "PATCH":
            return AuditAction.UPDATE
        elif method == "DELETE":
            return AuditAction.DELETE
        
        # No auditar GET requests (excepto los específicos arriba)
        return None
    
    def _extract_resource_info(self, request: Request) -> dict:
        """
        Extrae información del recurso afectado
        
        Args:
            request: Request de FastAPI
            
        Returns:
            dict: Información del recurso
        """
        path = request.url.path
        parts = [p for p in path.split("/") if p]
        
        info = {
            "type": None,
            "id": None,
            "details": {}
        }
        
        try:
            # Determinar tipo de recurso
            if "/users/" in path:
                info["type"] = "user"
            elif "/software/" in path:
                info["type"] = "software"
            elif "/installers/" in path:
                info["type"] = "installer"
            elif "/licenses/" in path:
                info["type"] = "license"
            
            # Extraer ID del recurso (generalmente último segmento numérico)
            for part in reversed(parts):
                if part.isdigit():
                    info["id"] = int(part)
                    break
            
            # Detalles adicionales según método
            if request.method == "POST" and hasattr(request.state, "request_body"):
                info["details"]["body"] = request.state.request_body
            
        except Exception as e:
            logger.error(f"Error extracting resource info: {e}")
        
        return info
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Obtiene IP real del cliente considerando proxies
        
        Args:
            request: Request de FastAPI
            
        Returns:
            str: IP del cliente
        """
        # Intentar obtener IP de headers de proxy
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback a client.host
        return request.client.host if request.client else "unknown"
    
    async def _extract_user_from_request(self, request: Request) -> Optional[User]:
        """
        Intenta extraer usuario del token JWT en el request
        
        Args:
            request: Request de FastAPI
            
        Returns:
            User o None
        """
        try:
            from app.services.auth_service import AuthService
            from sqlalchemy import select
            
            # Obtener token del header Authorization
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None
            
            token = auth_header[7:]  # Remover "Bearer "
            
            # Decodificar token
            payload = AuthService.decode_token(token)
            if not payload:
                return None
            
            user_id = payload.get("sub")
            if not user_id:
                return None
            
            # Obtener usuario de BD
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(User).where(User.id == int(user_id))
                )
                user = result.scalar_one_or_none()
                return user
            
        except Exception as e:
            logger.error(f"Error extracting user from request: {e}")
            return None
    
    async def _create_audit_log(
        self,
        user: Optional[User],
        action: AuditAction,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[dict] = None
    ):
        """
        Crea registro en audit_logs
        
        Args:
            user: Usuario que realizó la acción
            action: Acción realizada
            resource_type: Tipo de recurso afectado
            resource_id: ID del recurso
            ip_address: IP del cliente
            user_agent: User agent del cliente
            details: Detalles adicionales
        """
        try:
            async with AsyncSessionLocal() as db:
                audit_log = AuditLog(
                    user_id=user.id if user else None,
                    username=user.username if user else "anonymous",
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details=details
                )
                
                db.add(audit_log)
                await db.commit()
                
                logger.info(
                    f"Audit log created: {action.value} by {audit_log.username} "
                    f"on {resource_type}:{resource_id}"
                )
                
        except Exception as e:
            logger.error(f"Error creating audit log: {e}", exc_info=True)


class AuditService:
    """Servicio para crear logs de auditoría manualmente"""
    
    @staticmethod
    async def log_action(
        db: AsyncSession,
        user: Optional[User] = None,
        username: Optional[str] = None,
        action: AuditAction = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[dict] = None
    ):
        """
        Registra acción en audit log
        
        Uso en routers:
            await AuditService.log_action(
                db=db,
                user=current_user,
                action=AuditAction.VIEW_LICENSE,
                resource_type="license",
                resource_id=license_id
            )

        Also supports logging by username for unauthenticated events (e.g. failed login):
            await AuditService.log_action(
                db=db,
                username="unknown_user",
                action=AuditAction.LOGIN,
                details={"success": False}
            )
        """
        try:
            audit_log = AuditLog(
                user_id=user.id if user else None,
                username=(user.username if user else username if username else "anonymous"),
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details
            )
            
            db.add(audit_log)
            await db.commit()
            
            actor = user.username if user else (username if username else "anonymous")
            logger.info(
                f"Manual audit log: {action.value} by {actor} "
                f"on {resource_type}:{resource_id}"
            )
            
        except Exception as e:
            logger.error(f"Error in manual audit log: {e}")
            # No propagar el error para no afectar la operación principal


# Instancia global del servicio
audit_service = AuditService()