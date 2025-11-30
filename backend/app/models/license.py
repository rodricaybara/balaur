"""
Modelo de Licencias
"""
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, Enum as SQLEnum, LargeBinary
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class LicenseType(str, enum.Enum):
    """Tipos de licencia"""
    PERPETUAL = "perpetual"
    SUBSCRIPTION = "subscription"
    VOLUME = "volume"
    OEM = "oem"
    EDUCATIONAL = "educational"
    TRIAL = "trial"


class License(Base):
    """Modelo de licencia de software"""
    __tablename__ = "licenses"
    
    id = Column(Integer, primary_key=True, index=True)
    software_id = Column(Integer, ForeignKey("software.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Tipo de licencia
    license_type = Column(
        SQLEnum(LicenseType, name="license_type"),
        nullable=False,
        index=True
    )
    
    # Clave cifrada con AES-GCM
    # Almacena: nonce (12 bytes) + ciphertext + tag (16 bytes)
    encrypted_key = Column(LargeBinary, nullable=False)
    
    # Información adicional
    max_activations = Column(Integer, nullable=True)
    expiration_date = Column(Date, nullable=True, index=True)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    software = relationship("Software", back_populates="licenses")
    
    def __repr__(self):
        return f"<License {self.license_type} for software_id={self.software_id}>"