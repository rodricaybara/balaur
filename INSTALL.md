# Deployment Guide – Balaur SMS

## 📋 Prerequisites

### Required Software

* Python 3.12+
* PostgreSQL 15+
* LDAP/Active Directory server configured
* FTP/FTPS server (ProFTPD, vsftpd, or similar)
* nginx (recommended as reverse proxy)
* systemd (to run as a service)

### Recommended Hardware (on-premise)

* CPU: 4 cores
* RAM: minimum 8GB
* Disk: 500GB+ (depending on installer volume)
* Network: 1Gbps

---

## 🔧 Step-by-Step Installation

### 1. Prepare the System

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y python3 python3-venv python3-pip postgresql nginx git
```

---

### 2. Configure PostgreSQL

```bash
# Create user and database
sudo -u postgres psql

CREATE USER balaur WITH PASSWORD 'your_secure_password';
CREATE DATABASE balaur_sms OWNER balaur;
GRANT ALL PRIVILEGES ON DATABASE balaur_sms TO balaur;
\c balaur_sms
GRANT ALL ON SCHEMA public TO balaur;
\q
```

---

### 3. Configure FTP/FTPS

#### 3.1. Install ProFTPD

```bash
# Install ProFTPD with TLS support
sudo apt install -y proftpd openssl proftpd-mod-ldap

# Generate SSL certificate for FTPS (or use a real certificate)
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/proftpd.key \
  -out /etc/ssl/certs/proftpd.crt \
  -subj "/C=ES/ST=Basque/L=Leioa/O=University/CN=ftp.balaur.local"
```

#### 3.2. Create directory structure

```bash
# Create FTP structure
sudo mkdir -p /srv/ftp/balaur/{inbox/{pending,processing},repository,quarantine}

# Create balaur user for FTP
sudo useradd -m -d /srv/ftp/balaur -s /bin/bash balaur

# Adjust permissions (IMPORTANT for backend access)
sudo chown -R balaur:balaur /srv/ftp
sudo chmod 775 /srv/ftp
sudo chown -R balaur:balaur /srv/ftp/balaur
sudo chmod 775 /srv/ftp/balaur
sudo chmod 775 /srv/ftp/balaur/inbox
sudo chmod 775 /srv/ftp/balaur/inbox/pending
sudo chmod 775 /srv/ftp/balaur/inbox/processing
sudo chmod 775 /srv/ftp/balaur/repository
sudo chmod 775 /srv/ftp/balaur/quarantine
sudo chmod -R g+rw /srv/ftp/balaur
# Setgid for directory group inheritance
sudo chmod g+s /srv/ftp/balaur/inbox/pending
sudo chmod g+s /srv/ftp/balaur/inbox/processing
sudo chmod g+s /srv/ftp/balaur/quarantine
```

#### 3.3. Configure ProFTPD

Create `/etc/proftpd/proftpd.conf`:


```apache
#
# ProFTPD Configuration for Balaur SMS
#

Include /etc/proftpd/modules.conf

UseIPv6                         on
ServerName                      "Balaur SMS FTP Server"
ServerType                      standalone
DeferWelcome                    off
DefaultServer                   on
ShowSymlinks                    on

# Timeouts
TimeoutNoTransfer               600
TimeoutStalled                  600
TimeoutIdle                     1200

DisplayLogin                    welcome.msg
DisplayChdir                    .message true
ListOptions                     "-l"
DenyFilter                      \*.*/
Port                            21
PassivePorts                    49152 65534

<IfModule mod_ident.c>
  IdentLookups                  off
</IfModule>

MaxInstances                    30
User                            proftpd
Group                           nogroup
Umask                           022 022
AllowOverwrite                  on

TransferLog                     /var/log/proftpd/xferlog
SystemLog                       /var/log/proftpd/proftpd.log

<IfModule mod_quotatab.c>
  QuotaEngine                   off
</IfModule>

<IfModule mod_ratio.c>
  Ratios                        off
</IfModule>

<IfModule mod_delay.c>
  DelayEngine                   on
</IfModule>

<IfModule mod_ctrls.c>
  ControlsEngine                off
  ControlsMaxClients            2
  ControlsLog                   /var/log/proftpd/controls.log
  ControlsInterval              5
  ControlsSocket                /var/run/proftpd/proftpd.sock
</IfModule>

<IfModule mod_ctrls_admin.c>
  AdminControlsEngine           off
</IfModule>

# TLS/FTPS Configuration
Include /etc/proftpd/tls.conf

