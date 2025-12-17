#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
source "$SCRIPT_DIR/modules/utils/logger.sh"

log_section "ProFTPD Setup"

# Install ProFTPD
log_step "Installing ProFTPD..."
DEBIAN_FRONTEND=noninteractive apt-get install -y proftpd openssl proftpd-mod-ldap >> "$LOG_FILE" 2>&1
log_success "ProFTPD installed"

# Generate SSL certificate
log_step "Generating SSL certificate for FTPS..."
if [ ! -f /etc/ssl/certs/proftpd.crt ]; then
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/ssl/private/proftpd.key \
        -out /etc/ssl/certs/proftpd.crt \
        -subj "/CN=ftp.balaur.local" >> "$LOG_FILE" 2>&1
    chmod 600 /etc/ssl/private/proftpd.key
    log_success "SSL certificate generated"
else
    log_info "SSL certificate already exists"
fi

# Create FTP users and groups
log_step "Creating FTP users and groups..."
if ! id "balaur" &>/dev/null; then
    useradd -m -d /srv/ftp/balaur -s /bin/bash balaur
    log_success "User balaur created"
else
    log_info "User balaur already exists"
fi

getent group balaur-upload &>/dev/null || groupadd balaur-upload
getent group balaur-download &>/dev/null || groupadd balaur-download

usermod -a -G balaur-upload,balaur-download balaur
usermod -a -G balaur-upload,balaur-download balaur-app

log_success "FTP users and groups configured"

# Create directory structure
log_step "Creating FTP directory structure..."
mkdir -p /srv/ftp/balaur/{inbox/{pending,processing},repository,quarantine}

# Set ownership and permissions
chown -R balaur:balaur /srv/ftp
chmod 775 /srv/ftp
chown -R balaur:balaur /srv/ftp/balaur
chmod 775 /srv/ftp/balaur
chown -R balaur:balaur-upload /srv/ftp/balaur/inbox
chmod 775 /srv/ftp/balaur/inbox
chmod 775 /srv/ftp/balaur/inbox/pending
chmod 775 /srv/ftp/balaur/inbox/processing
chown -R balaur:balaur-download /srv/ftp/balaur/repository
chmod 775 /srv/ftp/balaur/repository
chmod 775 /srv/ftp/balaur/quarantine
chmod -R g+rw /srv/ftp/balaur
chmod g+s /srv/ftp/balaur/inbox/pending
chmod g+s /srv/ftp/balaur/inbox/processing
chmod g+s /srv/ftp/balaur/quarantine

log_success "FTP directory structure created"

# Copy configuration files from templates
log_step "Configuring ProFTPD..."
cp "$SCRIPT_DIR/templates/proftpd.conf.template" /etc/proftpd/proftpd.conf
cp "$SCRIPT_DIR/templates/proftpd-tls.conf.template" /etc/proftpd/tls.conf

# Test configuration
proftpd -t >> "$LOG_FILE" 2>&1 || {
    log_error "ProFTPD configuration test failed"
    exit 1
}
log_success "ProFTPD configuration valid"

# Restart ProFTPD
log_step "Starting ProFTPD..."
systemctl restart proftpd
systemctl enable proftpd
wait_for_service proftpd 30
log_success "ProFTPD started"

# Test permissions
log_step "Testing FTP permissions..."
sudo -u balaur-app bash -c "touch /srv/ftp/balaur/inbox/pending/test.txt && rm /srv/ftp/balaur/inbox/pending/test.txt" || {
    log_error "Permission test failed"
    exit 1
}
log_success "FTP permissions OK"

log_success "ProFTPD setup complete"