#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# Start the Leader Service on PC2, remotely from PC1
#
# Run this on PC1. It SSHes into PC2 and starts leader_service.py.
# After this, PC1's teleoperate command will use RemoteLeaderTeleop
# to connect to PC2:5555 and receive joint positions.
#
# Usage:
#   ./deployment/start-remote-leader.sh
# ──────────────────────────────────────────────────────────────

set -euo pipefail

# ── Configuration ──
PC2_USER="${PC2_USER:-hadi}"
PC2_WIFI_IP="${PC2_WIFI_IP:-192.168.2.138}"
LEADER_IP="${LEADER_IP:-192.168.1.2}"
LEADER_PORT="${LEADER_PORT:-5555}"
FPS="${FPS:-60}"
LEROBOT_DIR_ON_PC2="${LEROBOT_DIR_ON_PC2:-/home/$PC2_USER/lerobot_trossen}"

echo "╔══════════════════════════════════════════════════╗"
echo "║       Remote Leader Service Launcher             ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "  PC2:         $PC2_USER@$PC2_WIFI_IP"
echo "  Leader IP:   $LEADER_IP (on PC2's Ethernet)"
echo "  Service port: $LEADER_PORT"
echo "  Stream FPS:  $FPS"
echo ""

# Step 1: Check PC2 is reachable
echo "[1/4] Checking PC2 connectivity..."
if ! ping -c 1 -W 2 "$PC2_WIFI_IP" > /dev/null 2>&1; then
    echo "[ERROR] Cannot reach PC2 at $PC2_WIFI_IP"
    echo "  - Is PC2 powered on and on the WiFi network?"
    exit 1
fi
echo "  PC2 is reachable via WiFi."

# Step 2: Check SSH
echo "[2/4] Testing SSH access..."
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "$PC2_USER@$PC2_WIFI_IP" 'echo ok' > /dev/null 2>&1; then
    echo "[ERROR] SSH to $PC2_USER@$PC2_WIFI_IP failed"
    echo "  - Have you set up SSH keys? Run: ssh-copy-id $PC2_USER@$PC2_WIFI_IP"
    exit 1
fi
echo "  SSH access confirmed."

# Step 3: Kill any existing leader service on PC2
echo "[3/4] Stopping any existing leader service on PC2..."
ssh "$PC2_USER@$PC2_WIFI_IP" 'pkill -f leader_service.py 2>/dev/null || true'
sleep 1

# Step 4: Start the leader service on PC2
echo "[4/4] Starting leader service on PC2..."
ssh "$PC2_USER@$PC2_WIFI_IP" bash -s <<REMOTE_SCRIPT
set -euo pipefail

# Verify leader is reachable from PC2
if ! ping -c 1 -W 2 "$LEADER_IP" > /dev/null 2>&1; then
    echo "[ERROR] PC2 cannot reach leader at $LEADER_IP"
    echo "  - Is the leader iNerve powered on with green LED?"
    echo "  - Is it connected through the NetGear switch?"
    exit 1
fi

echo "  Leader reachable from PC2. Starting service..."
nohup python3 -u ~/leader_service.py \\
    --ip "$LEADER_IP" \\
    --port "$LEADER_PORT" \\
    --fps "$FPS" \\
    > /tmp/leader_service.log 2>&1 &

sleep 2
if pgrep -f "leader_service.py" > /dev/null; then
    echo "  Leader service running (PID: \$(pgrep -f leader_service.py))"
else
    echo "[ERROR] Leader service failed to start. Logs:"
    tail -20 /tmp/leader_service.log
    exit 1
fi
REMOTE_SCRIPT

echo ""

# Verify service is accessible from PC1
echo "[*] Verifying leader service is accessible from PC1..."
sleep 1
if nc -zw3 "$PC2_WIFI_IP" "$LEADER_PORT" 2>/dev/null; then
    echo "  Leader service is accessible at $PC2_WIFI_IP:$LEADER_PORT"
else
    echo "[WARNING] Cannot connect to $PC2_WIFI_IP:$LEADER_PORT yet"
    echo "  The service may still be configuring. Check PC2 logs:"
    echo "    ssh $PC2_USER@$PC2_WIFI_IP 'tail -f /tmp/leader_service.log'"
fi

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  Leader service is running on PC2!               ║"
echo "║                                                  ║"
echo "║  You can now start teleoperation from the UI.    ║"
echo "║                                                  ║"
echo "║  Monitor logs:                                   ║"
echo "║    ssh $PC2_USER@$PC2_WIFI_IP 'tail -f /tmp/leader_service.log'"
echo "║                                                  ║"
echo "║  Stop service:                                   ║"
echo "║    ssh $PC2_USER@$PC2_WIFI_IP 'pkill -f leader_service.py'"
echo "╚══════════════════════════════════════════════════╝"