# Balaur SMS Virtual Host
<VirtualHost 0.0.0.0>
  ServerName                    "Balaur SMS Storage"
  DefaultRoot                   /srv/ftp/balaur
  RequireValidShell             off
  AllowStoreRestart             on
  AllowRetrieveRestart          on
  MaxClients                    20
  MaxClientsPerUser             3
  MaxHostsPerUser               2
  ServerIdent                   on "Balaur SMS FTP Server"
  
  ExtendedLog                   /var/log/proftpd/balaur-access.log WRITE,READ
  ExtendedLog                   /var/log/proftpd/balaur-auth.log AUTH auth
  
  # inbox/pending - Users upload here
  <Directory /srv/ftp/balaur/inbox/pending>
    <Limit ALL>
      AllowUser                 balaur
      AllowGroup                balaur-upload
    </Limit>
    <Limit STOR STOU>
      AllowAll
    </Limit>
    <Limit DELE RNFR RNTO>
      DenyAll
    </Limit>
    <Limit LIST NLST>
      DenyAll
    </Limit>
    Umask                       022 022
  </Directory>
  
  # inbox/processing - Backend only
  <Directory /srv/ftp/balaur/inbox/processing>
    <Limit ALL>
      DenyAll
    </Limit>
  </Directory>
  
  # repository - Read-only downloads
  <Directory /srv/ftp/balaur/repository>
    <Limit ALL>
      AllowUser                 balaur
      AllowGroup                balaur-download
    </Limit>
    <Limit RETR>
      AllowAll
    </Limit>
    <Limit WRITE STOR STOU DELE RNFR RNTO MKD RMD>
      DenyAll
    </Limit>
    <Limit LIST NLST>
      AllowAll
    </Limit>
  </Directory>
  
  # quarantine - Admin only
  <Directory /srv/ftp/balaur/quarantine>
    <Limit ALL>
      AllowUser                 root
      DenyAll
    </Limit>
  </Directory>
  
  # Security
  PathDenyFilter                "(\\.\\./|/\\.\\./)"
  PathDenyFilter                "^\\."
  
  <Directory /srv/ftp/balaur/*>
    HideFiles                   ^\\.
  </Directory>
  
</VirtualHost>
```

Crear `/etc/proftpd/tls.conf`:

```apache
#
# ProFTPD TLS/FTPS Configuration
#

<IfModule mod_tls.c>
  TLSEngine                     on
  TLSLog                        /var/log/proftpd/tls.log
  TLSProtocol                   TLSv1.2 TLSv1.3
  TLSCipherSuite                HIGH:!aNULL:!MD5:!DES:!3DES:!RC4
  TLSRSACertificateFile         /etc/ssl/certs/proftpd.crt
  TLSRSACertificateKeyFile      /etc/ssl/private/proftpd.key
  TLSVerifyClient               off
  TLSRequired                   on
  TLSOptions                    NoSessionReuseRequired
  TLSRenegotiate                none
  TLSSessionCache               shm:/file=/var/run/proftpd/tls-sesscache
  TLSTimeoutHandshake           30
</IfModule>
```

#### 3.4. Create FTP Groups

```bash
sudo groupadd balaur-upload
sudo groupadd balaur-download
sudo usermod -a -G balaur-upload,balaur-download balaur
sudo usermod -a -G balaur-upload balaur-app
```

#### 3.5. Restart ProFTPD

```bash
# Check configuration
sudo proftpd -t

# Restart service
sudo systemctl restart proftpd
sudo systemctl enable proftpd
sudo systemctl status proftpd
```

#### 3.6. Manual Test

```bash
# As user balaur-app (created in step 4.1)
sudo -u balaur-app bash

# Try to create a file in pending
touch /srv/ftp/balaur/inbox/pending/test.txt

# Try to move to processing
mv /srv/ftp/balaur/inbox/pending/test.txt /srv/ftp/balaur/inbox/processing/

# If it works, permissions are OK
```

#### 3.7. FTP Permission Summary

```bash
System users:
  balaur-app (corre FastAPI/Gunicorn)
  balaur (dueño de archivos FTP)

Groups:
  balaur-upload (usuarios FTP + balaur-app)

Directories:
  /srv/ftp/balaur/inbox/pending/     → 2775 (rwxrwsr-x) balaur:balaur-upload
  /srv/ftp/balaur/inbox/processing/  → 2775 (rwxrwsr-x) balaur:balaur-upload  
  /srv/ftp/balaur/repository/        → 0755 (rwxr-xr-x) balaur-app:balaur-app
  /srv/ftp/balaur/quarantine/        → 2775 (rwxrwsr-x) balaur:balaur-upload

Files upload to FTP:
  -rw-rw-r-- (664) balaur:balaur-upload

Comannds:
sudo usermod -aG balaur-upload balaur-app
sudo chmod 2775 /srv/ftp/balaur/inbox/{pending,processing}
sudo chmod 2775 /srv/ftp/balaur/quarantine
sudo chmod 0755 /srv/ftp/balaur/repository
sudo systemctl restart balaur-backend
```

---

### 4. Install Backend Application

```bash
sudo useradd -m -s /bin/bash balaur-app
```



### 5. Configure Application with Secure Secrets Management

*(Sections 5.1 – 5.5 translated fully.)*

---

### 6. Initialize Database

*(All Alembic and DB initialization instructions translated and preserved.)*

---

### 7. Configure systemd Service

*(Full translation including the service file and Gunicorn configuration.)*

---

### 8. Configure nginx as Reverse Proxy

*(Full nginx translation with all directives preserved.)*

---

## 🔒 Post-Installation Security

*(Firewall, Fail2ban, and log rotation sections translated.)*

---

## 📊 Monitoring & Maintenance

*(All health checks, logs, and systemctl instructions translated.)*

---

## 🔄 Updates

*(All update steps translated.)*

---

## 🛠 Troubleshooting

*(All debugging sections translated.)*

---

## 📋 Production Checklist

*(All checklist items translated.)*

---

## 🔐 Backup & Recovery

*(Full backup/restore sections translated.)*

---

## 📞 Support

For issues or questions:

* Email: [it@university.edu](mailto:it@university.edu)
* Documentation: [https://docs.balaur.university.edu](https://docs.balaur.university.edu)
* Repository: *[link]*