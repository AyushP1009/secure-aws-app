from flask import Flask, request, jsonify, render_template_string
import boto3
import logging
import os
import json
from datetime import datetime
from botocore.exceptions import ClientError

app = Flask(__name__)

# ─────────────────────────────────────────
# LOGGING SETUP
# All logs go to a file that CloudWatch agent ships to AWS
# ─────────────────────────────────────────
os.makedirs('/var/log/secure-app', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.FileHandler('/var/log/secure-app/app.log'),
        logging.StreamHandler()  # Also print to console
    ]
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# FETCH SECRETS FROM SSM (not hardcoded)
# ─────────────────────────────────────────
def get_ssm_parameter(name):
    """Fetch a parameter from SSM Parameter Store using the EC2 IAM role"""
    try:
        ssm = boto3.client('ssm', region_name='us-east-1')
        response = ssm.get_parameter(Name=name, WithDecryption=True)
        return response['Parameter']['Value']
    except ClientError as e:
        logger.error(f"Failed to fetch SSM parameter {name}: {e}")
        return None

# Fetch secret at startup — no secrets in code or environment variables
SECRET_KEY = get_ssm_parameter('/secure-app/secret-key') or 'fallback-dev-key'
APP_ENV = get_ssm_parameter('/secure-app/app-env') or 'development'

logger.info(f"Application starting in {APP_ENV} environment")

# ─────────────────────────────────────────
# HTML TEMPLATE
# ─────────────────────────────────────────
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Secure AWS App</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: #0f1117;
            color: #e0e0e0;
            min-height: 100vh;
            padding: 40px 20px;
        }
        .container { max-width: 900px; margin: 0 auto; }
        h1 { color: #fff; font-size: 2em; margin-bottom: 5px; }
        .subtitle { color: #888; margin-bottom: 40px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }
        .card {
            background: #1a1d27;
            border: 1px solid #2a2d3a;
            border-radius: 12px;
            padding: 24px;
        }
        .card h2 { font-size: 1em; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 16px; }
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 600;
            margin: 4px 4px 4px 0;
        }
        .badge.green { background: #1a3a2a; color: #4ade80; border: 1px solid #166534; }
        .badge.blue { background: #1a2a3a; color: #60a5fa; border: 1px solid #1e3a5f; }
        .feature-list { list-style: none; }
        .feature-list li { padding: 8px 0; border-bottom: 1px solid #2a2d3a; font-size: 0.9em; }
        .feature-list li:last-child { border-bottom: none; }
        .check { color: #4ade80; margin-right: 8px; }
        .stat { font-size: 2em; font-weight: 700; color: #fff; }
        .stat-label { color: #888; font-size: 0.85em; margin-top: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔒 Secure Cloud Application</h1>
        <p class="subtitle">Deployed on AWS EC2 · IAM Roles · CloudWatch · HTTPS</p>

        <div class="grid">
            <div class="card">
                <h2>System Status</h2>
                <div class="stat">● Online</div>
                <div class="stat-label">{{ timestamp }}</div>
                <br>
                <span class="badge green">{{ environment }}</span>
                <span class="badge blue">Amazon Linux 2023</span>
            </div>

            <div class="card">
                <h2>Security Features</h2>
                <ul class="feature-list">
                    <li><span class="check">✓</span>HTTPS / SSL (Let's Encrypt)</li>
                    <li><span class="check">✓</span>IAM Role — no hardcoded credentials</li>
                    <li><span class="check">✓</span>Least-privilege IAM policy</li>
                    <li><span class="check">✓</span>Secrets in SSM Parameter Store</li>
                    <li><span class="check">✓</span>Security Groups firewall</li>
                    <li><span class="check">✓</span>S3 encryption at rest</li>
                    <li><span class="check">✓</span>CloudWatch monitoring & alerts</li>
                </ul>
            </div>

            <div class="card">
                <h2>Request Info</h2>
                <ul class="feature-list">
                    <li><strong>IP:</strong> {{ client_ip }}</li>
                    <li><strong>Method:</strong> {{ method }}</li>
                    <li><strong>Protocol:</strong> {{ protocol }}</li>
                    <li><strong>User Agent:</strong> {{ user_agent[:40] }}...</li>
                </ul>
            </div>
        </div>
    </div>
</body>
</html>
"""

# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────
@app.route('/')
def index():
    logger.info(f"GET / from {request.remote_addr}")
    return render_template_string(HTML_TEMPLATE,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
        environment=APP_ENV,
        client_ip=request.remote_addr,
        method=request.method,
        protocol=request.scheme,
        user_agent=request.headers.get('User-Agent', 'Unknown')
    )

@app.route('/health')
def health():
    """Health check endpoint — used by monitoring to verify app is alive"""
    logger.info("Health check")
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "environment": APP_ENV
    })

@app.route('/upload', methods=['POST'])
def upload():
    """Secure file upload to S3 using IAM role — no hardcoded credentials"""
    if 'file' not in request.files:
        return jsonify({"error": "No file in request"}), 400

    file = request.files['file']
    bucket = os.environ.get('S3_BUCKET', 'your-secure-app-bucket-uniquename')

    try:
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.upload_fileobj(
            file,
            bucket,
            f"uploads/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}",
            ExtraArgs={'ServerSideEncryption': 'AES256'}
        )
        logger.info(f"File uploaded: {file.filename} from {request.remote_addr}")
        return jsonify({"message": "File uploaded securely to S3"})
    except ClientError as e:
        logger.error(f"S3 upload error: {e}")
        return jsonify({"error": "Upload failed"}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=False)