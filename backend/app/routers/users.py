"""
Router de gestión de usuarios (solo administradores)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from math import ceil
from app.database import get_db
from app.schemas import (
    UserResponse,
    UserListResponse,
    UserCreateRequest,
    UserUpdateRequest
)
from app.models import User, UserRole
from app.dependencies.auth import require_admin, get_current_user
from app.services.auth_service import AuthService
from app.config import settings

router = APIRouter(tags=["Users"])


@router.get("", response_model=UserListResponse, dependencies=[Depends(require_admin)])
async def list_users(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(
        settings.default_page_size,
        ge=1,
        le=settings.max_page_size,
        description="Elementos por página"
    ),
    role: Optional[UserRole] = Query(None, description="Filtrar por rol"),
    search: Optional[str] = Query(None, description="Buscar por username o email"),
    db: AsyncSession = Depends(get_db)
):
    """
    Listar usuarios con paginación y filtros
    
    **Requiere:** Rol de Administrador
    
    **Filtros:**
    - `role`: Filtrar por rol específico
    - `search`: Búsqueda en username o email
    """
    # Construir query base
    query = select(User)
    
    # Aplicar filtros
    if role:
        query = query.where(User.role == role)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (User.username.ilike(search_pattern)) |
            (User.email.ilike(search_pattern))
        )
    
    # Obtener total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    # Aplicar paginación
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(User.created_at.desc())
    
    # Ejecutar query
    result = await db.execute(query)
    users = result.scalars().all()
    
    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total > 0 else 0
    )


@router.get("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_admin)])
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener usuario por ID
    
    **Requiere:** Rol de Administrador
    """
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    return user


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
async def create_user(
    user_data: UserCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Crear usuario manualmente (no sincronizado con LDAP)
    
    **Requiere:** Rol de Administrador
    
    - Crea usuario local con contraseña
    - Para usuarios LDAP, se crean automáticamente en el login
    """
    # Verificar que el username no exista
    result = await db.execute(
        select(User).where(User.username == user_data.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Verificar que el email no exista
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )
    
    # Crear usuario
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        role=user_data.role,
        is_ldap_user=False,
        is_active=True
    )
    
    # Hashear contraseña si se proporciona
    if user_data.password:
        new_user.hashed_password = AuthService.get_password_hash(user_data.password)
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return new_user


@router.put("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_admin)])
async def update_user(
    user_id: int,
    user_data: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Actualizar usuario
    
    **Requiere:** Rol de Administrador
    
    - Permite cambiar rol y estado
    - No se puede desactivar a sí mismo
    """
    # Obtener usuario
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    # Prevenir que el admin se desactive a sí mismo
    if user.id == current_user.id and user_data.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    # Actualizar campos
    if user_data.email is not None:
        # Verificar que el email no esté en uso
        result = await db.execute(
            select(User).where(
                User.email == user_data.email,
                User.id != user_id
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        user.email = user_data.email
    
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    
    if user_data.role is not None:
        user.role = user_data.role
    
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    
    await db.commit()
    await db.refresh(user)
    
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Eliminar usuario (soft delete - marca como inactivo)
    
    **Requiere:** Rol de Administrador
    
    - No elimina físicamente, solo desactiva
    - No puede eliminarse a sí mismo
    """
    # Obtener usuario
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    # Prevenir que el admin se elimine a sí mismo
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    # Soft delete
    user.is_active = False
    await db.commit()
    
    return None
