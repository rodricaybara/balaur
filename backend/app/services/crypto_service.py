"""
Servicio de cifrado AES-GCM para licencias
"""
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from app.config import settings


class CryptoService:
    """Servicio de cifrado/descifrado con AES-GCM"""
    
    def __init__(self):
        """Inicializa el servicio con la clave de cifrado"""
        # La clave debe ser de 32 bytes (256 bits)
        key_hex = settings.encryption_key
        if len(key_hex) != 64:  # 32 bytes = 64 caracteres hex
            raise ValueError("ENCRYPTION_KEY must be 64 hex characters (32 bytes)")
        
        self.key = bytes.fromhex(key_hex)
        self.aesgcm = AESGCM(self.key)
    
    def encrypt(self, plaintext: str) -> bytes:
        """
        Cifra texto plano con AES-GCM
        
        Args:
            plaintext: Texto a cifrar
            
        Returns:
            bytes: nonce (12 bytes) + ciphertext + tag (16 bytes)
        """
        # Generar nonce aleatorio de 12 bytes (recomendado para GCM)
        nonce = os.urandom(12)
        
        # Cifrar
        plaintext_bytes = plaintext.encode('utf-8')
        ciphertext = self.aesgcm.encrypt(nonce, plaintext_bytes, None)
        
        # Retornar nonce + ciphertext (ciphertext ya incluye el tag)
        return nonce + ciphertext
    
    def decrypt(self, encrypted_data: bytes) -> str:
        """
        Descifra datos cifrados con AES-GCM
        
        Args:
            encrypted_data: nonce (12 bytes) + ciphertext + tag
            
        Returns:
            str: Texto descifrado
            
        Raises:
            ValueError: Si el descifrado falla (datos corruptos o clave incorrecta)
        """
        if len(encrypted_data) < 12:
            raise ValueError("Encrypted data is too short")
        
        # Separar nonce y ciphertext
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        
        try:
            # Descifrar
            plaintext_bytes = self.aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext_bytes.decode('utf-8')
        except InvalidTag:
            raise ValueError("Decryption failed: invalid authentication tag")
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")


# Instancia global del servicio
crypto_service = CryptoService()


def encrypt_license_key(key: str) -> bytes:
    """Helper para cifrar clave de licencia"""
    return crypto_service.encrypt(key)


def decrypt_license_key(encrypted_key: bytes) -> str:
    """Helper para descifrar clave de licencia"""
    return crypto_service.decrypt(encrypted_key)
