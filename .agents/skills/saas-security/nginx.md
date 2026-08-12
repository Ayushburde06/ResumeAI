# Nginx Reverse Proxy Config — hardens connections and rate limits

Nginx serves as our reverse proxy. It shields our Uvicorn/FastAPI process, manages SSL/TLS terminations, and rate limits incoming client requests.

---

## 1. Rate Limiting Configurations

Nginx restricts traffic via `limit_req_zone`. Key limits are placed in `/etc/nginx/sites-available/resumeai`:

```nginx
# Zone for AI endpoints (expensive operations — tightest limits)
limit_req_zone $binary_remote_addr zone=ai_endpoints:10m rate=5r/m;

# Zone for auth endpoints (prevents brute forcing)
limit_req_zone $binary_remote_addr zone=auth_endpoints:10m rate=10r/m;

# Zone for general API endpoints
limit_req_zone $binary_remote_addr zone=general_api:10m rate=60r/m;
```

---

## 2. Port Invariants (Crucial Network Security)

Only allow ports 80 (HTTP) and 443 (HTTPS) to be exposed to the public internet. Ensure the following internal services are **never** reachable publicly:

| Service | Default Port | Exposure Rule |
| :--- | :--- | :--- |
| **FastAPI** | `8000` | Blocked (Listen internally to `127.0.0.1:8000` only) |
| **PostgreSQL** | `5432` | Blocked (Listen internally or bind to private subnet) |
| **Redis** | `6379` | Blocked (Bind to local loopback `127.0.0.1`) |
| **Flask** | `5000` | Blocked (Listen internally only) |
| **MongoDB** | `27017` | Blocked (Bind to local loopback) |

---

## 3. Production Application Runner (systemd + Gunicorn)

Never run your application with `python app.py` or running `uvicorn` directly in the shell. In production, run the application as a background service managed by **systemd** wrapping **Gunicorn** with **Uvicorn workers**:

### systemd Service Configuration
Create a service file `/etc/systemd/system/resumeai.service`:
```ini
[Unit]
Description=ResumeAI FastAPI Application
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/var/www/resumeai/backend
EnvironmentFile=/var/www/resumeai/backend/.env
ExecStart=/var/www/resumeai/backend/venv/bin/gunicorn main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 127.0.0.1:8000 --timeout 120

[Install]
WantedBy=multi-user.target
```
Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable resumeai
sudo systemctl start resumeai
```

---

## 4. Restricting Access: Cloudflare vs Direct Traffic

The server script includes a Cloudflare-only filter block.

### To allow ONLY Cloudflare Traffic:
Ensure these lines are active in your server block. Direct traffic bypassing Cloudflare will get `403 Forbidden`:
```nginx
include /etc/nginx/cloudflare_ips.conf;
real_ip_header CF-Connecting-IP;
```

### To Deploy WITHOUT Cloudflare (Direct IP / Domain):
If you are hosting your app on a simple domain or IP without Cloudflare (e.g. for a quick AWS Free Tier MVP), comment out the allow/deny list so Nginx accepts direct connections:
```nginx
# include /etc/nginx/cloudflare_ips.conf;
# real_ip_header CF-Connecting-IP;
```
Reload Nginx to apply changes:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## 5. Connection Limits & Size Caps
- **Max Upload Size:** `client_max_body_size 10M;` (prevents oversized resume uploads exhausting server disk space).
- **Timeouts:** `client_body_timeout 30s; client_header_timeout 15s;` (mitigates Slowloris-style denial of service).
- **Simultaneous Connections:** `limit_conn conn_limit 20;` (restricts maximum open sockets per IP).

---

## 6. TLS / HTTPS Hardening

### HTTP to HTTPS Redirect
Configure Nginx to redirect all unencrypted HTTP traffic (Port 80) to HTTPS (Port 443):
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$host$request_uri;
}
```

### HSTS & Modern TLS Protocols (1.2 / 1.3)
Configure the SSL server block to only allow TLS 1.2 and 1.3, enforce strong ciphers, and set the HSTS (HTTP Strict Transport Security) header:
```nginx
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    # SSL Certificates (managed by Certbot)
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    # TLS Protocols
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';

    # HSTS Header (1 year)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
}
```

### Let's Encrypt / Certbot Auto-Renewal
Install Certbot for automated TLS certificate provisioning and renewal:
```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d api.yourdomain.com
```
Certbot automatically installs a systemd timer or cron job to check and renew certificates twice daily. Verify the renewal dry-run:
```bash
sudo certbot renew --dry-run
```
