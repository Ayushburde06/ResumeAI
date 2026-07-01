#!/bin/bash
# =============================================================================
# ResumeAI — EC2 Security Hardening Script
# Run once after your EC2 is provisioned:
#   chmod +x setup_ec2_security.sh
#   sudo ./setup_ec2_security.sh
# =============================================================================
set -e

echo "=== [1/6] Updating system packages ==="
apt-get update -qq
apt-get upgrade -y -qq

# =============================================================================
# [2/6] UFW Firewall — block everything except SSH, HTTP, HTTPS
# =============================================================================
echo "=== [2/6] Configuring UFW firewall ==="
apt-get install -y ufw

ufw default deny incoming
ufw default allow outgoing

# SSH — only from your IP if you know it, or leave open and rely on key-only auth
ufw allow 22/tcp comment "SSH"

# HTTP and HTTPS — Cloudflare will sit in front, but keep 80/443 open
ufw allow 80/tcp  comment "HTTP"
ufw allow 443/tcp comment "HTTPS"

# Block direct access to app port from public internet
# (only Nginx should talk to uvicorn on 8000 internally)
ufw deny 8000/tcp comment "Block direct FastAPI access"

ufw --force enable
ufw status verbose
echo "UFW configured."

# =============================================================================
# [3/6] fail2ban — block SSH brute-force and HTTP abuse
# =============================================================================
echo "=== [3/6] Installing fail2ban ==="
apt-get install -y fail2ban

cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime  = 3600      ; ban for 1 hour
findtime = 600       ; within 10 minutes
maxretry = 5         ; after 5 failures

[sshd]
enabled  = true
port     = ssh
logpath  = %(sshd_log)s
backend  = %(sshd_backend)s

[nginx-http-auth]
enabled  = true
port     = http,https
logpath  = /var/log/nginx/error.log

[nginx-botsearch]
enabled  = true
port     = http,https
logpath  = /var/log/nginx/access.log
maxretry = 20
findtime = 60

[nginx-limit-req]
enabled  = true
port     = http,https
logpath  = /var/log/nginx/error.log
maxretry = 10
EOF

systemctl enable fail2ban
systemctl restart fail2ban
echo "fail2ban configured."

# =============================================================================
# [4/6] SSH hardening — key-only auth, no root login, no password auth
# =============================================================================
echo "=== [4/6] Hardening SSH ==="
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak

# Disable password authentication (key-only)
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config

# Disable root login
sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config

# Only allow specific user (change 'ubuntu' to your user)
grep -q "^AllowUsers" /etc/ssh/sshd_config || echo "AllowUsers ubuntu" >> /etc/ssh/sshd_config

# Limit auth attempts
grep -q "^MaxAuthTries" /etc/ssh/sshd_config || echo "MaxAuthTries 3" >> /etc/ssh/sshd_config
grep -q "^LoginGraceTime" /etc/ssh/sshd_config || echo "LoginGraceTime 20" >> /etc/ssh/sshd_config

systemctl restart sshd
echo "SSH hardened."

# =============================================================================
# [5/6] Nginx — rate limiting + Cloudflare-only + security headers
# =============================================================================
echo "=== [5/6] Configuring Nginx with rate limiting ==="
apt-get install -y nginx

