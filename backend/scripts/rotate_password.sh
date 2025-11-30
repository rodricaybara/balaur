#!/bin/bash
#
# Rotate passwords for Balaur SMS
# Location: /opt/balaur-sms/backend/scripts/rotate_password.sh
# Usage: sudo ./rotate_password.sh [db|ftp|all]
#

set -e

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SECRETS_DIR="/opt/balaur-sms/secrets"
SECRETS_FILE="${SECRETS_DIR}/credentials.vault"
ENV_FILE="/opt/balaur-sms/backend/.env"

# Verificar permisos
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: This script must be run as root${NC}"
    exit 1
fi

generate_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-32
}

echo -e "${GREEN}=== Balaur SMS - Password Rotation ===${NC}\n"

TARGET=${1:-all}

case $TARGET in
    db)
        echo -e "${YELLOW}Rotating database password...${NC}"
        NEW_DB_PASSWORD=$(generate_password)
        
        # Update PostgreSQL
        sudo -u postgres psql -c "ALTER USER balaur WITH PASSWORD '${NEW_DB_PASSWORD}';"
        
        # Update .env
        sed -i "s|DATABASE_URL=postgresql+asyncpg://balaur:[^@]*@|DATABASE_URL=postgresql+asyncpg://balaur:${NEW_DB_PASSWORD}@|g" "$ENV_FILE"
        
        echo -e "${GREEN}✓ Database password rotated${NC}"
        echo -e "New password: ${NEW_DB_PASSWORD}"
        ;;
        
    ftp)
        echo -e "${YELLOW}Rotating FTP password...${NC}"
        NEW_FTP_PASSWORD=$(generate_password)
        
        # Update FTP user
        echo "balaur:${NEW_FTP_PASSWORD}" | chpasswd
        
        # Update .env
        sed -i "s|FTP_PASSWORD=.*|FTP_PASSWORD=${NEW_FTP_PASSWORD}|g" "$ENV_FILE"
        
        echo -e "${GREEN}✓ FTP password rotated${NC}"
        echo -e "New password: ${NEW_FTP_PASSWORD}"
        ;;
        
    all)
        echo -e "${YELLOW}Rotating all passwords...${NC}"
        
        NEW_DB_PASSWORD=$(generate_password)
        NEW_FTP_PASSWORD=$(generate_password)
        
        # Database
        sudo -u postgres psql -c "ALTER USER balaur WITH PASSWORD '${NEW_DB_PASSWORD}';"
        sed -i "s|DATABASE_URL=postgresql+asyncpg://balaur:[^@]*@|DATABASE_URL=postgresql+asyncpg://balaur:${NEW_DB_PASSWORD}@|g" "$ENV_FILE"
        
        # FTP
        echo "balaur:${NEW_FTP_PASSWORD}" | chpasswd
        sed -i "s|FTP_PASSWORD=.*|FTP_PASSWORD=${NEW_FTP_PASSWORD}|g" "$ENV_FILE"
        
        echo -e "${GREEN}✓ All passwords rotated${NC}"
        echo -e "Database password: ${NEW_DB_PASSWORD}"
        echo -e "FTP password: ${NEW_FTP_PASSWORD}"
        ;;
        
    *)
        echo -e "${RED}Error: Invalid target '${TARGET}'${NC}"
        echo "Usage: sudo ./rotate_password.sh [db|ftp|all]"
        exit 1
        ;;
esac

# Backup del vault anterior
if [ -f "$SECRETS_FILE" ]; then
    BACKUP_FILE="${SECRETS_DIR}/credentials.vault.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$SECRETS_FILE" "$BACKUP_FILE"
    echo -e "${GREEN}✓ Previous vault backed up to ${BACKUP_FILE}${NC}"
fi

# Recrear vault cifrado con nuevas credenciales
echo -e "\n${YELLOW}Re-encrypting vault with new passwords...${NC}"
echo -e "${YELLOW}Enter vault encryption password:${NC}"

# Extraer valores actuales del .env
DB_PASSWORD=$(grep "^DATABASE_URL=" "$ENV_FILE" | sed 's|.*://balaur:\([^@]*\)@.*|\1|')
FTP_PASSWORD=$(grep "^FTP_PASSWORD=" "$ENV_FILE" | cut -d'=' -f2)
SECRET_KEY=$(grep "^SECRET_KEY=" "$ENV_FILE" | cut -d'=' -f2)
ENCRYPTION_KEY=$(grep "^ENCRYPTION_KEY=" "$ENV_FILE" | cut -d'=' -f2)

cat > /tmp/balaur_secrets_new.txt << EOF
# ============================================
# BALAUR SMS - CREDENTIALS VAULT
# Updated: $(date '+%Y-%m-%d %H:%M:%S')
# ============================================

DB_USER=balaur
DB_PASSWORD=${DB_PASSWORD}
DB_NAME=balaur_sms

FTP_USER=balaur
FTP_PASSWORD=${FTP_PASSWORD}

SECRET_KEY=${SECRET_KEY}
ENCRYPTION_KEY=${ENCRYPTION_KEY}

DATABASE_URL=postgresql+asyncpg://balaur:${DB_PASSWORD}@localhost:5432/balaur_sms
EOF

openssl enc -aes-256-cbc -salt -pbkdf2 -in /tmp/balaur_secrets_new.txt -out "${SECRETS_FILE}"
shred -u /tmp/balaur_secrets_new.txt
chmod 400 "${SECRETS_FILE}"

echo -e "${GREEN}✓ Vault updated${NC}"
echo -e "\n${YELLOW}IMPORTANT: Restart backend service to apply changes${NC}"
echo -e "sudo systemctl restart balaur-backend"
