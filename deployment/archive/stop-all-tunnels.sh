#!/bin/bash
# Stop all tunnels and socat processes

PC2_USER="hadi"
PC2_WIFI_IP="192.168.2.138"

echo "=== Stopping All Tunnels ==="

# Stop PC1 socat
echo "Stopping PC1 socat..."
pkill -f "socat.*UDP4-LISTEN:50000" && echo "✓ Stopped" || echo "Not running"

# Stop SSH tunnels
echo "Stopping SSH tunnels..."
pkill -f "ssh.*50001:192.168.1.2" && echo "✓ Stopped TCP tunnel" || echo "Not running"
pkill -f "ssh.*15000:localhost:15000" && echo "✓ Stopped UDP relay tunnel" || echo "Not running"

# Stop PC2 socat
echo "Stopping PC2 socat..."
ssh ${PC2_USER}@${PC2_WIFI_IP} 'pkill -f "socat.*TCP4-LISTEN:15000"' && echo "✓ Stopped" || echo "Not running"

echo ""
echo "✓ All tunnels and relays stopped"
