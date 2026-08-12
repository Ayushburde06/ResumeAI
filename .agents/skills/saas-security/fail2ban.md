# Fail2ban Config — automatically blocks malicious IPs

Fail2Ban monitors log files (such as SSH logins and Nginx access/error logs) and automatically bans IPs showing malicious behavior.

---

## 1. jail.local Configuration

Fail2ban jails are defined in `/etc/fail2ban/jail.local`:

```ini
[DEFAULT]
bantime  = 3600      ; Ban IP for 1 hour
findtime = 600       ; Monitor violations in a 10-minute window
maxretry = 5         ; Ban after 5 violations

# SSH Brute Force protection
[sshd]
enabled  = true
port     = ssh
logpath  = %(sshd_log)s

# Blocks IPs trying to scan for vulnerabilities / PHP admin sites
[nginx-botsearch]
enabled  = true
port     = http,https
logpath  = /var/log/nginx/access.log
maxretry = 20
findtime = 60

# Blocks IPs that trigger repeated 404/403 errors
[nginx-http-auth]
enabled  = true
port     = http,https
logpath  = /var/log/nginx/error.log

# Automatically bans IPs that violate Nginx request limits
[nginx-limit-req]
enabled  = true
port     = http,https
logpath  = /var/log/nginx/error.log
maxretry = 10
```

---

## 2. Managing Banned IPs

### Check Jail Status
To check active bans in a specific jail (e.g. `nginx-limit-req`):
```bash
sudo fail2ban-client status nginx-limit-req
```

### Unban an IP
If a legitimate user gets locked out, unban their IP:
```bash
sudo fail2ban-client set nginx-limit-req unbanip <IP_ADDRESS>
```
