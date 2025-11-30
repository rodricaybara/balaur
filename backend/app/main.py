"""
Balaur SMS - FastAPI Application Entry Point
Location: /opt/balaur-sms/backend/app/main.py
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import logging
import time

from app.config import settings
from app.database import engine

# Import routers
from app.routers import auth, users, software, installers, licenses, audit, system

# Agregar import del watcher
from app.services.ftp_watcher import start_ftp_watcher, ftp_watcher

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info("=" * 60)
    logger.info("Starting Balaur SMS Backend")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"API version: {settings.app_version}")
    logger.info(f"LDAP enabled: {settings.ldap_enabled}")
    logger.info(f"Database: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'configured'}")
    logger.info("=" * 60)
    
    # Iniciar ftp_watcher (si start_ftp_watcher es coroutine, se await; si devuelve tarea, se llama)
    try:
        started = start_ftp_watcher()
        if hasattr(started, "__await__"):
            await started
        logger.info("ftp_watcher started")
    except Exception as e:
        logger.error(f"Failed to start ftp_watcher: {e}")

    yield
    
    # Shutdown
    logger.info("Shutting down Balaur SMS Backend")
    # Intentar detener el watcher si expone método stop()
    try:
        if hasattr(ftp_watcher, "stop") and callable(ftp_watcher.stop):
            stop_ret = ftp_watcher.stop()
            if hasattr(stop_ret, "__await__"):
                await stop_ret
            logger.info("ftp_watcher stopped")
    except Exception as e:
        logger.error(f"Failed to stop ftp_watcher cleanly: {e}")

    await engine.dispose()
    logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Software Management System for Universities",
    version=settings.app_version,
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
    lifespan=lifespan
)


# ============================================
# MIDDLEWARE
# ============================================

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-Page", "X-Per-Page"]
)

# Trusted Host Middleware (production)
if settings.is_production:
    # Get allowed hosts from CORS origins
    allowed_hosts = []
    for origin in settings.cors_origins:
        # Extract host from URL
        if "://" in origin:
            host = origin.split("://")[1].split(":")[0]
        else:
            host = origin.split(":")[0]
        allowed_hosts.append(host)
    
    # Add localhost for internal health checks
    allowed_hosts.extend(["localhost", "127.0.0.1"])
    
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=allowed_hosts
    )


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header to responses"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    return response


# Audit logging middleware
@app.middleware("http")
async def audit_log_middleware(request: Request, call_next):
    """Log all requests for audit purposes"""
    
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    # Get user from request state (set by auth dependency)
    user_id = getattr(request.state, "user_id", None)
    
    # Log request
    logger.info(
        f"Request: {request.method} {request.url.path} | "
        f"IP: {client_ip} | User: {user_id or 'anonymous'}"
    )
    
    # Process request
    response = await call_next(request)
    
    # Log response
    logger.info(
        f"Response: {request.method} {request.url.path} | "
        f"Status: {response.status_code} | User: {user_id or 'anonymous'}"
    )
    
    return response


# Security headers middleware
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to responses"""
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # Remove server header
    if "server" in response.headers:
        del response.headers["server"]
    
    return response


# ============================================
# EXCEPTION HANDLERS
# ============================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Don't expose internal errors in production
    if settings.is_production:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"}
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error",
                "error": str(exc),
                "type": type(exc).__name__
            }
        )


# ============================================
# ROUTERS
# ============================================

# Health check endpoint (always enabled)
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for monitoring
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment
    }

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information
    """
    return {
        "message": "Balaur SMS API",
        "version": settings.app_version,
        "docs": f"{settings.api_v1_prefix}/docs" if settings.docs_enabled else "disabled",
        "health": "/health"
    }


# Include API routers
app.include_router(
    auth.router,
    prefix=f"{settings.api_v1_prefix}/auth",
    tags=["Authentication"]
)

app.include_router(
    users.router,
    prefix=f"{settings.api_v1_prefix}/users",
    tags=["Users"]
)

app.include_router(
    software.router,
    prefix=f"{settings.api_v1_prefix}/software",
    tags=["Software"]
)

app.include_router(
    installers.router,
    prefix=f"{settings.api_v1_prefix}/installers",
    tags=["Installers"]
)

app.include_router(
    licenses.router,
    prefix=f"{settings.api_v1_prefix}/licenses",
    tags=["Licenses"]
)

app.include_router(
    audit.router,
    prefix=f"{settings.api_v1_prefix}/audit",
    tags=["Audit"]
)

# NUEVO: Router de system
app.include_router(
    system.router,
    prefix=f"{settings.api_v1_prefix}/system",
    tags=["System"]
)

# ============================================
# STARTUP MESSAGE
# ============================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Balaur SMS in development mode")
    logger.info("Use 'uvicorn app.main:app --reload' for development")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )
