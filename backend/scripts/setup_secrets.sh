#!/bin/bash
#
# Script para gestionar secrets de Balaur SMS
# Location: /opt/balaur/backend/scripts/setup_secrets.sh
#

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Directorio de secrets
SECRETS_DIR="/opt/balaur/secrets"
SECRETS_FILE="${SECRETS_DIR}/credentials.vault"

echo -e "${GREEN}=== Balaur SMS - Secrets Setup ===${NC}\n"

# Crear directorio de secrets si no existe
if [ ! -d "$SECRETS_DIR" ]; then
    echo "Creating secrets directory..."
    sudo mkdir -p "$SECRETS_DIR"
    sudo chown root:balaur-app "$SECRETS_DIR"
    sudo chmod 750 "$SECRETS_DIR"
fi

# ============================================
# GENERAR PASSWORDS SEGUROS
# ============================================

generate_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-32
}

echo -e "${YELLOW}Generating secure passwords...${NC}"

DB_PASSWORD=$(generate_password)
FTP_PASSWORD=$(generate_password)
LDAP_BIND_PASSWORD="ASK_YOUR_IT_DEPARTMENT"  # Este debe ser proporcionado por IT

# ============================================
# GENERAR CLAVES DE SEGURIDAD
# ============================================

echo -e "${YELLOW}Generating security keys...${NC}"

# JWT Secret Key (64 bytes)
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")

# Encryption Key (Fernet format)
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# ============================================
# GUARDAR EN VAULT CIFRADO
# ============================================

echo -e "${YELLOW}Creating encrypted credentials vault...${NC}"

# Crear archivo temporal con credenciales
cat > /tmp/balaur_secrets.txt << EOF
# ============================================
# BALAUR SMS - CREDENTIALS VAULT
# Generated: $(date '+%Y-%m-%d %H:%M:%S')
# ============================================

# DATABASE
DB_USER=balaur
DB_PASSWORD=${DB_PASSWORD}
DB_NAME=balaur_sms
DB_HOST=localhost
DB_PORT=5432

# FTP
FTP_USER=balaur
FTP_PASSWORD=${FTP_PASSWORD}
FTP_HOST=localhost

# LDAP (Configure with your IT department)
LDAP_SERVER=ldap://ldap.university.edu
LDAP_BIND_DN=cn=balaur-service,ou=services,dc=university,dc=edu
LDAP_BIND_PASSWORD=${LDAP_BIND_PASSWORD}

# SECURITY KEYS
SECRET_KEY=${SECRET_KEY}
ENCRYPTION_KEY=${ENCRYPTION_KEY}

# ============================================
# DATABASE CONNECTION STRING
# ============================================
DATABASE_URL=postgresql+asyncpg://balaur:${DB_PASSWORD}@localhost:5432/balaur_sms

# ============================================
# IMPORTANT NOTES
# ============================================
# 1. This file is encrypted with OpenSSL AES-256-CBC
# 2. Keep the encryption password in a safe place (password manager)
# 3. Never commit this file to Git
# 4. Backup this file securely (encrypted USB, safe location)
# 5. Update LDAP_BIND_PASSWORD with real value from IT department
EOF

# Cifrar el archivo
echo -e "${YELLOW}Enter a strong password to encrypt the vault:${NC}"
openssl enc -aes-256-cbc -salt -pbkdf2 -in /tmp/balaur_secrets.txt -out "${SECRETS_FILE}"

# Limpiar archivo temporal
shred -u /tmp/balaur_secrets.txt

# Permisos restrictivos
sudo chown root:root "${SECRETS_FILE}"
sudo chmod 400 "${SECRETS_FILE}"

echo -e "${GREEN}✓ Secrets vault created: ${SECRETS_FILE}${NC}"

# ============================================
# CONFIGURAR POSTGRESQL
# ============================================

echo -e "\n${YELLOW}Configuring PostgreSQL...${NC}"

sudo -u postgres psql << EOSQL
-- Create user if not exists
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'balaur') THEN
        CREATE USER balaur WITH PASSWORD '${DB_PASSWORD}';
    END IF;
END
\$\$;

-- Create database if not exists
SELECT 'CREATE DATABASE balaur_sms OWNER balaur'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'balaur_sms')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE balaur_sms TO balaur;

\c balaur_sms
GRANT ALL ON SCHEMA public TO balaur;
EOSQL

echo -e "${GREEN}✓ PostgreSQL configured${NC}"

# ============================================
# CONFIGURAR USUARIO FTP
# ============================================

echo -e "\n${YELLOW}Configuring FTP user...${NC}"

# Crear usuario balaur si no existe
if ! id "balaur" &>/dev/null; then
    sudo useradd -m -d /srv/ftp/balaur -s /bin/bash balaur
    echo "balaur:${FTP_PASSWORD}" | sudo chpasswd
    echo -e "${GREEN}✓ FTP user 'balaur' created${NC}"
else
    echo "balaur:${FTP_PASSWORD}" | sudo chpasswd
    echo -e "${GREEN}✓ FTP user 'balaur' password updated${NC}"
fi

# ============================================
# CREAR .env
# ============================================

echo -e "\n${YELLOW}Creating .env file...${NC}"

