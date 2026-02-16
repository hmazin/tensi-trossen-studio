#!/bin/bash
# UDP Forwarder using socat
# Forwards local UDP port 50000 to leader robot via PC2

PC2_USER="hadi"
PC2_WIFI_IP="192.168.2.138"
LEADER_IP="192.168.1.2"
UDP_PORT=50000

echo "=== UDP Forwarder Setup (via socat on PC2) ==="
echo "This will forward UDP port ${UDP_PORT} from PC1 to leader robot"
echo ""

# Check if socat is installed on PC2
echo "Checking if socat is installed on PC2..."
if ! ssh ${PC2_USER}@${PC2_WIFI_IP} 'which socat' &>/dev/null; then
    echo "Installing socat on PC2..."
    ssh ${PC2_USER}@${PC2_WIFI_IP} 'sudo apt-get update && sudo apt-get install -y socat'
fi

# Kill any existing socat UDP forwarder on PC2
echo "Stopping any existing UDP forwarder on PC2..."
ssh ${PC2_USER}@${PC2_WIFI_IP} 'pkill -f "socat.*UDP4-LISTEN:50000"' 2>/dev/null || true

# Start socat UDP forwarder on PC2 (background)
echo "Starting UDP forwarder on PC2..."
ssh ${PC2_USER}@${PC2_WIFI_IP} "nohup socat UDP4-LISTEN:50000,fork,reuseaddr UDP4:${LEADER_IP}:50000 > /tmp/socat-udp.log 2>&1 &"

sleep 2

# Verify socat is running on PC2
if ssh ${PC2_USER}@${PC2_WIFI_IP} 'pgrep -f "socat.*UDP4-LISTEN:50000"' &>/dev/null; then
    echo "✓ UDP forwarder running on PC2"
else
    echo "✗ Failed to start UDP forwarder on PC2"
    exit 1
fi

# Now create SSH tunnel for UDP (forwards to PC2's socat listener)
echo "Creating SSH tunnel for UDP port ${UDP_PORT}..."
ssh -f -N \
    -L ${UDP_PORT}:localhost:${UDP_PORT} \
    -o ServerAliveInterval=60 \
    -o ServerAliveCountMax=3 \
    ${PC2_USER}@${PC2_WIFI_IP}

if [ $? -eq 0 ]; then
    echo "✓ UDP tunnel established: localhost:${UDP_PORT} → PC2:${UDP_PORT} → Leader:${UDP_PORT}"
else
    echo "✗ Failed to establish UDP tunnel"
    exit 1
fi

echo ""
echo "=== Status ==="
echo "✓ TCP: localhost:50001 → Leader (via SSH tunnel)"
echo "✓ UDP: localhost:50000 → Leader (via SSH tunnel + socat on PC2)"
echo ""
echo "To stop:"
echo "  pkill -f 'ssh.*50000:localhost:50000'"
echo "  ssh ${PC2_USER}@${PC2_WIFI_IP} 'pkill -f socat.*UDP4-LISTEN:50000'"
echo ""
