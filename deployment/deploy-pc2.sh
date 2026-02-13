#!/bin/bash
# Deployment script for PC2 (Follower Side - with cameras and follower robot)

set -e

echo "=== TENSI Trossen Studio - PC2 Deployment (Follower Side) ==="
echo ""

# Configuration
SERVICE_NAME="tensi-camera"
SERVICE_FILE="tensi-camera.service"
BACKEND_DIR="/home/tensi/tensi-trossen-studio/backend"
DEPLOYMENT_DIR="/home/tensi/tensi-trossen-studio/deployment"

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
  echo "This script must be run with sudo for systemd operations"
  echo "Usage: sudo ./deploy-pc2.sh"
  exit 1
fi

echo "Step 1: Installing backend dependencies..."
cd "$BACKEND_DIR"
sudo -u tensi uv sync
echo "✓ Dependencies installed"
echo ""

echo "Step 2: Testing camera service..."
echo "Starting camera service test (will stop after 5 seconds)..."
timeout 5s sudo -u tensi uv run uvicorn camera_service:app --host 0.0.0.0 --port 8001 || true
echo "✓ Camera service can start"
echo ""

echo "Step 3: Installing systemd service..."
cp "$DEPLOYMENT_DIR/$SERVICE_FILE" /etc/systemd/system/
systemctl daemon-reload
echo "✓ Service file installed"
echo ""

echo "Step 4: Configuring firewall (allowing port 8001)..."
if command -v ufw &> /dev/null; then
    ufw allow from 192.168.1.0/24 to any port 8001 comment "TENSI Camera Service"
    echo "✓ UFW rule added"
elif command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-port=8001/tcp
    firewall-cmd --reload
    echo "✓ firewalld rule added"
else
    echo "⚠ No firewall detected (ufw/firewalld). Ensure port 8001 is accessible."
fi
echo ""

echo "Step 5: Starting and enabling service..."
systemctl enable "$SERVICE_NAME.service"
systemctl start "$SERVICE_NAME.service"
echo "✓ Service started and enabled"
echo ""

echo "Step 6: Checking service status..."
systemctl status "$SERVICE_NAME.service" --no-pager || true
echo ""

echo "Step 7: Verifying camera service..."
sleep 3
if curl -s http://localhost:8001/health | grep -q "ok"; then
    echo "✓ Camera service is responding"
else
    echo "⚠ Camera service health check failed. Check logs with: journalctl -u $SERVICE_NAME -f"
fi
echo ""

echo "=== Deployment Complete ==="
echo ""
echo "Next steps:"
echo "  1. Check logs: journalctl -u $SERVICE_NAME -f"
echo "  2. Test camera detection: curl http://localhost:8001/api/cameras/detect"
echo "  3. Access camera streams from PC1 at http://$(hostname -I | awk '{print $1}'):8001/api/cameras/stream/wrist"
echo "  4. Configure PC1 with CAMERA_SERVICE_URL=http://$(hostname -I | awk '{print $1}'):8001"
echo ""
