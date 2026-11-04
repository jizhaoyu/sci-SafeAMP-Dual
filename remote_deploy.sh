#!/usr/bin/env bash
# ==============================================================================
# DTI Remote Deployment & Hot-Reload Script
# Target: Ubuntu 22.04/24.04 LTS (Tencent Cloud VM)
# ==============================================================================

set -euo pipefail

SERVER_DIR="/home/ubuntu/dti-server"
BACKUP_DIR="/home/ubuntu/backups/deploy_$(date +%Y%m%d_%H%M%S)"
ENV_PYTHON="/home/ubuntu/dti-env/bin/python3"

echo "=== [1/6] Initializing Deployment & Backup ==="
mkdir -p "${BACKUP_DIR}"
if [ -d "${SERVER_DIR}" ]; then
    cp -r "${SERVER_DIR}/app.py" "${BACKUP_DIR}/" 2>/dev/null || true
    if [ -f "/etc/nginx/sites-available/dti.conf" ]; then
        cp "/etc/nginx/sites-available/dti.conf" "${BACKUP_DIR}/dti.conf"
    fi
    echo "Backup successfully saved to: ${BACKUP_DIR}"
fi

echo "=== [2/6] Installing Rate Limiter & Backend Updates ==="
if [ -f "/tmp/dti_deploy/rate_limiter.py" ]; then
    cp "/tmp/dti_deploy/rate_limiter.py" "${SERVER_DIR}/rate_limiter.py"
    chmod 644 "${SERVER_DIR}/rate_limiter.py"
    chown ubuntu:ubuntu "${SERVER_DIR}/rate_limiter.py"
    echo "Installed rate_limiter.py"
fi

if [ -f "/tmp/dti_deploy/patch_remote_app.py" ]; then
    python3 "/tmp/dti_deploy/patch_remote_app.py" "${SERVER_DIR}/app.py"
    chmod 644 "${SERVER_DIR}/app.py"
    chown ubuntu:ubuntu "${SERVER_DIR}/app.py"
fi

echo "=== [3/6] Deploying Hardened Nginx Configuration ==="
if [ -f "/tmp/dti_deploy/dti.conf" ]; then
    sudo cp "/tmp/dti_deploy/dti.conf" "/etc/nginx/sites-available/dti.conf"
    sudo ln -sf "/etc/nginx/sites-available/dti.conf" "/etc/nginx/sites-enabled/dti.conf"
    echo "Testing Nginx configuration..."
    sudo nginx -t
    echo "Reloading Nginx service..."
    sudo systemctl reload nginx
    echo "Nginx successfully reloaded with rate-limiting, gzip, and security headers."
fi

echo "=== [4/6] Updating Frontend Dist Build ==="
if [ -d "/tmp/dti_deploy/dist" ]; then
    mkdir -p "${SERVER_DIR}/frontend/dist"
    cp -r /tmp/dti_deploy/dist/* "${SERVER_DIR}/frontend/dist/"
    chown -R ubuntu:ubuntu "${SERVER_DIR}/frontend"
    echo "Frontend SPA distribution refreshed."
fi

echo "=== [5/6] Restarting DTI Systemd Service ==="
sudo systemctl daemon-reload
sudo systemctl restart dti

echo "Waiting for service initialization and ESM model loading (up to 25s)..."
for i in $(seq 1 12); do
    if curl -s -m 2 http://127.0.0.1:8090/api/health | grep -q '"status":"ok"'; then
        echo "Backend service is ready and serving healthy responses after ${i} attempts!"
        break
    fi
    sleep 2
done

echo "=== [6/6] Verifying Service Health & Observability ==="
if systemctl is-active --quiet dti; then
    echo "[SUCCESS] dti.service is ACTIVE (running)!"
else
    echo "[ERROR] dti.service failed to start! Dumping logs:"
    sudo journalctl -u dti -n 30 --no-pager
    exit 1
fi

echo "Probing local backend /api/health..."
HEALTH_RESP=$(curl -s -m 5 http://127.0.0.1:8090/api/health || echo "FAILED")
echo "Local Health Probe: ${HEALTH_RESP}"

echo "Probing local backend /api/metrics..."
METRICS_RESP=$(curl -s -m 5 http://127.0.0.1:8090/api/metrics || echo "FAILED")
echo "Local Metrics Probe: ${METRICS_RESP}"

echo "Probing public HTTP Nginx endpoint /api/health..."
PUBLIC_RESP=$(curl -s -m 5 http://127.0.0.1/api/health || echo "FAILED")
echo "Public Nginx Probe: ${PUBLIC_RESP}"

echo "=== DTI Remote Deployment Finished Successfully! ==="
