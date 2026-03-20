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
    Middleware para registrar automáticamente operaciones en audit log.

    Actúa como capa de seguridad para LOGIN y LOGOUT.
    Para el resto de acciones (CREATE, UPDATE, DELETE, DOWNLOAD, VIEW_LICENSE)
    el logging se realiza explícitamente en cada router; el middleware solo
    actúa si el router no lo ha hecho ya (request.state.audit_logged != True).
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Procesa request y registra en audit log si corresponde"""

        audit_action = self._get_audit_action(request)
        if audit_action:
            logger.debug(f"Audit candidate: {audit_action.value} for {request.method} {request.url.path}")

        response = await call_next(request)

        try:
            if audit_action is None:
                return response

            # Si el router ya registró el evento, no duplicar
            if getattr(request.state, "audit_logged", False):
                logger.debug(f"Skipping middleware audit — already logged by router: {request.url.path}")
                return response

            # Registrar siempre login/logout (incluso si fallaron)
            # Para el resto solo registrar si fue exitoso
            if audit_action in (AuditAction.LOGIN, AuditAction.LOGOUT):
                await self._log_request(request, response, audit_action)
            elif 200 <= response.status_code < 300:
                await self._log_request(request, response, audit_action)
            else:
                logger.debug(
                    f"Skipping audit for {request.method} {request.url.path} "
                    f"with status {response.status_code}"
                )
        except Exception as e:
            logger.error(f"Error in audit middleware dispatch: {e}", exc_info=True)

        return response

    async def _log_request(self, request: Request, response: Response, audit_action: AuditAction):
        """
        Registra request en audit log.

        audit_action se recibe ya calculado para no llamar a _get_audit_action dos veces.
        """
        try:
            # Obtener usuario desde request.state (inyectado por get_current_user si existe)
            user = getattr(request.state, "user", None)

            if not user:
                user = await self._extract_user_from_request(request)

            if not user:
                logger.info(
                    f"Audit middleware: no user resolved for {audit_action.value} "
                    f"on {request.url.path} — logging as anonymous"
                )

            # Extraer información del recurso ANTES de usarla en el log
            resource_info = self._extract_resource_info(request)

            logger.debug(
                f"Audit middleware writing: action={audit_action.value} "
                f"user={user.username if user else 'anonymous'} "
                f"resource={resource_info.get('type')}:{resource_info.get('id')} "
                f"ip={self._get_client_ip(request)}"
            )

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
            logger.error(f"Error in audit middleware _log_request: {e}", exc_info=True)

    def _get_audit_action(self, request: Request) -> Optional[AuditAction]:
        """
        Determina la acción de auditoría según el request.

        Returns:
            AuditAction o None si no debe auditarse
        """
        path = request.url.path
        method = request.method

        # Login / Logout
        if path == "/api/v1/auth/login" and method == "POST":
            return AuditAction.LOGIN

        if path == "/api/v1/auth/logout" and method == "POST":
            return AuditAction.LOGOUT

        # Descargas de instaladores: /api/v1/installers/{id}/download
        if "/installers/" in path and path.endswith("/download") and method == "GET":
            return AuditAction.DOWNLOAD

        # Acceso individual a licencia: /api/v1/licenses/{id}
        # path.count("/") == 4 → ["", "api", "v1", "licenses", "{id}"]
        if path.startswith("/api/v1/licenses/") and method == "GET" and path.count("/") == 4:
            return AuditAction.VIEW_LICENSE

        # CRUD genérico
        if method == "POST":
            return AuditAction.CREATE
        if method in ("PUT", "PATCH"):
            return AuditAction.UPDATE
        if method == "DELETE":
            return AuditAction.DELETE

        # GETs de listado y otros no se auditan a nivel middleware
        return None

    def _extract_resource_info(self, request: Request) -> dict:
        """
        Extrae tipo e ID del recurso afectado a partir de la URL.
        """
        path = request.url.path
        parts = [p for p in path.split("/") if p]

        info: dict = {
            "type": None,
            "id": None,
            "details": {}
        }

        try:
            if "/users/" in path or path.endswith("/users"):
                info["type"] = "user"
            elif "/software/" in path or path.endswith("/software"):
                info["type"] = "software"
            elif "/installers/" in path or path.endswith("/installers"):
                info["type"] = "installer"
            elif "/licenses/" in path or path.endswith("/licenses"):
                info["type"] = "license"

            # Extraer ID: último segmento numérico de la ruta
            for part in reversed(parts):
                if part.isdigit():
                    info["id"] = int(part)
                    break

        except Exception as e:
            logger.error(f"Error extracting resource info: {e}")

        return info

    def _get_client_ip(self, request: Request) -> str:
        """Obtiene IP real del cliente considerando proxies."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    async def _extract_user_from_request(self, request: Request) -> Optional[User]:
        """
        Intenta extraer el usuario del token JWT cuando el router no lo
        ha inyectado en request.state.user.
        Abre su propia sesión de BD para no interferir con la sesión del router.
        """
        try:
            from app.services.auth_service import AuthService
            from sqlalchemy import select

            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None

            token = auth_header[7:]
            payload = AuthService.decode_token(token)
            if not payload:
                return None

            user_id = payload.get("sub")
            if not user_id:
                return None

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(User).where(User.id == int(user_id))
                )
                return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error extracting user from JWT in middleware: {e}")
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
        """Persiste un registro en audit_logs con su propia sesión de BD."""
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
                    f"Audit log created (middleware): {action.value} "
                    f"by {audit_log.username} on {resource_type}:{resource_id}"
                )

        except Exception as e:
            logger.error(f"Error creating audit log in middleware: {e}", exc_info=True)


class AuditService:
    """
    Servicio para crear logs de auditoría manualmente desde los routers.

    Uso estándar en un endpoint:
        await AuditService.log_action(
            db=db,
            user=current_user,
            action=AuditAction.VIEW_LICENSE,
            resource_type="license",
            resource_id=license_id,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
        )
    """

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
        Registra acción en audit log usando la sesión de BD del router.

        Acepta `username` como alternativa a `user` para eventos no autenticados
        (ej. login fallido).
        """
        try:
            resolved_username = (
                user.username if user
                else username if username
                else "anonymous"
            )

            audit_log = AuditLog(
                user_id=user.id if user else None,
                username=resolved_username,
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
                f"Audit log created (manual): {action.value} "
                f"by {resolved_username} on {resource_type}:{resource_id}"
            )

        except Exception as e:
            logger.error(f"Error in manual audit log: {e}", exc_info=True)
            # No propagar para no afectar la operación principal


# Instancia global del servicio (compatibilidad con routers que lo importan)
audit_service = AuditService()