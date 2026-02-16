#!/bin/bash
# Debug script to check tunnel and port status

echo "=== SSH Tunnel and Port Status Debug ==="
echo ""

# Check SSH tunnel process
echo "1. SSH Tunnel Process:"
ps aux | grep 'ssh.*50001:192.168.1.2' | grep -v grep
echo ""

# Check if TCP port 50001 is listening locally
echo "2. TCP Port 50001 (should be LISTEN):"
sudo lsof -i :50001 | grep LISTEN || echo "Not listening"
echo ""

# Check if UDP port 50000 is listening locally  
echo "3. UDP Port 50000 (should NOT be listening - not tunneled):"
sudo lsof -i :50000 | grep UDP || echo "Not listening"
echo ""

# Test TCP connectivity
echo "4. Test TCP connection to localhost:50001:"
nc -zv localhost 50001 2>&1
echo ""

# Test UDP connectivity (will fail)
echo "5. Test UDP connection to localhost:50000 (expected to fail):"
nc -zvu localhost 50000 2>&1 | head -3
echo ""

# Check from PC2 if UDP port is open on leader
echo "6. Check if leader robot UDP port is accessible from PC2:"
ssh hadi@192.168.2.138 'nc -zvu 192.168.1.2 50000 2>&1' | head -3
echo ""

echo "=== Analysis ==="
echo "SSH can only tunnel TCP, not UDP"
echo "UDP port 50000 needs alternative solution:"
echo "  Option 1: Use socat for UDP forwarding"
echo "  Option 2: Configure robot to work without UDP"
echo "  Option 3: Use VPN for transparent UDP access"
echo ""
