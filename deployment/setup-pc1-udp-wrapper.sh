#!/bin/bash
# PC1: UDP (from lerobot) → TCP (to SSH tunnel)
# This converts incoming UDP from lerobot to TCP for SSH tunneling

TCP_PORT=15000
UDP_PORT=50000

echo "=== PC1 UDP Wrapper Setup ==="
echo "UDP:${UDP_PORT} → TCP:${TCP_PORT} (for SSH tunnel)"

# Kill old socat processes (if any)
pkill -f "socat.*UDP4-LISTEN:50000" 2>/dev/null || true

# Check if socat is installed
if ! which socat > /dev/null 2>&1; then
    echo "✗ socat not installed on PC1"
    echo "  Install with: sudo apt-get install -y socat"
    exit 1
fi

# Start UDP listener that converts to TCP
socat UDP4-LISTEN:${UDP_PORT},reuseaddr,fork TCP4:localhost:${TCP_PORT} &
SOCAT_PID=$!

sleep 1

# Verify it started
if pgrep -f "socat.*UDP4-LISTEN:50000" > /dev/null; then
    echo "✓ PC1 UDP wrapper running (PID: $SOCAT_PID)"
    echo "  UDP:${UDP_PORT} → TCP:${TCP_PORT}"
else
    echo "✗ Failed to start PC1 UDP wrapper"
    exit 1
fi
