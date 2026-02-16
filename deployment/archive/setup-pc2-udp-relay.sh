#!/bin/bash
# PC2: TCP (from SSH tunnel) → UDP (to leader robot)
# This script runs on PC2 to relay UDP traffic from the SSH tunnel to the leader

LEADER_IP="192.168.1.2"
TCP_PORT=15000
UDP_PORT=50000

echo "=== PC2 UDP Relay Setup ==="
echo "TCP:${TCP_PORT} → UDP:${UDP_PORT} to leader ${LEADER_IP}"

# Kill old socat processes (if any)
pkill -f "socat.*UDP4-LISTEN:50000" 2>/dev/null || true
pkill -f "socat.*TCP4-LISTEN:15000" 2>/dev/null || true

# Start TCP listener that forwards to leader's UDP port
socat TCP4-LISTEN:${TCP_PORT},reuseaddr,fork UDP4:${LEADER_IP}:${UDP_PORT} &
SOCAT_PID=$!

sleep 1

# Verify it started
if pgrep -f "socat.*TCP4-LISTEN:15000" > /dev/null; then
    echo "✓ PC2 UDP relay running (PID: $SOCAT_PID)"
    echo "  TCP:${TCP_PORT} → Leader UDP:${UDP_PORT}"
else
    echo "✗ Failed to start PC2 UDP relay"
    exit 1
fi
