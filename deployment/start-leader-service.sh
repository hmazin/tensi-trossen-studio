#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# Start the Leader Service on PC2 (the PC connected to the leader robot)
#
# This script is run ON PC2, either manually or via SSH from PC1.
# It connects to the leader robot locally and streams joint positions
# over TCP so that PC1 can use RemoteLeaderTeleop.
#
# Usage:
#   ./deployment/start-leader-service.sh                # defaults
#   ./deployment/start-leader-service.sh 192.168.1.3    # custom leader IP
#   ./deployment/start-leader-service.sh 192.168.1.3 5555 60  # IP, port, fps
# ──────────────────────────────────────────────────────────────

set -euo pipefail

LEADER_IP="${1:-192.168.1.2}"
PORT="${2:-5555}"
FPS="${3:-60}"
LEROBOT_DIR="${LEROBOT_TROSSEN_PATH:-$HOME/lerobot_trossen}"
LOG_FILE="/tmp/leader_service.log"

echo "=== Leader Service Startup ==="
echo "  Leader IP:    $LEADER_IP"
echo "  Listen port:  $PORT"
echo "  Stream FPS:   $FPS"
echo "  LeRobot dir:  $LEROBOT_DIR"
echo "  Log file:     $LOG_FILE"
echo ""

# Kill any existing leader service
if pgrep -f "leader_service.py" > /dev/null 2>&1; then
    echo "[*] Stopping existing leader service..."
    pkill -f "leader_service.py" || true
    sleep 1
fi

# Check leader robot is reachable
echo "[*] Checking leader connectivity at $LEADER_IP..."
if ! ping -c 1 -W 2 "$LEADER_IP" > /dev/null 2>&1; then
    echo "[ERROR] Cannot ping leader at $LEADER_IP"
    echo "  - Is the leader iNerve powered on?"
    echo "  - Is it connected through the NetGear switch?"
    exit 1
fi
echo "  Leader is reachable."

# Check TCP port
if nc -zw2 "$LEADER_IP" 50001 2>/dev/null; then
    echo "  TCP:50001 is open."
else
    echo "[WARNING] TCP:50001 not responding - leader may not be ready"
fi

cd "$LEROBOT_DIR"

echo ""
echo "[*] Starting leader service (logging to $LOG_FILE)..."
echo "    To follow logs: tail -f $LOG_FILE"
echo ""

# Run with nohup so it survives SSH disconnection
nohup uv run python -u leader_service.py \
    --ip "$LEADER_IP" \
    --port "$PORT" \
    --fps "$FPS" \
    > "$LOG_FILE" 2>&1 &

SERVICE_PID=$!
echo "[*] Leader service started (PID: $SERVICE_PID)"

# Wait a moment and verify it's still running
sleep 2
if kill -0 "$SERVICE_PID" 2>/dev/null; then
    echo "[OK] Service is running."
    echo ""
    echo "=== Ready ==="
    echo "  Clients can connect to $(hostname -I | awk '{print $1}'):$PORT"
    echo "  Stop with: pkill -f leader_service.py"
else
    echo "[ERROR] Service exited immediately. Check $LOG_FILE:"
    tail -20 "$LOG_FILE"
    exit 1
fi
