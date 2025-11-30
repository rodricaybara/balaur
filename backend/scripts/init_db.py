#!/usr/bin/env python3
"""
Script para inicializar la base de datos con datos de ejemplo
Location: /opt/balaur-sms/backend/scripts/init_db.py
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Añadir directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.models.software import Software, InstallerFile
from app.models.license import License, LicenseType
from app.services.auth_service import AuthService
from app.services.crypto_service import encrypt_license_key

# Colors for output
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
BLUE = '\033[0;34m'
NC = '\033[0m'


async def create_initial_users():
    """Crear usuarios iniciales"""
    print(f"{BLUE}Creating initial users...{NC}")
    
    async with AsyncSessionLocal() as db:
        # Admin
        admin = User(
            username="admin",
            email="admin@university.edu",
            full_name="System Administrator",
            role=UserRole.ADMIN,
            is_ldap_user=False,
            is_active=True,
            hashed_password=AuthService.get_password_hash("Admin123!")
        )
        db.add(admin)
        
        # Manager
        manager = User(
            username="manager",
            email="manager@university.edu",
            full_name="Software Manager",
            role=UserRole.MANAGER,
            is_ldap_user=False,
            is_active=True,
            hashed_password=AuthService.get_password_hash("Manager123!")
        )
        db.add(manager)
        
        # User
        user = User(
            username="user",
            email="user@university.edu",
            full_name="Regular User",
            role=UserRole.USER,
            is_ldap_user=False,
            is_active=True,
            hashed_password=AuthService.get_password_hash("User123!")
        )
        db.add(user)
        
        # Guest
        guest = User(
            username="guest",
            email="guest@university.edu",
            full_name="Guest User",
            role=UserRole.GUEST,
            is_ldap_user=False,
            is_active=True,
            hashed_password=AuthService.get_password_hash("Guest123!")
        )
        db.add(guest)
        
        await db.commit()
        await db.refresh(admin)
        await db.refresh(manager)
        
        print(f"{GREEN}✓ Users created successfully{NC}")
        print(f"  - admin / Admin123! (Role: {UserRole.ADMIN})")
        print(f"  - manager / Manager123! (Role: {UserRole.MANAGER})")
        print(f"  - user / User123! (Role: {UserRole.USER})")
        print(f"  - guest / Guest123! (Role: {UserRole.GUEST})")
        
        return admin.id, manager.id


async def create_sample_software(admin_id: int, manager_id: int):
    """Crear software de ejemplo"""
    print(f"\n{BLUE}Creating sample software...{NC}")
    
    async with AsyncSessionLocal() as db:
        software_list = [
            {
                "software": Software(
                    name="Microsoft Office",
                    vendor="Microsoft",
                    category="Productivity",
                    description="Suite ofimática completa con Word, Excel, PowerPoint",
                    website="https://www.office.com",
                    created_by=admin_id,
                ),
            },
            {
                "software": Software(
                    name="Adobe Acrobat Reader",
                    vendor="Adobe",
                    category="PDF Viewer",
                    description="Lector de archivos PDF",
                    website="https://www.adobe.com/acrobat",
                    created_by=admin_id,
                ),
            },
            {
                "software": Software(
                    name="Visual Studio Code",
                    vendor="Microsoft",
                    category="Development",
                    description="Editor de código multiplataforma",
                    website="https://code.visualstudio.com",
                    created_by=manager_id,
                ),
            },
            {
                "software": Software(
                    name="Google Chrome",
                    vendor="Google",
                    category="Web Browser",
                    description="Navegador web rápido y seguro",
                    website="https://www.google.com/chrome",
                    created_by=manager_id,
                ),
            },
            {
                "software": Software(
                    name="MATLAB",
                    vendor="MathWorks",
                    category="Mathematics",
                    description="Plataforma de análisis numérico y programación",
                    website="https://www.mathworks.com",
                    created_by=admin_id,
                ),
            }
        ]
        
        software_ids = []
        for item in software_list:
            software = item["software"]
            db.add(software)
            await db.flush()
            software_ids.append(software.id)
        
        await db.commit()
        print(f"{GREEN}✓ Created {len(software_list)} software entries with versions{NC}")
        
        return software_ids


async def create_sample_licenses(software_ids: list):
    """Crear licencias de ejemplo"""
    print(f"\n{BLUE}Creating sample licenses...{NC}")
    
    async with AsyncSessionLocal() as db:
        licenses = [
            License(
                software_id=software_ids[0],  # Microsoft Office
                license_type=LicenseType.VOLUME,
                encrypted_key=encrypt_license_key("XXXXX-XXXXX-XXXXX-XXXXX-XXXXX"),
                max_activations=500,
                expiration_date=None,
                notes="Licencia por volumen institucional - Campus Wide"
            ),
            License(
                software_id=software_ids[4],  # MATLAB
                license_type=LicenseType.EDUCATIONAL,
                encrypted_key=encrypt_license_key("12345-67890-ABCDE-FGHIJ-KLMNO"),
                max_activations=100,
                expiration_date=datetime.utcnow() + timedelta(days=365),
                notes="Licencia educativa campus-wide - Renovación anual"
            ),
            License(
                software_id=software_ids[1],  # Adobe Acrobat
                license_type=LicenseType.SUBSCRIPTION,
                encrypted_key=encrypt_license_key("ADOBE-2024-SUBS-KEY-12345"),
                max_activations=200,
                expiration_date=datetime.utcnow() + timedelta(days=180),
                notes="Suscripción semestral - Departamento de Informática"
            )
        ]
        
        for license_obj in licenses:
            db.add(license_obj)
        
        await db.commit()
        print(f"{GREEN}✓ Created {len(licenses)} license entries{NC}")


async def main():
    """Función principal"""
    print("=" * 60)
    print("BALAUR SMS - Database Initialization")
    print("=" * 60)
    print()
    print(f"{YELLOW}⚠️  WARNING: This will create sample data in your database{NC}")
    print(f"{YELLOW}⚠️  Make sure you have a clean database or want to add this data{NC}")
    print()
    
    response = input("Continue? (yes/no): ")
    if response.lower() != "yes":
        print(f"\n{RED}Aborted.{NC}")
        return
    
    print()
    
    try:
        # Create users first and get IDs
        admin_id, manager_id = await create_initial_users()
        
        # Create software with the user IDs
        software_ids = await create_sample_software(admin_id, manager_id)
        
        # Create licenses
        await create_sample_licenses(software_ids)
        
        print()
        print("=" * 60)
        print(f"{GREEN}✓ Database initialized successfully!{NC}")
        print("=" * 60)
        print()
        print("You can now:")
        print("  1. Start the server: uvicorn app.main:app --reload")
        print("  2. Access API docs: http://localhost:8000/docs")
        print("  3. Login with: admin / Admin123!")
        print()
        print(f"{YELLOW}⚠️  IMPORTANT: Change default passwords in production!{NC}")
        print()
        
    except Exception as e:
        print()
        print("=" * 60)
        print(f"{RED}✗ Error: {e}{NC}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
