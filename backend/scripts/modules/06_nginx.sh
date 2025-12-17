#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
source "$SCRIPT_DIR/utils/logger.sh"

log_section "Nginx Configuration"

# Install nginx
log_step "Installing nginx..."
DEBIAN_FRONTEND=noninteractive apt-get install -y nginx >> "$LOG_FILE" 2>&1
log_success "Nginx installed"

# Generate self-signed certificate
log_step "Generating SSL certificate..."
if [ ! -f /etc/ssl/certs/balaur-selfsigned.crt ]; then
    openssl req -x509 -nodes -days 365 \
        -newkey rsa:2048 \
        -keyout /etc/ssl/private/balaur-selfsigned.key \
        -out /etc/ssl/certs/balaur-selfsigned.crt \
        -subj "/CN=$SERVER_NAME" >> "$LOG_FILE" 2>&1
    chmod 600 /etc/ssl/private/balaur-selfsigned.key
    log_success "SSL certificate generated"
else
    log_info "SSL certificate already exists"
fi

# Create nginx configuration
log_step "Creating nginx configuration..."
cat > /etc/nginx/sites-available/balaur-sms << EOF
upstream balaur_backend {
    server 127.0.0.1:8000;
    keepalive 16;
}

server {
    listen 80;
    server_name $SERVER_NAME;

    location /.well-known/acme-challenge/ {
        root /var/www/letsencrypt;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name $SERVER_NAME;

    ssl_certificate /etc/ssl/certs/balaur-selfsigned.crt;
    ssl_certificate_key /etc/ssl/private/balaur-selfsigned.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_stapling on;
    ssl_stapling_verify on;

    access_log /var/log/nginx/balaur-access.log;
    error_log  /var/log/nginx/balaur-error.log warn;

    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    root /opt/balaur/frontend/dist;
    index index.html;

    location ~* \.(?:css|js|svg|ico|png|jpg|jpeg|webp|woff2?|ttf|otf)$ {
        try_files \$uri =404;
        expires 365d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://balaur_backend;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        proxy_buffering off;

        client_max_body_size 10G;
        client_body_timeout 300s;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;

        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /docs {
        proxy_pass http://balaur_backend/docs;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    location /redoc {
        proxy_pass http://balaur_backend/redoc;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    location = /health {
        proxy_pass http://balaur_backend/health;
        proxy_set_header Host \$host;
    }

    location ~ (^|/)\.env$ {
        deny all;
        access_log off;
        log_not_found off;
    }
}
EOF

# Enable site
log_step "Enabling nginx site..."
ln -sf /etc/nginx/sites-available/balaur-sms /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test configuration
log_step "Testing nginx configuration..."
nginx -t >> "$LOG_FILE" 2>&1 || {
    log_error "Nginx configuration test failed"
    exit 1
}
log_success "Nginx configuration valid"

# Restart nginx
log_step "Restarting nginx..."
systemctl restart nginx
systemctl enable nginx
wait_for_service nginx 30
log_success "Nginx started"

log_success "Nginx configuration complete"