"""
Schemas Pydantic para autenticación
"""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Request para login"""
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)


class RefreshRequest(BaseModel):
    """Request para refresh token"""
    refresh_token: str


class TokenResponse(BaseModel):
    """Response con tokens JWT"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Segundos hasta expiración del access token")