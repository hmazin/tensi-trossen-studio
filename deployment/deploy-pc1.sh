#!/bin/bash
# Deployment script for PC1 (Leader Side - with leader robot and web UI)

set -e

echo "=== TENSI Trossen Studio - PC1 Deployment (Leader Side) ==="
echo ""

# Configuration
BACKEND_SERVICE_NAME="tensi-backend"
BACKEND_SERVICE_FILE="tensi-backend.service"
BACKEND_DIR="/home/tensi/tensi-trossen-studio/backend"
FRONTEND_DIR="/home/tensi/tensi-trossen-studio/frontend"
DEPLOYMENT_DIR="/home/tensi/tensi-trossen-studio/deployment"

# Get PC2 IP from user
read -p "Enter PC2 (Follower) IP address [192.168.1.5]: " PC2_IP
PC2_IP=${PC2_IP:-192.168.1.5}
CAMERA_SERVICE_URL="http://${PC2_IP}:8001"

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
  echo "This script must be run with sudo for systemd operations"
  echo "Usage: sudo ./deploy-pc1.sh"
  exit 1
fi

echo "Configuration:"
echo "  PC2 IP: $PC2_IP"
echo "  Camera Service URL: $CAMERA_SERVICE_URL"
echo ""

echo "Step 1: Installing backend dependencies..."
cd "$BACKEND_DIR"
sudo -u tensi uv sync
echo "✓ Backend dependencies installed"
echo ""

echo "Step 2: Installing frontend dependencies..."
cd "$FRONTEND_DIR"
sudo -u tensi npm install
echo "✓ Frontend dependencies installed"
echo ""

echo "Step 3: Building frontend for production..."
sudo -u tensi VITE_API_BASE=http://localhost:8000/api VITE_CAMERA_API_BASE=${CAMERA_SERVICE_URL}/api npm run build
echo "✓ Frontend built"
echo ""

echo "Step 4: Testing backend service..."
timeout 5s sudo -u tensi CAMERA_SERVICE_URL="$CAMERA_SERVICE_URL" uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 || true
echo "✓ Backend can start"
echo ""

echo "Step 5: Installing systemd service..."
# Update service file with correct CAMERA_SERVICE_URL
sed "s|Environment=\"CAMERA_SERVICE_URL=.*\"|Environment=\"CAMERA_SERVICE_URL=$CAMERA_SERVICE_URL\"|" \
    "$DEPLOYMENT_DIR/$BACKEND_SERVICE_FILE" > /etc/systemd/system/"$BACKEND_SERVICE_NAME.service"
systemctl daemon-reload
echo "✓ Service file installed"
echo ""

echo "Step 6: Starting and enabling backend service..."
systemctl enable "$BACKEND_SERVICE_NAME.service"
systemctl start "$BACKEND_SERVICE_NAME.service"
echo "✓ Backend service started and enabled"
echo ""

echo "Step 7: Checking backend service status..."
systemctl status "$BACKEND_SERVICE_NAME.service" --no-pager || true
echo ""

echo "Step 8: Serving frontend..."
echo "Starting frontend in background (use systemd or screen for production)..."
cd "$FRONTEND_DIR"
sudo -u tensi nohup npm run preview -- --host 0.0.0.0 --port 5173 > /tmp/tensi-frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✓ Frontend started (PID: $FRONTEND_PID)"
echo ""

echo "Step 9: Verifying services..."
sleep 3
if curl -s http://localhost:8000/health | grep -q "ok"; then
    echo "✓ Backend is responding"
else
    echo "⚠ Backend health check failed. Check logs with: journalctl -u $BACKEND_SERVICE_NAME -f"
fi
echo ""

echo "=== Deployment Complete ==="
echo ""
echo "Access the application:"
echo "  Web UI: http://$(hostname -I | awk '{print $1}'):5173"
echo "  Backend API: http://$(hostname -I | awk '{print $1}'):8000/docs"
echo ""
echo "Useful commands:"
echo "  Check backend logs: journalctl -u $BACKEND_SERVICE_NAME -f"
echo "  Check frontend logs: tail -f /tmp/tensi-frontend.log"
echo "  Test camera connection: curl ${CAMERA_SERVICE_URL}/health"
echo ""
echo "NOTE: For production, set up a systemd service for the frontend as well."
echo ""
