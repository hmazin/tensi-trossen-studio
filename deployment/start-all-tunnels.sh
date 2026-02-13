#!/bin/bash
# Complete startup sequence for distributed teleoperation with UDP support

set -e

PC2_USER="hadi"
PC2_WIFI_IP="192.168.2.138"

echo "=== Starting Distributed Teleoperation Setup ==="
echo ""

# Step 1: Set up PC2 UDP relay
echo "Step 1: Setting up UDP relay on PC2..."
ssh ${PC2_USER}@${PC2_WIFI_IP} 'bash -s' < deployment/setup-pc2-udp-relay.sh
sleep 1

# Step 2: Create SSH tunnels
echo ""
echo "Step 2: Creating SSH tunnels..."
./deployment/ssh-tunnel-complete.sh
sleep 1

# Step 3: Set up PC1 UDP wrapper
echo ""
echo "Step 3: Setting up UDP wrapper on PC1..."
./deployment/setup-pc1-udp-wrapper.sh
sleep 1

# Step 4: Verify everything
echo ""
echo "=== Verification ==="
echo ""

echo "PC2 socat (TCP→UDP relay):"
ssh ${PC2_USER}@${PC2_WIFI_IP} 'pgrep -af socat' || echo "⚠ Not running"

echo ""
echo "PC1 socat (UDP→TCP wrapper):"
pgrep -af socat | grep "UDP4-LISTEN:50000" || echo "⚠ Not running"

echo ""
echo "SSH tunnels:"
ps aux | grep -E 'ssh.*(50001|15000)' | grep -v grep || echo "⚠ Not running"

echo ""
echo "Port tests:"
echo -n "  TCP 50001 (robot control): "
nc -zv localhost 50001 2>&1 | grep -q succeeded && echo "✓" || echo "✗"
echo -n "  TCP 15000 (UDP relay): "
nc -zv localhost 15000 2>&1 | grep -q succeeded && echo "✓" || echo "✗"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Network path:"
echo "  lerobot → UDP:50000 → socat(PC1) → TCP:15000 → SSH → PC2:15000 → socat(PC2) → Leader UDP:50000"
echo ""
echo "Configuration:"
echo "  leader_ip: 127.0.0.1 (tunneled to 192.168.1.2 via PC2)"
echo "  follower_ip: 192.168.1.5 (direct Ethernet)"
echo ""
echo "Ready for teleoperation!"
echo ""
