"""
Schemas Pydantic para usuarios
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime
from app.models import UserRole


class UserBase(BaseModel):
    """Base schema para usuario"""
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    full_name: Optional[str] = None


class UserCreateRequest(UserBase):
    """Request para crear usuario"""
    role: UserRole = UserRole.GUEST
    password: Optional[str] = Field(None, min_length=8, description="Solo para usuarios locales")


class UserUpdateRequest(BaseModel):
    """Request para actualizar usuario"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """Response con datos de usuario"""
    id: int
    role: UserRole
    is_active: bool
    is_ldap_user: bool = Field(..., description="Indica si es usuario sincronizado desde LDAP")
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    """Response para lista de usuarios"""
    items: list[UserResponse]
    total: int
    page: int
    page_size: int
    pages: int