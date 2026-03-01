# Secure Cloud Web Application on AWS

A production-grade, security-focused web application deployed on AWS EC2 
following security best practices including least-privilege IAM, encrypted 
storage, HTTPS enforcement, and real-time monitoring.

> **Note:** Live demo available upon request. 

---

## Architecture
```
Internet
    │
    v
[Security Group] ← Firewall: ports 80, 443 only
    │
    v
[Nginx] ← Reverse proxy + SSL termination
    │
    v
[Flask App] ← Running on localhost:8000 only
    │
    v
[IAM Role] ← Temporary credentials, no hardcoded keys
    │         │              │
    v          v              v
   [S3]    [CloudWatch]   [SSM Parameter Store]
```

---

## Tech Stack

- **Cloud:** AWS (EC2, S3, IAM, CloudWatch, SSM, CloudTrail, SNS)
- **Server:** Amazon Linux 2023
- **Web Server:** Nginx (reverse proxy + SSL termination)
- **Application:** Python 3 / Flask
- **Process Manager:** Gunicorn + systemd
- **Containerization:** Docker
- **Monitoring:** AWS CloudWatch

---

## Project Structure
```
├── app/
│   └── app.py                         # Flask web application
├── config/
│   ├── nginx/secure-app.conf          # Nginx reverse proxy config
│   ├── cloudwatch/                    # CloudWatch agent config
│   └── systemd/secure-app.service     # systemd service definition
├── infrastructure/
│   └── iam-policy.json                # Least-privilege IAM policy
├── docs/
│   └── screenshot.png                 # App screenshot
├── Dockerfile                         # Container definition
├── requirements.txt                   # Python dependencies
└── README.md
```

---

## Key Implementation Decisions

**Why IAM Role instead of access keys?**
Access keys are permanent credentials — if stolen they work forever 
from anywhere. IAM roles inject temporary credentials that expire 
every few hours automatically. Even if stolen, they expire before 
causing significant damage.

**Why Nginx in front of Flask?**
Flask's built-in server is single-threaded and not production-ready. 
Nginx handles SSL termination, security headers, and HTTP→HTTPS 
redirection, then forwards clean requests to Gunicorn workers. 
Separation of concerns — the app never handles SSL complexity.

**Why SSM Parameter Store for secrets?**
Secrets in code end up in Git history. Secrets in environment 
variables show up in process listings. SSM Parameter Store is 
encrypted at rest (KMS), access-controlled via IAM, and every 
read is audited. Secrets never touch the filesystem or codebase.

**Why least-privilege IAM policy?**
The EC2 role can only access the specific S3 bucket it needs and 
specific SSM parameters — nothing else. If the server is compromised, 
the damage is contained to those specific resources only.

---

## Monitoring Setup

- **CPU alarm** — triggers if CPU exceeds 80% for 10 minutes
- **Memory alarm** — triggers if memory exceeds 85%
- **Scanning detection** — triggers if 404 errors exceed 20 in 5 minutes
- **All alerts** delivered via SNS email notification
- **CloudTrail** records every AWS API call with full audit trail
- **CloudWatch Agent** ships application logs and system metrics

---

## Local Development
```bash
git clone https://github.com/YOURUSERNAME/secure-aws-app
cd secure-aws-app
pip install -r app/requirements.txt

# Note: SSM Parameter Store calls require AWS credentials
# For local dev set environment variables instead:
export SECRET_KEY=local-dev-key
export APP_ENV=development

python app/app.py
```

---

## What I Learned

- Designing cloud architecture with security as a first principle
- The difference between IAM Users (permanent credentials) and 
  IAM Roles (temporary credentials) and why roles are always 
  preferred for compute resources
- How defense in depth works — Security Groups, Nginx, and the 
  application each add an independent layer of protection
- How to structure monitoring to detect both operational issues 
  (CloudWatch metrics) and attacks (log-based intrusion detection)
- Why least-privilege IAM policies matter and how to write them
- How containerization with Docker ensures consistency between 
  development and production environments

---

## Security Notes

- The `.pem` key file is excluded from this repository
- No AWS credentials are stored in code — IAM roles only
- All secrets stored in AWS SSM Parameter Store
- To deploy yourself follow the setup steps above

---