"""
Configuration management using pydantic-settings
Location: /opt/balaur-sms/backend/app/config.py
"""

from typing import List, Literal
from pydantic import Field, field_validator, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # ============================================
    # APPLICATION
    # ============================================
    app_name: str = "Balaur SMS"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "production"
    api_v1_prefix: str = "/api/v1"
    docs_enabled: bool = False
    
    # CORS - Parse JSON string to list
    cors_origins: str = '["http://localhost:5173"]'
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v
    
    # ============================================
    # DATABASE
    # ============================================
    database_url: str
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 3600
    
    # ============================================
    # SECURITY - JWT & Encryption
    # ============================================
    secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    encryption_key: str  # Fernet key for AES-GCM
    bcrypt_rounds: int = 12
    
    # ============================================
    # LDAP
    # ============================================
    ldap_enabled: bool = False
    ldap_server: str | None = None
    ldap_port: int = 389
    ldap_use_ssl: bool = False
    ldap_use_tls: bool = True
    ldap_bind_dn: str | None = None
    ldap_bind_password: str | None = None
    ldap_base_dn: str | None = None
    ldap_user_search_base: str | None = None
    ldap_user_search_filter: str = "(sAMAccountName={username})"
    ldap_user_object_class: str = "user"
    ldap_attr_username: str = "sAMAccountName"
    ldap_attr_email: str = "mail"
    ldap_attr_first_name: str = "givenName"
    ldap_attr_last_name: str = "sn"
    ldap_attr_member_of: str = "memberOf"
    ldap_group_admin: str | None = None
    ldap_group_manager: str | None = None
    ldap_group_user: str | None = None
    ldap_timeout: int = 10
    ldap_referrals: bool = False
    ldap_tls_require_cert: str = "never"
    
    @field_validator("ldap_server", mode="before")
    @classmethod
    def validate_ldap_config(cls, v, info):
        """Validate LDAP configuration if enabled"""
        if info.data.get("ldap_enabled") and not v:
            raise ValueError("LDAP_SERVER is required when LDAP_ENABLED=True")
        return v
    
    # ============================================
    # FTP / FTPS
    # ============================================
    ftp_host: str = "localhost"
    ftp_port: int = 21
    ftp_user: str
    ftp_password: str
    ftp_use_tls: bool = True
    ftp_tls_implicit: bool = False
    ftp_base_path: str = "/srv/ftp/balaur"
    ftp_inbox_pending: str = "/srv/ftp/balaur/inbox/pending"
    ftp_inbox_processing: str = "/srv/ftp/balaur/inbox/processing"
    ftp_repository: str = "/srv/ftp/balaur/repository"
    ftp_quarantine: str = "/srv/ftp/balaur/quarantine"
    ftp_timeout: int = 30
    ftp_passive_mode: bool = True
    
    # ============================================
    # FILE HANDLING
    # ============================================
    allowed_installer_extensions: str = '[".exe",".msi",".dmg",".pkg",".deb",".rpm",".AppImage",".zip",".tar.gz"]'
    allowed_doc_extensions: str = '[".pdf",".docx",".txt",".md"]'
    max_file_size: int = 10737418240  # 10GB
    hash_algorithm: str = "sha256"
    
    @field_validator("allowed_installer_extensions", "allowed_doc_extensions", mode="before")
    @classmethod
    def parse_extensions(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v
    
    # ============================================
    # FTP WATCHER
    # ============================================
    watcher_interval: int = 300  # 5 minutes
    watcher_enabled: bool = True
    watcher_max_retries: int = 3
    
    # ============================================
    # LOGGING
    # ============================================
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_file_path: str = "/var/log/balaur/backend/app.log"
    log_max_bytes: int = 10485760  # 10MB
    log_backup_count: int = 10
    audit_log_retention_days: int = 365
    
    # ============================================
    # RATE LIMITING
    # ============================================
    rate_limit_enabled: bool = False
    rate_limit_per_minute: int = 60
    
    # ============================================
    # EMAIL (Future)
    # ============================================
    email_enabled: bool = False
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_use_tls: bool = True
    
    # ============================================
    # REDIS (Future)
    # ============================================
    redis_enabled: bool = False
    redis_url: str | None = None
    
    # ============================================
    # DEVELOPMENT
    # ============================================
    sql_echo: bool = False
    reload: bool = False
    
    # ============================================
    # BACKUP
    # ============================================
    backup_dir: str = "/var/backups/balaur"
    backup_retention_days: int = 30
    
    # ============================================
    # COMPUTED PROPERTIES
    # ============================================
    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL (for Alembic)"""
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == "development"


# Singleton instance
settings = Settings()


# Validation on import
def validate_settings():
    """Validate critical settings on startup"""
    errors = []
    
    # Check required security keys
    if len(settings.secret_key) < 32:
        errors.append("SECRET_KEY must be at least 32 characters long")
    
    if len(settings.encryption_key) < 32:
        errors.append("ENCRYPTION_KEY must be at least 32 characters long")
    
    # Check LDAP configuration
    if settings.ldap_enabled:
        required_ldap = ["ldap_server", "ldap_base_dn", "ldap_bind_dn", "ldap_bind_password"]
        for field in required_ldap:
            if not getattr(settings, field):
                errors.append(f"{field.upper()} is required when LDAP is enabled")
    
    # Check FTP configuration
    if not settings.ftp_user or not settings.ftp_password:
        errors.append("FTP_USER and FTP_PASSWORD are required")
    
    # Check production settings
    if settings.is_production:
        if settings.debug:
            errors.append("DEBUG must be False in production")
        if settings.docs_enabled:
            errors.append("DOCS_ENABLED should be False in production")
        if settings.sql_echo:
            errors.append("SQL_ECHO should be False in production")
    
    if errors:
        raise ValueError(f"Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))


# Run validation on import
validate_settings()




