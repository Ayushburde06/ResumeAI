---
name: saas-security
description: Multi-layered deployment security, Nginx rate-limiting, Fail2ban, UFW, AWS security groups, and AI API cost protection.
---

# SaaS Security & Hardening Guide — ResumeAI

This guide details how to configure production-grade security, limit cost exposures for the GLM/AI API, and verify server hardening on AWS Free Tier EC2 instances.

---

## EC2 Deployment Architecture

```text
                Internet
                    │
         AWS Security Group
        (80,443 open | 22 only your IP)
                    │
                  Nginx (Reverse Proxy)
         ┌──────────┼──────────┐
         │          │          │
    Rate Limits  HTTPS/TLS  Security Headers
         │          │          │
         └──────────┼──────────┘
                    │
              FastAPI / Flask (behind Gunicorn/Uvicorn)
                    │
      JWT + Quotas + Validation
                    │
        PostgreSQL / SQLite
                    │
              GLM-5 API
```

---

## Production Security Checklist

Verify all checks before promoting a release to public access:

### Infrastructure & OS
- [ ] **HTTPS enabled** (Let's Encrypt / Certbot).
- [ ] **Nginx reverse proxy** (FastAPI backend not publicly exposed on port 8000).
- [ ] **SSH restricted to your IP** (SSH port 22 blocked for all other IPs).
- [ ] **Password authentication disabled** (key-only auth enforced).
- [ ] **Root login disabled** (direct root access disabled in sshd_config).
- [ ] **UFW enabled** (deny incoming default; allow only 22, 80, 443).
- [ ] **Fail2Ban configured** (SSH, Nginx rate limits and authentication monitored).
- [ ] **Automatic backups** configured (regular SQLite copies / PG daily backups).
- [ ] **Monitoring and logs active** (system resources and token spending tracked).

### Web Server (Nginx)
- [ ] **Nginx rate limiting active** (5r/m for AI, 10r/m for auth, 60r/m general).
- [ ] **Security headers enabled** (nosniff, DENY, strict-origin).
- [ ] **CORS restricted** to your frontend production domain (no `*`).
- [ ] **Nginx connection limits enabled** (max 20 active connections per IP).

### Application & API Security
- [ ] **JWT authentication enabled** on all `/api/` endpoints.
- [ ] **Per-user quotas enabled** (rolling 24-hour database limit checks).
- [ ] **Input validation active** (size checks and prompt injection filters).
- [ ] **Secure file uploads** (10MB body cap enforced).
- [ ] **.env excluded from Git** (never committed to repository).
- [ ] **API key rotation procedure documented**.
- [ ] **Regular dependency updates and security scans** (`pip-audit`).

---

## Detailed Security Modules

* **[Nginx Config Guide](file:///c:/Users/Ayush123/Desktop/resume-saas-main/resume-saas-main/.agents/skills/saas-security/nginx.md)**
* **[Fail2Ban Setup Guide](file:///c:/Users/Ayush123/Desktop/resume-saas-main/resume-saas-main/.agents/skills/saas-security/fail2ban.md)**
* **[Firewall Policies](file:///c:/Users/Ayush123/Desktop/resume-saas-main/resume-saas-main/.agents/skills/saas-security/firewall.md)**
* **[AWS Infrastructure Security](file:///c:/Users/Ayush123/Desktop/resume-saas-main/resume-saas-main/.agents/skills/saas-security/aws.md)**
* **[AI & Application Security](file:///c:/Users/Ayush123/Desktop/resume-saas-main/resume-saas-main/.agents/skills/saas-security/api-security.md)**
* **[Monitoring & Logs](file:///c:/Users/Ayush123/Desktop/resume-saas-main/resume-saas-main/.agents/skills/saas-security/monitoring.md)**
* **[Incident Response Playbook](file:///c:/Users/Ayush123/Desktop/resume-saas-main/resume-saas-main/.agents/skills/saas-security/incident-response.md)**
