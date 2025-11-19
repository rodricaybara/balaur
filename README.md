# Balaur SMS (Software Management System)

Balaur SMS is a full‑stack software inventory and distribution platform built with **FastAPI (Python)** and **Vue.js**. It provides a secure and scalable backend for managing software packages, documentation, and sensitive license keys across an institutional environment.

The system is designed for universities, enterprises, or IT‑intensive environments that require strict control over software distribution, versioning, authentication, and auditing.

---

## 🚀 Key Features

### **Backend (FastAPI)**

* **Modular, service‑oriented architecture** using FastAPI, Pydantic, and SQLAlchemy.
* **Role‑Based Access Control (RBAC)** with granular permissions for different user roles.
* **Secure authentication** using JWT access and refresh tokens.
* **Software catalog management** with versioning and metadata.
* **Integrity‑checked file storage** using SHA‑256 validation.
* **Encrypted license storage** using AES‑GCM.
* **LDAP integration** for enterprise authentication scenarios.
* **Full audit logging** for all critical system actions.
* **Alembic migrations** for reliable database evolution.
* **Extensive service layer** for clean separation of domain logic.

### **Frontend (Vue.js)**

* Modern, responsive UI built with Vue 3 and Vite.
* Session management with JWT.
* Dashboard for software management and user administration.
* Secure download flows for software installers and assets.
* Interactive logs, audit history, and license visibility (restricted by role).

### **Infrastructure & Storage**

* **FTP-based storage** for binary files.
* PostgreSQL as the primary database.
* Environment-based configuration via `.env`.

---

## 🧱 Architecture Overview

Balaur SMS follows a clean, layered backend architecture:

```
backend/
  api/         → Route handlers (v1 endpoints)
  core/        → Config, logging, security, utilities
  models/      → SQLAlchemy ORM models
  schemas/     → Pydantic request/response models
  services/    → Business logic and domain operations
  storage/     → Storage handlers (FTP)
  utils/       → Crypto, hashing, validation tools
```

This makes the system scalable, maintainable, and easy to extend.

---

## 🛡 Security Model

Balaur implements:

* **JWT-based authentication**
* **RBAC with 4 primary user roles**
* **AES‑GCM encryption** for software license keys and secrets
* **Audit logs** for all sensitive actions
* **Strict file validation** (extension + MIME + checksum)

This ensures safe handling of software installers and confidential licensing data.

---

## 📄 License

This project is licensed under the **GNU GPLv3**.

---

## 🐉 About the Name "Balaur"

A *balaur* is a mythical multi‑headed dragon from Eastern European folklore. The name reflects the system's ability to handle multiple components—software versions, licenses, audit events, user roles—working together under a unified platform.

---

If you need a refined version, a shorter variant, or a richer technical version for enterprise documentation, just let me know!

