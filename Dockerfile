# Use an official, minimal base image — not "latest" (unpredictable)
FROM python:3.11-slim

# Metadata
LABEL maintainer="Ayush Patel"
LABEL description="Secure Flask web application"

# Create a non-root user to run the app
# Running as root inside a container is dangerous —
# if someone escapes the container, they'd be root on the host
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

# Set working directory
WORKDIR /app

# Copy dependency file first (layer caching optimization)
# Docker builds images in layers. If requirements.txt doesn't change,
# Docker reuses the cached pip install layer — much faster rebuilds
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Create log directory
RUN mkdir -p /var/log/secure-app && \
    chown appuser:appgroup /var/log/secure-app

# Switch to non-root user
USER appuser

# Document which port the app uses (doesn't actually expose it)
EXPOSE 8000

# Health check — Docker will run this to verify the container is healthy
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run gunicorn
CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:8000", \
     "--access-logfile", "/var/log/secure-app/access.log", \
     "--error-logfile", "/var/log/secure-app/error.log", \
     "app:app"]