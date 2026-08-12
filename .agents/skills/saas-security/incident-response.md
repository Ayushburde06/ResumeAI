# Incident Response Playbook

An operational guide detailing step-by-step actions to take when responding to active security incidents.

---

## Scenario A: API Key Compromise (Leaked Key)

If your GLM-5 or Bedrock API key is leaked in a public commit or logs:

1. **Rotate the Key immediately:**
   - Go to your AI provider console (AWS Bedrock / Zhipu).
   - Generate a new API key.
2. **Update the Server:**
   - SSH into your EC2 instance.
   - Update `GLM_API_KEY` or `AWS_BEARER_TOKEN_BEDROCK` in your production `backend/.env` file.
   - Restart the server process (`sudo systemctl restart resumeai`).
3. **Revoke the Leaked Key:**
   - Go back to the provider console and **delete** the compromised key.
   - Inspect the logs for unauthorized calls and note the token usage.

---

## Scenario B: Active DDoS / Request Flood

If your server becomes unresponsive and you see massive IP requests in `access.log`:

1. **Verify Fail2ban Status:**
   Ensure Fail2ban has successfully jailed the offending IPs:
   ```bash
   sudo fail2ban-client status nginx-limit-req
   ```
2. **Block IPs manually via UFW:**
   If a specific IP or subnet is evading Fail2ban, block it manually:
   ```bash
   sudo ufw insert 1 deny from <IP_ADDRESS> to any
   ```
3. **Turn on Cloudflare Under Attack Mode:**
   If using Cloudflare:
   - Log in to your Cloudflare Dashboard.
   - Go to **Overview** → **Quick Actions** → Toggle **Under Attack Mode** to **ON**.
   - This challenges all visitors with a JS challenge before they can reach Nginx.

---

## Scenario C: Unexpected AI Cost Spike (Billing Alert)

If you receive a high billing alert from AWS/Zhipu:

1. **Audit Logs:**
   Identify if the spike was caused by:
   - A single compromised account/token.
   - A rate-limiting bypass.
   - Excessive loop calls in the frontend code.
2. **Increase Rate Limits:**
   Temporarily throttle limits in `/etc/nginx/sites-available/resumeai`:
   - Reduce the AI zone rate (e.g., from `5r/m` to `2r/m`).
   - Reload Nginx (`sudo systemctl reload nginx`).
3. **Enforce Database Quotas:**
   Lower the daily user quotas for free accounts in your backend config until the source of abuse is isolated.
