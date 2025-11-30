"""
Routers de la aplicación
"""
from app.routers import auth, users, software, installers, licenses, audit

__all__ = [
    "auth",
    "users",
    "software",
    "installers",
    "licenses",
    "audit",
]