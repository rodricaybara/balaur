# Balaur SMS - Automated Installer

Automated installation script for Balaur SMS on Ubuntu 22.04+

## 📁 File Structure

```
backend/scripts/
├── install_balaur.sh # Main script
├── modules/
│ ├── utils/
│ │ ├── logger.sh # Logging functions
│ │ ├── validators.sh # Input validators
│ │ └── prompts.sh # Interactive prompts
│ ├── 00_preflight.sh # Preflight checks
│ ├── 01_system.sh # System preparation
│ ├── 02_postgresql.sh # PostgreSQL Installation
│ ├── 03_ftp.sh # ProFTPD Configuration
│ ├── 04_backend.sh # Backend Installation
│ ├── 05_frontend.sh # Frontend Build
│ ├── 06_nginx.sh # Nginx Configuration
│ ├── 07_security.sh # Security Hardening
│ ├── 08_database.sh # Database Initialization
│ └── 09_postinstall.sh # Final Verifications
├── templates/
│ ├── proftpd.conf.template
│ └── proftpd-tls.conf.template
└── config/
└── install.conf.example # Example configuration
```

## 🚀 Usage

### Interactive Installation (Recommended)

```bash
cd /opt/balaur/backend/scripts
sudo ./install_balaur.sh
```

The script will ask you questions about:
- Server (FQDN/IP)
- Administrator email
- Active Directory/LDAP configuration
- Database
- Sample data (yes/no)

### Unattended Installation

1. **Create configuration file:**

```bash
cp config/install.conf.example config/install.conf
nano config/install.conf
```

2. **Run with configuration:**

```bash
sudo ./install_balaur.sh --config config/install.conf
```

### Installation with Resume

If the installation fails at any step, the progress is saved:

```bash
# The script automatically detects and asks if you want to resume
sudo ./install_balaur.sh
```

## 📋 Prerequisites

- Ubuntu 22.04 LTS or higher
- Root/sudo access
- 8GB RAM minimum
- 4 CPU cores (recommended)
- 50GB disk space
- Internet connection
- Available ports: 80, 443, 21, 8000, 5432

## 🔧 Minimum Required Configuration

### Active Directory / LDAP

You need You must have:
- An accessible LDAP/AD server
- A service user with read permissions
- The service user's DN
- A search base

Example:
```bash
LDAP_SERVER="ldaps://dc.university.edu:636"
LDAP_BIND_DN="cn=balaur-service,ou=Service Accounts,dc=university,dc=edu"
LDAP_SEARCH_BASE="dc=university,dc=edu"
```

### DNS

The server must have:
- A configured hostname
- A functioning DNS server
- (Optional) An A/CNAME record pointing to the server

## 📝 Logs

During installation:
```bash
# Logs are saved in:
/var/log/balaur-install-YYYYMMDD-HHMMSS.log

# View in real time:
tail -f /var/log/balaur-install-*.log
```

After installation:
```bash
# Backend logs
sudo journalctl -u balaur-backend -f
tail -f /var/log/balaur/backend/error.log

# Nginx logs
tail -f /var/log/nginx/balaur-error.log

# ProFTPD logs
tail -f /var/log/proftpd/proftpd.log
```

## ✅ Post-Installation Checks

The script automatically checks:
- ✅ Active services (PostgreSQL, ProFTPD, Nginx, Backend)
- ✅ Listening ports (80, 443, 8000, 21, 5432)
- ✅ API responding in /health
- ✅ Accessible frontend
- ✅ Database with tables
- ✅ Correct file permissions

### Manual Verification

```bash
# Backend API
curl http://localhost:8000/health

# Frontend
curl http://localhost/

# Services
sudo systemctl status balaur-backend
sudo systemctl status nginx
sudo systemctl status postgresql
sudo systemctl status proftpd
```

## 🔐 Security

The script configures:
- ✅ UFW firewall (only necessary ports)
- ✅ Fail2ban (protection against attacks)
- ✅ SSL/TLS (self-signed certificate)
- ✅ Restrictive permissions on sensitive files
- ✅ Log rotation

### Generated Credentials

Passwords are automatically generated and saved in:
```bash
/opt/balaur/secrets/credentials.vault (AES-256 encryption)
```

To view the credentials:
```bash
sudo /opt/balaur/backend/scripts/view_secrets.sh
```

## 🐛 Troubleshooting

### Problem: Script fails at step X

**Solution:**
1. Check the log: `tail -f /var/log/balaur-install-*.log`
2. Fix the problem
3. Rerun the script (it will detect and ask if you want to resume)

### Problem: LDAP not connecting

**Solution:**
```bash
# Check connectivity
telnet dc.university.edu 636

# Manual test after installation
cd /opt/balaur/backend
source venv/bin/activate
python3 scripts/test_ldap.py <username> <password>
```

### Problem: API not responding

**Solution:**
```bash
# View logs
sudo journalctl -u balaur-backend -n 100

# Restart service
sudo systemctl restart balaur-backend
```

### Problem: Frontend not loading

**Solution:**
```bash
# Check nginx
sudo nginx -t
sudo systemctl status nginx

# View logs
tail -f /var/log/nginx/balaur-error.log
```

### Problem: Port already in use

**Solution:**
```bash
# See what's using the port
sudo lsof -i :8000

# Kill process
sudo kill -9 <PID>
`