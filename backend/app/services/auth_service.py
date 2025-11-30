"""
Servicio de autenticación y gestión de tokens JWT
"""
from datetime import datetime, timedelta
from typing import Optional
import ssl
from jose import JWTError, jwt
from passlib.context import CryptContext
from ldap3 import Server, Connection, ALL, SUBTREE, Tls
from ldap3.core.exceptions import LDAPException, LDAPBindError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models import User, UserRole

# Contexto para hashing de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    """Servicio de autenticación"""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verifica contraseña contra hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Genera hash de contraseña"""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Crea JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
        
        to_encode.update({
            "exp": expire,
            "type": "access"
        })
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: dict) -> str:
        """Crea JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
        
        to_encode.update({
            "exp": expire,
            "type": "refresh"
        })
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """Decodifica y valida token JWT"""
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
            return payload
        except JWTError:
            return None
    
    @staticmethod
    def authenticate_ldap(username: str, password: str) -> Optional[dict]:
        """
        Autentica usuario contra LDAP/AD
        Retorna dict con datos del usuario si es exitoso, None si falla
        
        FLUJO CORRECTO (igual que test_ldap.py):
        1. Conectar con cuenta de servicio
        2. Buscar DN del usuario
        3. Autenticar con DN + password del usuario
        4. Extraer atributos adicionales
        """
        if not settings.ldap_enabled:
            return None
        
        try:
            # PASO 1: Configurar TLS (igual que test_ldap.py)
            tls_config = None
            if settings.ldap_use_tls or settings.ldap_use_ssl:
                tls_config = Tls(
                    validate=ssl.CERT_NONE if settings.ldap_tls_require_cert == "never" else ssl.CERT_REQUIRED
                )
            
            # PASO 2: Crear servidor (igual que test_ldap.py)
            use_ssl = settings.ldap_use_ssl
            server = Server(
                settings.ldap_server.replace('ldap://', '').replace('ldaps://', ''),
                port=settings.ldap_port,
                use_ssl=use_ssl,
                tls=tls_config,
                get_info=ALL,
                connect_timeout=settings.ldap_timeout
            )
            
            # PASO 3: Bind con CUENTA DE SERVICIO (igual que test_ldap.py línea 71)
            service_conn = Connection(
                server,
                user=settings.ldap_bind_dn,  # ← CUENTA DE SERVICIO
                password=settings.ldap_bind_password,  # ← PASSWORD DE SERVICIO
                auto_bind=True,
                raise_exceptions=True
            )
            
            # PASO 4: Buscar usuario para obtener su DN real (igual que test_ldap.py línea 94)
            search_filter = settings.ldap_user_search_filter.replace("{username}", username)
            service_conn.search(
                search_base=settings.ldap_user_search_base,  # ← BASE ESPECÍFICA DE USUARIOS
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=[
                    settings.ldap_attr_username,
                    settings.ldap_attr_email,
                    settings.ldap_attr_first_name,
                    settings.ldap_attr_last_name,
                    'distinguishedName'
                ]
            )
            
            if not service_conn.entries:
                print(f"LDAP: Usuario '{username}' no encontrado")
                service_conn.unbind()
                return None
            
            # Extraer DN del usuario
            user_entry = service_conn.entries[0]
            user_dn = user_entry.entry_dn
            
            print(f"LDAP: Usuario encontrado - DN: {user_dn}")
            
            # Extraer atributos del usuario
            user_data = {
                "username": username,
                "email": None,
                "full_name": None,
            }
            
            # Email
            if hasattr(user_entry, settings.ldap_attr_email):
                email_value = getattr(user_entry, settings.ldap_attr_email)
                user_data["email"] = str(email_value.value if hasattr(email_value, 'value') else email_value)
            
            # Nombre completo
            if hasattr(user_entry, settings.ldap_attr_first_name) and hasattr(user_entry, settings.ldap_attr_last_name):
                first_name = getattr(user_entry, settings.ldap_attr_first_name)
                last_name = getattr(user_entry, settings.ldap_attr_last_name)
                first_name_str = str(first_name.value if hasattr(first_name, 'value') else first_name)
                last_name_str = str(last_name.value if hasattr(last_name, 'value') else last_name)
                user_data["full_name"] = f"{first_name_str} {last_name_str}"
            
            # Cerrar conexión de servicio
            service_conn.unbind()
            
            # PASO 5: Autenticar con DN real del usuario (igual que test_ldap.py línea 127)
            user_conn = Connection(
                server,
                user=user_dn,  # ← DN REAL del usuario (no el bind_dn)
                password=password,  # ← Password del USUARIO
                auto_bind=True,
                raise_exceptions=True
            )
            
            # Verificar bind
            if not user_conn.bind():
                print(f"LDAP: Autenticación fallida para {username}")
                return None
            
            print(f"LDAP: Autenticación exitosa para {username}")
            user_conn.unbind()
            
            return user_data
            
        except LDAPBindError as e:
            print(f"LDAP Bind Error: {e}")
            print(f"  Usuario: {username}")
            return None
            
        except LDAPException as e:
            print(f"LDAP Exception: {e}")
            return None
            
        except Exception as e:
            print(f"LDAP authentication error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    async def authenticate_local(
        db: AsyncSession,
        username: str,
        password: str
    ) -> Optional[User]:
        """Autentica usuario local (no LDAP)"""
        result = await db.execute(
            select(User).where(
                User.username == username,
                User.is_active == True,
                User.is_ldap_user == False
            )
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.hashed_password:
            return None
        
        if not AuthService.verify_password(password, user.hashed_password):
            return None
        
        return user
    
    @staticmethod
    async def get_or_create_ldap_user(
        db: AsyncSession,
        ldap_data: dict
    ) -> User:
        """
        Obtiene usuario LDAP de la BD o lo crea si no existe
        Los nuevos usuarios LDAP se crean con rol GUEST por defecto
        """
        username = ldap_data["username"]
        
        # Buscar usuario existente
        result = await db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Actualizar último login
            user.last_login = datetime.utcnow()
            await db.commit()
            await db.refresh(user)
            return user
        
        # Crear nuevo usuario
        email = ldap_data.get("email") or f"{username}@university.edu"
        
        new_user = User(
            username=username,
            email=email,
            full_name=ldap_data.get("full_name"),
            is_ldap_user=True,
            role=UserRole.GUEST,  # Rol por defecto
            is_active=True,
            last_login=datetime.utcnow()
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        return new_user
    
    @staticmethod
    async def authenticate(
        db: AsyncSession,
        username: str,
        password: str
    ) -> Optional[User]:
        """
        Autentica usuario (primero LDAP, luego local)
        Retorna objeto User si es exitoso
        """
        # Intentar autenticación LDAP
        if settings.ldap_enabled:
            ldap_data = AuthService.authenticate_ldap(username, password)
            if ldap_data:
                user = await AuthService.get_or_create_ldap_user(db, ldap_data)
                return user
        
        # Si falla LDAP, intentar autenticación local
        user = await AuthService.authenticate_local(db, username, password)
        return user
    
    @staticmethod
    def create_tokens(user: User) -> dict:
        """Crea par de tokens (access + refresh) para un usuario"""
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value,
        }
        
        access_token = AuthService.create_access_token(token_data)
        refresh_token = AuthService.create_refresh_token({"sub": str(user.id)})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.jwt_access_token_expire_minutes * 60
        }