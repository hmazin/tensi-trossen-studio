# UDP Port Forwarding Solution for Leader Robot

## Problem

The leader robot requires both TCP (port 50001) and UDP (port 50000). SSH tunnels can only forward TCP, not UDP.

**Current status:**
- ✅ TCP port 50001: Working via SSH tunnel
- ❌ UDP port 50000: NOT forwarded (causing connection refused error)

## Solution: UDP Forwarding with socat on PC2

We need to run `socat` on PC2 to relay UDP traffic from the WiFi network to the leader robot's Ethernet network.

### Setup Instructions

**On PC2 (via terminal or SSH), run these commands:**

```bash
# Install socat (if not already installed)
sudo apt-get update && sudo apt-get install -y socat

# Start UDP forwarder
# This listens on WiFi IP (192.168.2.138:50000) and forwards to leader (192.168.1.2:50000)
nohup socat UDP4-LISTEN:50000,fork,reuseaddr,bind=192.168.2.138 UDP4:192.168.1.2:50000 > /tmp/socat-udp.log 2>&1 &

# Verify it's running
pgrep -af socat
```

**Then on PC1, create SSH tunnel for UDP:**

```bash
# This tunnels PC1's localhost:50000 to PC2's 192.168.2.138:50000 (where socat is listening)
ssh -f -N -L 50000:192.168.2.138:50000 hadi@192.168.2.138

# Verify tunnel
nc -zvu localhost 50000
```

### Architecture

```
PC1 (localhost:50000)
  ↓ SSH tunnel
PC2 (192.168.2.138:50000 - socat listening)
  ↓ socat forwards
Leader Robot (192.168.1.2:50000 - Ethernet)
```

### Complete Setup Script

Run this on PC1 after socat is running on PC2:

```bash
#!/bin/bash
# Complete tunnel setup (TCP + UDP)

PC2_USER="hadi"
PC2_WIFI_IP="192.168.2.138"

echo "=== Setting up TCP and UDP tunnels ==="

# TCP tunnel (already running, but ensure it)
if ! pgrep -f "ssh.*50001:192.168.1.2" > /dev/null; then
    echo "Creating TCP tunnel..."
    ssh -f -N -L 50001:192.168.1.2:50001 ${PC2_USER}@${PC2_WIFI_IP}
fi

# UDP tunnel (to PC2's socat listener)
if ! pgrep -f "ssh.*50000:${PC2_WIFI_IP}" > /dev/null; then
    echo "Creating UDP tunnel..."
    ssh -f -N -L 50000:${PC2_WIFI_IP}:50000 ${PC2_USER}@${PC2_WIFI_IP}
fi

echo "✓ TCP tunnel: localhost:50001 → Leader"
echo "✓ UDP tunnel: localhost:50000 → PC2 socat → Leader"
```

### Testing

```bash
# Test TCP
nc -zv localhost 50001

# Test UDP
nc -zvu localhost 50000

# Both should succeed
```

### Stopping

**On PC1:**
```bash
pkill -f "ssh.*50001:192.168.1.2"
pkill -f "ssh.*50000:192.168.2.138"
```

**On PC2:**
```bash
pkill -f "socat.*UDP4-LISTEN:50000"
```

### Making it Permanent (Optional)

**On PC2** - Create systemd service:

```bash
sudo nano /etc/systemd/system/socat-leader-udp.service
```

```ini
[Unit]
Description=Socat UDP Forwarder for Leader Robot
After=network.target

[Service]
Type=simple
User=hadi
ExecStart=/usr/bin/socat UDP4-LISTEN:50000,fork,reuseaddr,bind=192.168.2.138 UDP4:192.168.1.2:50000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable socat-leader-udp
sudo systemctl start socat-leader-udp
```

## Alternative: Network Bridge (More Complex)

If you want to avoid socat, you could bridge the two Ethernet networks using PC2 as a router, but this requires more network configuration.

## Quick Start Checklist

- [ ] Install socat on PC2: `sudo apt-get install socat`
- [ ] Start socat on PC2: `socat UDP4-LISTEN:50000,fork,reuseaddr,bind=192.168.2.138 UDP4:192.168.1.2:50000 &`
- [ ] Create UDP SSH tunnel on PC1: `ssh -f -N -L 50000:192.168.2.138:50000 hadi@192.168.2.138`
- [ ] Test UDP: `nc -zvu localhost 50000`
- [ ] Start teleoperation from Web UI
