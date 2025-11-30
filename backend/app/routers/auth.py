"""
Router de autenticación
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.schemas import LoginRequest, RefreshRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthService
from app.dependencies.auth import get_current_user
from app.models import User

router = APIRouter(tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db)
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
    
    if not user:
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