# Download current Cloudflare IP ranges (IPv4 + IPv6)
CF_IPV4=$(curl -s https://www.cloudflare.com/ips-v4)
CF_IPV6=$(curl -s https://www.cloudflare.com/ips-v6)

# Build Cloudflare allowlist file
CF_CONF="/etc/nginx/cloudflare_ips.conf"
echo "# Cloudflare IP ranges — auto-generated $(date)" > $CF_CONF
for ip in $CF_IPV4; do echo "allow $ip;"; done >> $CF_CONF
for ip in $CF_IPV6; do echo "allow $ip;"; done >> $CF_CONF
echo "deny all;  # Block non-Cloudflare direct access" >> $CF_CONF

# Write main Nginx config for ResumeAI
cat > /etc/nginx/sites-available/resumeai << 'NGINXEOF'
# ── Rate limit zones ─────────────────────────────────────────────────────────
# Zone for AI endpoints (expensive — very tight)
limit_req_zone $binary_remote_addr zone=ai_endpoints:10m rate=5r/m;
# Zone for auth endpoints
limit_req_zone $binary_remote_addr zone=auth_endpoints:10m rate=10r/m;
# Zone for general API
limit_req_zone $binary_remote_addr zone=general_api:10m rate=60r/m;
# Zone for connection count per IP
limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

server {
    listen 80;
    server_name api.yourdomain.com;   # <-- CHANGE THIS

    # ── Max upload size ───────────────────────────────────────────────────────
    client_max_body_size 10M;
    client_body_timeout  30s;
    client_header_timeout 15s;
    send_timeout 60s;

    # ── Connection limit per IP ───────────────────────────────────────────────
    limit_conn conn_limit 20;

    # ── Only accept traffic from Cloudflare ──────────────────────────────────
    include /etc/nginx/cloudflare_ips.conf;

    # ── Real IP from Cloudflare header ────────────────────────────────────────
    set_real_ip_from 103.21.244.0/22;
    set_real_ip_from 103.22.200.0/22;
    set_real_ip_from 103.31.4.0/22;
    set_real_ip_from 104.16.0.0/13;
    set_real_ip_from 104.24.0.0/14;
    set_real_ip_from 108.162.192.0/18;
    set_real_ip_from 131.0.72.0/22;
    set_real_ip_from 141.101.64.0/18;
    set_real_ip_from 162.158.0.0/15;
    set_real_ip_from 172.64.0.0/13;
    set_real_ip_from 173.245.48.0/20;
    set_real_ip_from 188.114.96.0/20;
    set_real_ip_from 190.93.240.0/20;
    set_real_ip_from 197.234.240.0/22;
    set_real_ip_from 198.41.128.0/17;
    real_ip_header CF-Connecting-IP;

    # ── Security headers ─────────────────────────────────────────────────────
    add_header X-Content-Type-Options   "nosniff"                 always;
    add_header X-Frame-Options          "DENY"                    always;
    add_header Referrer-Policy          "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy       "camera=(), microphone=(), geolocation=()" always;

    # ── Block common attack patterns ─────────────────────────────────────────
    # Block SQL injection attempts in query strings
    if ($query_string ~* "(union.*select|insert.*into|drop.*table|1=1|or%201%3D1)") {
        return 403;
    }
    # Block path traversal
    if ($request_uri ~* "(\.\./|\.\.\\)") {
        return 403;
    }
    # Block common scanner paths
    if ($request_uri ~* "(phpMyAdmin|wp-admin|wp-login|\.env|\.git|\.htaccess|web\.config)") {
        return 403;
    }
    # Block empty user agents (most bots)
    if ($http_user_agent = "") {
        return 403;
    }

    # ── AI endpoints — tightest limits ───────────────────────────────────────
    location ~* ^/api/(analyze|agent-analyze|improve-ats) {
        limit_req zone=ai_endpoints burst=3 nodelay;
        limit_req_status 429;

        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout  120s;
        proxy_send_timeout  120s;
        proxy_connect_timeout 10s;
    }

    # ── Auth endpoints ────────────────────────────────────────────────────────
    location ~* ^/api/auth/(login|register) {
        limit_req zone=auth_endpoints burst=5 nodelay;
        limit_req_status 429;

        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 15s;
    }

    # ── PDF / file export endpoints ───────────────────────────────────────────
    location ~* ^/api/export- {
        limit_req zone=general_api burst=10 nodelay;

        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }

    # ── All other API routes ──────────────────────────────────────────────────
    location /api/ {
        limit_req zone=general_api burst=20 nodelay;

        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 30s;
    }

    # ── Health check (no rate limit) ──────────────────────────────────────────
    location /health {
        proxy_pass http://127.0.0.1:8000;
        proxy_read_timeout 5s;
        access_log off;
    }
}
NGINXEOF

# Enable the site
ln -sf /etc/nginx/sites-available/resumeai /etc/nginx/sites-enabled/resumeai
rm -f /etc/nginx/sites-enabled/default

# Test and reload
nginx -t && systemctl reload nginx
echo "Nginx configured."

# =============================================================================
# [6/6] Auto-update Cloudflare IP list (weekly cron)
# =============================================================================
echo "=== [6/6] Setting up weekly Cloudflare IP refresh ==="
cat > /etc/cron.weekly/refresh-cloudflare-ips << 'CRONEOF'
#!/bin/bash
CF_CONF="/etc/nginx/cloudflare_ips.conf"
CF_IPV4=$(curl -s https://www.cloudflare.com/ips-v4)
CF_IPV6=$(curl -s https://www.cloudflare.com/ips-v6)
echo "# Cloudflare IP ranges — auto-updated $(date)" > $CF_CONF
for ip in $CF_IPV4; do echo "allow $ip;"; done >> $CF_CONF
for ip in $CF_IPV6; do echo "allow $ip;"; done >> $CF_CONF
echo "deny all;" >> $CF_CONF
nginx -t && systemctl reload nginx
CRONEOF
chmod +x /etc/cron.weekly/refresh-cloudflare-ips

# =============================================================================
echo ""
echo "============================================================"
echo "  Security hardening complete."
echo ""
echo "  NEXT STEPS:"
echo "  1. Edit /etc/nginx/sites-available/resumeai"
echo "     Change: server_name api.yourdomain.com"
echo ""
echo "  2. In Cloudflare Dashboard:"
echo "     Security > WAF > Rate Limiting > add rules (see README)"
echo "     SSL/TLS > set to Full"
echo "     Security > Bots > Bot Fight Mode > ON"
echo ""
echo "  3. Restart your app:"
echo "     sudo systemctl restart resumeai"
echo "============================================================"
