# AI & Application API Security — cost control and abuse protection

Because AI API endpoints (like GLM-5 or Bedrock) incur direct usage costs, they are the highest-risk target for financial abuse. Protect them using a multi-layered check before calling the AI model.

---

## 1. AI Cost Protection Pipeline

For every incoming rewrite or tailoring request, the backend executes the following checks in sequence to prevent cost exposure:

```text
       [Incoming Request]
               │
     [1. JWT Authentication] ─────(Invalid)───> [401 Unauthorized]
               │ (Valid)
     [2. Rate Limit Check]   ─────(Exceeded)──> [429 Too Many Requests]
               │ (Pass)
     [3. Daily Quota Check]  ─────(Exceeded)──> [429 Quota Exceeded]
               │ (Pass)
     [4. Input Validation]   ─────(Malformed)─> [400 Bad Request]
               │ (Valid)
  [5. Prompt Size Validation]─────(> 2MB)─────> [413 Payload Too Large]
               │ (Pass)
  [6. Duplicate Request Cache]────(Hit)───────> [Return Cached Result]
               │ (Miss)
     [7. Abuse Detection]    ─────(Flagged)───> [Temporary IP Block]
               │ (Clear)
      [GLM / Bedrock API]
               │
          [Log Usage]
```

---

## 2. API Abuse Detection Heuristics

Go beyond simple request rate-limiting by configuring your application to monitor and block the following abuse indicators:

### IP Account Creation Limits
- **Heuristic:** Monitor the number of user account registrations coming from a single IP address.
- **Rule:** If an IP registers more than **3 accounts in a 10-minute window**, block registrations from that IP for 2 hours.

### Bulk Tailoring Restrictions
- **Heuristic:** Monitor the volume of resume optimizations/checks performed by a single user account.
- **Rule:** If a single account performs more than **10 optimizations in an hour**, temporarily flag the user and suspend their ability to invoke the AI API for 12 hours.

### Repeated Identical / Large Payloads
- **Heuristic:** Flag users sending large, duplicated string prompts or payloads.
- **Rule:** If a user sends the exact same resume/job description combination more than 3 times in a row, block the request and return the cached result. Reject any single text prompt size exceeding **10,000 characters**.

---

## 3. Core API Protections

### JWT Authentication
Ensure a valid, signed JWT is present on the `Authorization` header of all AI-related router endpoints (`/api/analyze`, `/api/improve-ats`). Anonymous access must be blocked.

### Daily User Quotas
Save optimization counts in your database. Track user limits on a rolling 24-hour window:
- **Free users:** 5 tailoring actions / 10 ATS score checks per day.
- **Pro users:** 100 tailoring actions per day.

### Request Body & File Size Validation
- Nginx blocks payloads over **10MB** (`client_max_body_size 10M;`).
- FastAPI validates file type and checks input string lengths before parsing to prevent CPU/memory exhaustion.

### CORS Restriction
Configure the FastAPI CORS middleware in [main.py](file:///c:/Users/Ayush123/Desktop/resume-saas-main/resume-saas-main/backend/main.py) to reject requests from domains other than your verified production frontend:
```python
# In production, change this from "*" to:
origins = [
    "https://resume-ai-sigma-pied.vercel.app",
    "https://yourdomain.com"
]
```
