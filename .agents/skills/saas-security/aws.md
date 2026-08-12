# AWS Infrastructure & CI/CD Security

Hardening your AWS cloud infrastructure and deployment pipeline is the first line of defense against network attacks and API credential abuse.

---

## 1. Security Groups (EC2 Instance)

Your EC2 security group acts as a virtual firewall. In the AWS Console, configure your security group rules exactly as follows:

### Inbound Rules (Ingress)
- **HTTPS (Port 443):** Source `0.0.0.0/0` (or Cloudflare IP ranges if proxying).
- **HTTP (Port 80):** Source `0.0.0.0/0` (only used to redirect to HTTPS).
- **SSH (Port 22):** Source `<YOUR_IP_ADDRESS>/32` (NEVER open to `0.0.0.0/0`).
- **Application Port (8000):** **NO** inbound rule should exist for port 8000. It must remain blocked from the public internet.

---

## 2. AWS Free Tier Considerations (Memory Hardening)

On AWS Free Tier EC2 instances (such as `t2.micro` or `t3.micro`), you only have **1 GB of RAM**. To prevent server freezes and out-of-memory (OOM) crashes:

### 🚫 DO NOT Run:
- Heavy monitoring stacks (**Prometheus**, **Grafana**, ELK/Elasticsearch).
- Orchestration frameworks (**Kubernetes** / k3s).
- Local memory-heavy search databases.

### Key SaaS Stack (Memory Optimized):
Stick strictly to a minimal, high-efficiency stack:
- **Nginx** (reverse proxy, static file server).
- **FastAPI** (Uvicorn / Gunicorn backend).
- **PostgreSQL** or local **SQLite**.
- **Fail2Ban** (security scanning).
- **UFW** (kernel firewall).

*Tip:* Create a **2 GB Swap file** on the EC2 instance to act as emergency virtual memory in case of resource spikes.

---

## 3. Secrets Management & Git Scanning

### Secret Protection Invariants
- Never commit `.env` or other credential files to Git. 
- A baseline template [.env.example](file:///c:/Users/Ayush123/Desktop/resume-saas-main/resume-saas-main/backend/.env.example) should be used as a setup reference without containing real secret keys.
- Rotate GLM / Bedrock API keys immediately if you suspect a leak.

### Emergency Key Rotation Procedure
If an API key is committed or leaked:
1. **Revoke immediately:** Go to the provider console (AWS IAM console / Bedrock runtime) and disable/deactivate the key.
2. **Generate replacement:** Create a new key.
3. **Update production:** SSH into EC2, update the `backend/.env` file, and reload the server:
   ```bash
   sudo systemctl restart resumeai
   ```
4. **Purge Git History:** If the key was pushed to GitHub, use `git-filter-repo` or BFG Repo-Cleaner to completely wipe the secret-carrying commits from your repository history.

### Automated Git Secret Scanning
Prevent committing secrets by using pre-commit hooks or CI actions like **Gitleaks** or **TruffleHog**:
- **Local Hook:** Install Gitleaks locally:
  ```bash
  gitleaks detect --verbose
  ```
- **GitHub Action Integration:** Add Gitleaks to your repo workflows to block pull requests containing secrets.

---

## 4. CI/CD Deployment Security

If automating deployments using GitHub Actions or AWS CodePipeline:

- **Use Repository Secrets:** Never write API keys or SSH keys in your workflow files. Store them in **GitHub Actions Secrets** (e.g. `secrets.SSH_PRIVATE_KEY`, `secrets.API_TOKEN`) and inject them at run-time as environment variables.
- **Mask Logs:** Ensure secrets are never printed in build or test execution logs.
- **Branch Protection:** Enable branch protection rules on your `main` branch (require approvals, block direct pushes).
- **Deployment Flow:** Never edit or tweak code files directly on the production EC2 server. Use the following structured deployment pipeline:

```text
  GitHub Repository
         │
   [Push to main]
         │
  GitHub Actions CI (runs tests & lint checks)
         │ (Success)
  SSH Deployment Trigger to EC2
         │
    [git pull] (fetch latest main)
         │
    [pip install] (update dependency env)
         │
    [alembic upgrade] (run database migrations)
         │
    [npm run build] (build frontend assets)
         │
  [systemctl restart] (restart the resumeai service)
```
Keep production environments completely isolated from development.
