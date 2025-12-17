#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
source "$SCRIPT_DIR/utils/logger.sh"

log_section "Security Hardening"

# Configure UFW
log_step "Configuring UFW firewall..."
if ! command -v ufw &>/dev/null; then
    DEBIAN_FRONTEND=noninteractive apt-get install -y ufw >> "$LOG_FILE" 2>&1
fi

ufw --force reset >> "$LOG_FILE" 2>&1
ufw default deny incoming >> "$LOG_FILE" 2>&1
ufw default allow outgoing >> "$LOG_FILE" 2>&1
ufw allow 22/tcp comment 'SSH' >> "$LOG_FILE" 2>&1
ufw allow 80/tcp comment 'HTTP' >> "$LOG_FILE" 2>&1
ufw allow 443/tcp comment 'HTTPS' >> "$LOG_FILE" 2>&1
ufw allow 21/tcp comment 'FTP Control' >> "$LOG_FILE" 2>&1
ufw allow 49152:65534/tcp comment 'FTP Passive' >> "$LOG_FILE" 2>&1

echo "y" | ufw enable >> "$LOG_FILE" 2>&1
log_success "UFW configured"

# Install and configure fail2ban
log_step "Installing fail2ban..."
DEBIAN_FRONTEND=noninteractive apt-get install -y fail2ban >> "$LOG_FILE" 2>&1

cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true

[nginx-http-auth]
enabled = true

[proftpd]
enabled = true
EOF

systemctl restart fail2ban
systemctl enable fail2ban
log_success "Fail2ban configured"

# Configure logrotate
log_step "Configuring log rotation..."
cat > /etc/logrotate.d/balaur-sms << 'EOF'
/var/log/balaur/backend/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 balaur-app balaur-app
    sharedscripts
    postrotate
        systemctl reload balaur-backend > /dev/null 2>&1 || true
    endscript
}

/var/log/proftpd/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 proftpd proftpd
    sharedscripts
    postrotate
        systemctl reload proftpd > /dev/null 2>&1 || true
    endscript
}

/var/log/nginx/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload nginx > /dev/null 2>&1 || true
    endscript
}
EOF

log_success "Logrotate configured"

log_success "Security hardening complete"