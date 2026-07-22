#!/bin/bash
# =============================================================================
# ResumeAI — Auto Recovery & Watchdog
# Runs every minute via cron. Checks health, restarts if down,
# cleans disk, rotates logs. Set it and forget it.
#
# Install (run once on EC2):
#   chmod +x auto_recovery.sh
#   sudo ./auto_recovery.sh --install
#
# Manual health check:
#   sudo ./auto_recovery.sh --check
# =============================================================================

APP_SERVICE="resumeai"
APP_PORT=8000
HEALTH_URL="http://localhost:$APP_PORT/health"
LOG_FILE="/var/log/resumeai_watchdog.log"
APP_DIR="/home/ubuntu/resume-saas/backend"
MAX_DISK_PERCENT=85     # restart + cleanup if disk > 85%
MAX_MEM_PERCENT=90      # restart app if memory > 90%

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# ── Install mode: set up cron + log rotation + systemd watchdog ───────────────
if [[ "$1" == "--install" ]]; then
    echo "=== Installing ResumeAI Auto-Recovery ==="

    # Copy script to permanent location
    cp "$0" /usr/local/bin/resumeai_watchdog.sh
    chmod +x /usr/local/bin/resumeai_watchdog.sh

    # Add to cron — run every minute
    (crontab -l 2>/dev/null | grep -v resumeai_watchdog; \
     echo "* * * * * /usr/local/bin/resumeai_watchdog.sh --check >> /var/log/resumeai_watchdog.log 2>&1") \
     | crontab -
    echo "Cron watchdog installed (every 1 minute)."

    # Log rotation — keep 7 days of logs, max 50MB per file
    cat > /etc/logrotate.d/resumeai << 'EOF'
/var/log/resumeai_watchdog.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    size 50M
}
/home/ubuntu/resume-saas/backend/logs/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    size 100M
}
EOF
    echo "Log rotation configured."

    # Systemd hardening — memory limit + auto-restart
    mkdir -p /etc/systemd/system/resumeai.service.d
    cat > /etc/systemd/system/resumeai.service.d/hardening.conf << 'EOF'
[Service]
# Auto-restart on any failure
Restart=always
RestartSec=10
StartLimitIntervalSec=120
StartLimitBurst=5

    # Memory limit — prevent OOM from taking down the whole server
MemoryLimit=800M
MemorySwapMax=0

# Clean process tree shutdown
KillMode=mixed
TimeoutStopSec=30
EOF

    systemctl daemon-reload
    systemctl restart resumeai
    echo "Systemd hardening applied (memory limit 800M, auto-restart)."

    # Weekly git pull + restart (keep code up to date)
    cat > /etc/cron.weekly/resumeai_update << 'EOF'
#!/bin/bash
cd /home/ubuntu/resume-saas
git pull origin main --quiet
systemctl restart resumeai
echo "[$(date)] Weekly update pulled and restarted" >> /var/log/resumeai_watchdog.log
EOF
    chmod +x /etc/cron.weekly/resumeai_update
    echo "Weekly auto-update cron installed."

    echo ""
    echo "=== Auto-Recovery installed successfully ==="
    echo "  Watchdog: every 1 minute"
    echo "  Log:      $LOG_FILE"
    echo "  Update:   weekly git pull"
    exit 0
fi

# ── Check mode: runs every minute via cron ────────────────────────────────────
if [[ "$1" != "--check" ]]; then
    echo "Usage: $0 --install | --check"
    exit 1
fi

# 1. Is the service running?
if ! systemctl is-active --quiet "$APP_SERVICE"; then
    log "ALERT: $APP_SERVICE is not running. Restarting..."
    systemctl restart "$APP_SERVICE"
    sleep 5
    if systemctl is-active --quiet "$APP_SERVICE"; then
        log "OK: Service restarted successfully."
    else
        log "ERROR: Service failed to restart. Check: journalctl -u $APP_SERVICE -n 30"
    fi
fi

# 2. Health check — does the API actually respond?
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$HEALTH_URL" 2>/dev/null)
if [[ "$HTTP_STATUS" != "200" ]]; then
    log "ALERT: Health check failed (HTTP $HTTP_STATUS). Restarting service..."
    systemctl restart "$APP_SERVICE"
    sleep 8
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$HEALTH_URL" 2>/dev/null)
    if [[ "$HTTP_STATUS" == "200" ]]; then
        log "OK: Service recovered after restart (HTTP $HTTP_STATUS)."
    else
        log "ERROR: Service still unhealthy after restart (HTTP $HTTP_STATUS)."
    fi
fi

# 3. Memory guard — if RAM usage is critical, restart the app
MEM_USED=$(free | awk '/Mem:/ {printf "%.0f", $3/$2 * 100}')
if [[ "$MEM_USED" -gt "$MAX_MEM_PERCENT" ]]; then
    log "ALERT: Memory at ${MEM_USED}% — restarting $APP_SERVICE to free RAM..."
    systemctl restart "$APP_SERVICE"
    log "OK: Service restarted due to high memory."
fi

# 4. Disk guard — clean logs if disk is full
DISK_USED=$(df / | awk 'NR==2 {print $5}' | tr -d '%')
if [[ "$DISK_USED" -gt "$MAX_DISK_PERCENT" ]]; then
    log "ALERT: Disk at ${DISK_USED}%. Cleaning up..."

    # Clean Python cache
    find "$APP_DIR" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find "$APP_DIR" -name "*.pyc" -delete 2>/dev/null || true

    # Truncate old logs
    journalctl --vacuum-time=3d --quiet 2>/dev/null || true

    DISK_AFTER=$(df / | awk 'NR==2 {print $5}' | tr -d '%')
    log "OK: Disk cleaned. Before: ${DISK_USED}% → After: ${DISK_AFTER}%"
fi

exit 0
