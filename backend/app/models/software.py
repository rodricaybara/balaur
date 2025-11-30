"""
Modelos de Software e Instaladores
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, BigInteger
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Software(Base):
    """Modelo de software"""
    __tablename__ = "software"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    vendor = Column(String(200), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    website = Column(String(500), nullable=True)
    
    # Metadata
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    creator = relationship("User", back_populates="software_created", foreign_keys=[created_by])
    installers = relationship("InstallerFile", back_populates="software", cascade="all, delete-orphan")
    licenses = relationship("License", back_populates="software", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Software {self.name} by {self.vendor}>"


class InstallerFile(Base):
    """Modelo de archivo instalador"""
    __tablename__ = "installer_files"
    
    id = Column(Integer, primary_key=True, index=True)
    software_id = Column(Integer, ForeignKey("software.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Información de versión
    version = Column(String(50), nullable=False, index=True)
    
    # Información del archivo
    filename = Column(String(255), nullable=False)
    file_size = Column(BigInteger, nullable=False)  # Bytes
    sha256_hash = Column(String(64), nullable=False, unique=True, index=True)
    
    # Path relativo en FTP repository
    ftp_path = Column(String(500), nullable=False)
    
    # Metadata adicional
    architecture = Column(String(50), nullable=True)  # x64, x86, arm64, universal
    platform = Column(String(50), nullable=True)  # Windows, Linux, macOS
    notes = Column(Text, nullable=True)
    
    # Estadísticas
    download_count = Column(Integer, default=0, nullable=False)
    
    # Metadata de subida
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    software = relationship("Software", back_populates="installers")
    uploader = relationship("User", back_populates="installers_uploaded")
    
    def __repr__(self):
        return f"<InstallerFile {self.filename} v{self.version}>"
    
    @property
    def file_size_mb(self) -> float:
        """Tamaño en MB"""
        return self.file_size / (1024 * 1024)
    
    @property
    def file_size_gb(self) -> float:
        """Tamaño en GB"""
        return self.file_size / (1024 * 1024 * 1024)