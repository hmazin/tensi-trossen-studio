#!/bin/bash
# SSH Tunnel Script for Leader Robot Access
# Tunnels leader robot (192.168.1.2) from PC2 to localhost on PC1

# Configuration
PC2_USER="hadi"
PC2_WIFI_IP="192.168.2.138"
LEADER_IP="192.168.1.2"
TCP_PORT=50001
UDP_PORT=50000

echo "=== Leader Robot SSH Tunnel Setup ==="
echo "Tunneling leader robot from PC2 to PC1..."
echo "PC2: ${PC2_WIFI_IP}"
echo "Leader robot on PC2 network: ${LEADER_IP}"
echo "Ports: TCP ${TCP_PORT}, UDP ${UDP_PORT}"
echo ""

# Create SSH tunnel for TCP port
# -L local_port:destination_host:destination_port
# -N: No remote command
# -f: Background mode
# -o ServerAliveInterval: Keep connection alive
ssh -f -N \
    -L ${TCP_PORT}:${LEADER_IP}:${TCP_PORT} \
    -o ServerAliveInterval=60 \
    -o ServerAliveCountMax=3 \
    ${PC2_USER}@${PC2_WIFI_IP}

if [ $? -eq 0 ]; then
    echo "✓ TCP tunnel established: localhost:${TCP_PORT} -> ${LEADER_IP}:${TCP_PORT}"
else
    echo "✗ Failed to establish TCP tunnel"
    exit 1
fi

# Note: UDP tunneling through SSH is not directly supported
# We'll document this limitation

echo ""
echo "=== Tunnel Status ==="
echo "Leader robot TCP port ${TCP_PORT} is now accessible at localhost:${TCP_PORT}"
echo ""
echo "⚠ Note: UDP port ${UDP_PORT} cannot be tunneled through SSH"
echo "   The Trossen driver should work with TCP only for remote control"
echo ""
echo "To stop the tunnel:"
echo "  ps aux | grep 'ssh.*${TCP_PORT}:${LEADER_IP}'"
echo "  kill <PID>"
echo ""
echo "To verify tunnel is working:"
echo "  nc -zv localhost ${TCP_PORT}"
echo ""