cat > /opt/balaur/backend/.env << EOF
# ============================================
# BALAUR SMS - Backend Configuration
# Generated: $(date '+%Y-%m-%d %H:%M:%S')
# ============================================

# APPLICATION
APP_NAME="Balaur SMS"
APP_VERSION="1.0.0"
DEBUG=False
ENVIRONMENT=production
CORS_ORIGINS=["https://balaur.university.edu"]
API_V1_PREFIX=/api/v1
DOCS_ENABLED=False

# DATABASE
DATABASE_URL=postgresql+asyncpg://balaur:${DB_PASSWORD}@localhost:5432/balaur_sms
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# SECURITY
SECRET_KEY=${SECRET_KEY}
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
ENCRYPTION_KEY=${ENCRYPTION_KEY}
BCRYPT_ROUNDS=12

# LDAP (UPDATE WITH YOUR VALUES)
LDAP_ENABLED=True
LDAP_SERVER=ldap://ldap.university.edu
LDAP_PORT=389
LDAP_USE_SSL=False
LDAP_USE_TLS=True
LDAP_BIND_DN=cn=balaur-service,ou=services,dc=university,dc=edu
LDAP_BIND_PASSWORD=${LDAP_BIND_PASSWORD}
LDAP_BASE_DN=dc=university,dc=edu
LDAP_USER_SEARCH_BASE=ou=people,dc=university,dc=edu
LDAP_USER_SEARCH_FILTER=(uid={username})
LDAP_USER_OBJECT_CLASS=inetOrgPerson
LDAP_ATTR_USERNAME=uid
LDAP_ATTR_EMAIL=mail
LDAP_ATTR_FIRST_NAME=givenName
LDAP_ATTR_LAST_NAME=sn
LDAP_ATTR_MEMBER_OF=memberOf
LDAP_GROUP_ADMIN=cn=balaur-admins,ou=groups,dc=university,dc=edu
LDAP_GROUP_MANAGER=cn=balaur-managers,ou=groups,dc=university,dc=edu
LDAP_GROUP_USER=cn=balaur-users,ou=groups,dc=university,dc=edu
LDAP_TIMEOUT=10

# FTP
FTP_HOST=localhost
FTP_PORT=21
FTP_USER=balaur
FTP_PASSWORD=${FTP_PASSWORD}
FTP_USE_TLS=True
FTP_TLS_IMPLICIT=False
FTP_BASE_PATH=/srv/ftp/balaur
FTP_INBOX_PENDING=/srv/ftp/balaur/inbox/pending
FTP_INBOX_PROCESSING=/srv/ftp/balaur/inbox/processing
FTP_REPOSITORY=/srv/ftp/balaur/repository
FTP_QUARANTINE=/srv/ftp/balaur/quarantine
FTP_TIMEOUT=30
FTP_PASSIVE_MODE=True

# FILE HANDLING
ALLOWED_INSTALLER_EXTENSIONS=[".exe",".msi",".dmg",".pkg",".deb",".rpm",".AppImage",".zip",".tar.gz"]
ALLOWED_DOC_EXTENSIONS=[".pdf",".docx",".txt",".md"]
MAX_FILE_SIZE=10737418240
HASH_ALGORITHM=sha256

# FTP WATCHER
WATCHER_INTERVAL=300
WATCHER_ENABLED=True
WATCHER_MAX_RETRIES=3

# LOGGING
LOG_LEVEL=INFO
LOG_FILE_PATH=/var/log/balaur/backend/app.log
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=10
AUDIT_LOG_RETENTION_DAYS=365

# RATE LIMITING
RATE_LIMIT_ENABLED=False
RATE_LIMIT_PER_MINUTE=60

# EMAIL (Future)
EMAIL_ENABLED=False

# REDIS (Future)
REDIS_ENABLED=False

# DEVELOPMENT
SQL_ECHO=False
RELOAD=False

# BACKUP
BACKUP_DIR=/var/backups/balaur
BACKUP_RETENTION_DAYS=30
EOF

sudo chown balaur-app:balaur-app /opt/balaur/backend/.env
sudo chmod 600 /opt/balaur/backend/.env

echo -e "${GREEN}✓ .env file created${NC}"

# ============================================
# RESUMEN
# ============================================

echo -e "\n${GREEN}=== Setup Complete ===${NC}\n"
echo -e "✓ Encrypted vault: ${SECRETS_FILE}"
echo -e "✓ PostgreSQL configured"
echo -e "✓ FTP user configured"
echo -e "✓ .env file created"
echo -e "\n${YELLOW}IMPORTANT:${NC}"
echo -e "1. Vault password: Keep it safe! You'll need it to decrypt the vault"
echo -e "2. Update LDAP_BIND_PASSWORD in .env with real value from IT"
echo -e "3. Backup the encrypted vault to a secure location"
echo -e "4. Test database connection: psql -U balaur -d balaur_sms -h localhost"
echo -e "5. Test FTP connection: ftp balaur@localhost"
echo -e "\n${GREEN}To decrypt the vault later:${NC}"
echo -e "openssl enc -aes-256-cbc -d -pbkdf2 -in ${SECRETS_FILE} | less"
echo ""
