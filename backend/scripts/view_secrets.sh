#!/bin/bash
#
# View encrypted secrets vault
# Location: /opt/balaur/backend/scripts/view_secrets.sh
# Usage: sudo ./view_secrets.sh
#

set -e

SECRETS_FILE="/opt/balaur/secrets/credentials.vault"

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Balaur SMS - View Secrets Vault ===${NC}\n"

# Verificar permisos
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: This script must be run as root${NC}"
    echo "Usage: sudo ./view_secrets.sh"
    exit 1
fi

# Verificar que existe el vault
if [ ! -f "$SECRETS_FILE" ]; then
    echo -e "${RED}Error: Secrets vault not found at ${SECRETS_FILE}${NC}"
    exit 1
fi

# Descifrar y mostrar
echo -e "${YELLOW}Enter vault password:${NC}"
openssl enc -aes-256-cbc -d -pbkdf2 -in "$SECRETS_FILE"

echo -e "\n${YELLOW}Note: Secrets are displayed above. Keep them confidential!${NC}"
