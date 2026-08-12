# Firewall Configuration (UFW)

Uncomplicated Firewall (UFW) blocks direct connection attempts to backend ports on the server operating system.

---

## 1. Rules Strategy

- **FastAPI / Uvicorn Port 8000:** MUST be blocked publicly. Only Nginx is allowed to talk to port 8000 internally.
- **Port 80 (HTTP) & 443 (HTTPS):** Open to allow public domain requests to reach Nginx.
- **Port 22 (SSH):** Restricted as tightly as possible.

---

## 2. Command Reference

### Standard Hardening Setup
```bash
# Set default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH, HTTP, HTTPS
sudo ufw allow 22/tcp comment "SSH"
sudo ufw allow 80/tcp comment "HTTP"
sudo ufw allow 443/tcp comment "HTTPS"

# Explicitly deny direct access to FastAPI port
sudo ufw deny 8000/tcp comment "Block direct FastAPI access"

# Enable firewall
sudo ufw --force enable
```

### Checking Status
```bash
sudo ufw status verbose
```
Example output:
```text
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), disabled (routed)
New profiles: skip

To                         Action      From
--                         ------      ----
22/tcp (SSH)               ALLOW IN    Anywhere
80/tcp (HTTP)              ALLOW IN    Anywhere
443/tcp (HTTPS)            ALLOW IN    Anywhere
8000/tcp                   DENY IN     Anywhere
```
