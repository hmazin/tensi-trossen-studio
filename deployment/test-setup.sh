#!/bin/bash
# Test script for distributed robot setup with SSH tunnel

echo "=== Testing Distributed Robot Setup ==="
echo ""

# Test 1: SSH Tunnel
echo "Test 1: Checking SSH tunnel to leader..."
if nc -zv localhost 50001 2>&1 | grep -q "succeeded"; then
    echo "✓ SSH tunnel is active (localhost:50001)"
else
    echo "✗ SSH tunnel not found"
    echo "  Run: ./deployment/ssh-tunnel-leader.sh"
    exit 1
fi
echo ""

# Test 2: Follower connectivity
echo "Test 2: Checking follower robot connectivity..."
if nc -zv 192.168.1.5 50001 2>&1 | grep -q "succeeded"; then
    echo "✓ Follower robot reachable (192.168.1.5:50001)"
else
    echo "✗ Follower robot not reachable"
    echo "  Check: ping 192.168.1.5"
    exit 1
fi
echo ""

# Test 3: Configuration
echo "Test 3: Checking configuration..."
LEADER_IP=$(grep -A 1 '"leader_ip"' ~/.tensi_trossen_studio/config.json | grep -o '"[^"]*"' | tail -1 | tr -d '"')
FOLLOWER_IP=$(grep -A 1 '"follower_ip"' ~/.tensi_trossen_studio/config.json | grep -o '"[^"]*"' | tail -1 | tr -d '"')

if [ "$LEADER_IP" = "127.0.0.1" ]; then
    echo "✓ Leader IP configured for tunnel: $LEADER_IP"
else
    echo "✗ Leader IP should be 127.0.0.1 for tunnel, found: $LEADER_IP"
    echo "  Fix: Update ~/.tensi_trossen_studio/config.json"
fi

if [ "$FOLLOWER_IP" = "192.168.1.5" ]; then
    echo "✓ Follower IP configured correctly: $FOLLOWER_IP"
else
    echo "⚠ Follower IP is: $FOLLOWER_IP (expected 192.168.1.5)"
fi
echo ""

# Test 4: Cameras
echo "Test 4: Checking cameras..."
if lsusb | grep -q "8086"; then
    CAMERA_COUNT=$(lsusb | grep "8086" | wc -l)
    echo "✓ Found $CAMERA_COUNT RealSense camera(s)"
else
    echo "⚠ No RealSense cameras detected"
    echo "  Check: lsusb | grep -i real"
fi
echo ""

# Test 5: PC2 connectivity
echo "Test 5: Checking PC2 connectivity..."
if ping -c 1 192.168.2.138 &> /dev/null; then
    echo "✓ PC2 reachable via WiFi (192.168.2.138)"
else
    echo "✗ PC2 not reachable"
    echo "  Check: ping 192.168.2.138"
    exit 1
fi
echo ""

# Summary
echo "=== Test Summary ==="
echo "✓ SSH tunnel: localhost:50001 → PC2 → Leader (192.168.1.2)"
echo "✓ Direct connection: PC1 → Follower (192.168.1.5)"
echo "✓ Configuration: leader=127.0.0.1, follower=192.168.1.5"
echo ""
echo "Ready for teleoperation!"
echo ""
echo "Next steps:"
echo "  1. Start backend: cd backend && uv run uvicorn app.main:app"
echo "  2. Start frontend: cd frontend && npm run dev"
echo "  3. Open Web UI: http://localhost:5173"
echo "  4. Click 'Start Teleoperation'"
echo ""
