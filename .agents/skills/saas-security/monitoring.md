# Monitoring, Database, & Dependency Security

To maintain app availability, secure your data store, keep dependencies clean of vulnerabilities, and recover quickly in case of outages.

---

## 1. Database Security (Production)

If you are scaling from a local SQLite database to a production PostgreSQL database:

### Avoid Superuser Access
- Never run your application using the database owner / superuser (`postgres`).
- Instead, create a dedicated application-specific user role with restricted privileges:
  ```sql
  CREATE USER resumeai_app WITH PASSWORD 'secure_password';
  GRANT CONNECT ON DATABASE resumeai TO resumeai_app;
  GRANT USAGE, SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO resumeai_app;
  ```

### Encryption at Rest
Ensure your managed database service (e.g. AWS RDS) has **encryption at rest** enabled using AWS KMS (Key Management Service) keys.

### Connection Pooling (PgBouncer)
As traffic increases, open database connections can exhaust server resources. Use a connection pooler like **PgBouncer** placed between the FastAPI application and your database to recycle connection handles:
- Configure PgBouncer in `transaction` mode.
- Update your database connection URL to point to the PgBouncer port (default `6432`).

---

## 2. Dependency Security & Scanning

Outdated libraries are a primary entry point for hackers. Build these rules into your team standard:

- **Lock Library Versions:** Always pin dependency versions in [requirements.txt](file:///c:/Users/Ayush123/Desktop/resume-saas-main/resume-saas-main/backend/requirements.txt) (e.g., `openai==1.57.0`) or use a lockfile (`poetry.lock` / `pipfile.lock`) to prevent automatic upgrades of unverified packages.
- **Run Vulnerability Scans:** Scan your python environment weekly using `pip-audit`:
  ```bash
  pip-audit -r backend/requirements.txt
  ```
- **Dependabot Integration:** Enable **GitHub Dependabot** to monitor your repository dependencies. Dependabot automatically checks for CVE vulnerability notices and files pull requests with package upgrades.

---

## 3. Disaster Recovery Runbook

Use this checklist to restore services in the event of an outage:

### EC2 Instance Failure / Crash
1. Provision a new EC2 instance in the AWS Console.
2. Clone the repository and configure `.env` variables from your secrets manager.
3. Setup Docker containers:
   ```bash
   docker-compose up --build -d
   ```
4. Run the security hardening script:
   ```bash
   sudo ./scripts/setup_ec2_security.sh
   ```

### Database Corruption
1. Terminate active application connections (stop Nginx / FastAPI).
2. Restore the latest backup sql.gz file:
   ```bash
   gunzip < db_backup.sql.gz | psql -U postgres -d resumeai_db
   ```
3. Run tests to confirm data consistency, then reload services.

### Lost SSH Key
1. If your key is lost, you cannot log into the instance.
2. In AWS Console:
   - Go to EC2 instance settings.
   - Use **EC2 Instance Connect** (browser-based SSH terminal) if enabled.
   - Or stop the instance, detach the root EBS volume, mount it to a temporary helper instance, append your new public key to `/home/ubuntu/.ssh/authorized_keys`, detach, and remount it to the original instance.

### AWS Region Outage
1. Maintain backup templates/images (AMIs) in a secondary AWS region (e.g. `us-west-2`).
2. Point your DNS (Route 53 / Cloudflare) to the secondary region ip address.
3. Spin up the backup EC2 instance using the AMI and mount your latest database backup.
