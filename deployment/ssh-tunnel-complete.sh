#!/bin/bash
# Complete tunnel setup: TCP + UDP (via TCP wrapper)

PC2_USER="hadi"
PC2_WIFI_IP="192.168.2.138"
LEADER_IP="192.168.1.2"

echo "=== Complete Tunnel Setup (TCP + UDP) ==="

# 1. TCP tunnel for robot control (direct to leader)
if ! pgrep -f "ssh.*50001:${LEADER_IP}:50001" > /dev/null; then
    echo "Creating TCP tunnel for port 50001..."
    ssh -f -N -L 50001:${LEADER_IP}:50001 \
        -o ServerAliveInterval=60 \
        -o ServerAliveCountMax=3 \
        ${PC2_USER}@${PC2_WIFI_IP}
    echo "✓ TCP tunnel created"
else
    echo "✓ TCP tunnel already running"
fi

# 2. TCP tunnel for UDP wrapper (intermediate port 15000)
if ! pgrep -f "ssh.*15000:localhost:15000" > /dev/null; then
    echo "Creating TCP tunnel for UDP relay (port 15000)..."
    ssh -f -N -L 15000:localhost:15000 \
        -o ServerAliveInterval=60 \
        -o ServerAliveCountMax=3 \
        ${PC2_USER}@${PC2_WIFI_IP}
    echo "✓ UDP relay tunnel created"
else
    echo "✓ UDP relay tunnel already running"
fi

echo ""
echo "✓ TCP tunnel: localhost:50001 → Leader (direct)"
echo "✓ UDP tunnel: localhost:50000 → TCP:15000 → PC2 → Leader UDP"
echo ""
echo "Active SSH tunnels:"
ps aux | grep -E 'ssh.*(50001|15000)' | grep -v grep | awk '{print "  PID " $2 ": " $11 " " $12 " " $13}'
