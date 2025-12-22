"""
Router de autenticación
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.schemas import LoginRequest, RefreshRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthService
from app.dependencies.auth import get_current_user
from app.models import User, AuditAction
from app.middleware.audit import AuditService

router = APIRouter(tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """
    Iniciar sesión con credenciales LDAP/AD o locales
    
    - Autentica contra directorio corporativo (LDAP/AD)
    - Si no existe el usuario localmente, lo crea con rol Guest
    - Retorna access token y refresh token
    """
    # Autenticar usuario (LDAP o local)
    user = await AuthService.authenticate(
        db=db,
        username=credentials.username,
        password=credentials.password
    )

    # Prepare client IP and user agent
    forwarded = request.headers.get("X-Forwarded-For") if request else None
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.headers.get("X-Real-IP") if request else None
        if not client_ip:
            client_ip = request.client.host if request and request.client else "unknown"
    user_agent = request.headers.get("user-agent") if request else None
    
    if not user:
        # Log failed login attempt
        try:
            await AuditService.log_action(
                db=db,
                username=credentials.username,
                action=AuditAction.LOGIN,
                ip_address=client_ip,
                user_agent=user_agent,
                details={"success": False}
            )
            # Mark request as already logged to avoid duplicate logs in middleware
            try:
                request.state.audit_logged = True
            except Exception:
                pass
        except Exception:
            # Do not affect authentication flow
            pass

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Generar tokens
    tokens = AuthService.create_tokens(user)

    # Log successful login
    try:
        await AuditService.log_action(
            db=db,
            user=user,
            action=AuditAction.LOGIN,
            ip_address=client_ip,
            user_agent=user_agent,
            details={"success": True}
        )
        try:
            request.state.audit_logged = True
        except Exception:
            pass
    except Exception:
        # don't break login on audit failure
        pass
    
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Renovar access token usando refresh token válido
    
    - Valida refresh token
    - Genera nuevo access token
    - Retorna nuevo refresh token también
    """
    # Decodificar refresh token
    payload = AuthService.decode_token(refresh_data.refresh_token)
    
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Obtener usuario
    result = await db.execute(
        select(User).where(User.id == int(user_id))
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generar nuevos tokens
    tokens = AuthService.create_tokens(user)
    
    return tokens


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Obtener información del usuario autenticado actual
    
    - Requiere token JWT válido
    - Retorna datos del usuario
    """
    return current_user