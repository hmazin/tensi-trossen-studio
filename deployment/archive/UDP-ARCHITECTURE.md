# UDP-over-SSH Architecture Documentation

## Problem Solved

SSH cannot tunnel UDP directly. The Trossen leader robot requires both TCP (port 50001) and UDP (port 50000) for proper operation.

## Solution Architecture

### Complete Data Flow

```
lerobot-teleoperate (PC1)
  │
  ├─ TCP to localhost:50001
  │   └─→ SSH tunnel (50001:192.168.1.2:50001)
  │       └─→ PC2 WiFi (192.168.2.138)
  │           └─→ PC2 Ethernet → Leader 192.168.1.2:50001 ✓
  │
  └─ UDP to localhost:50000
      └─→ socat PC1 (UDP→TCP converter)
          └─→ TCP to localhost:15000
              └─→ SSH tunnel (15000:localhost:15000)
                  └─→ PC2:15000 (TCP over WiFi)
                      └─→ socat PC2 (TCP→UDP converter)
                          └─→ UDP to 192.168.1.2:50000 ✓
```

### Component Diagram

```
┌─────────────────────────────────────────┐
│              PC1 (192.168.2.140)         │
│  ┌─────────────────────────────────┐    │
│  │ lerobot-teleoperate             │    │
│  └────────┬────────────┬───────────┘    │
│           │ TCP:50001  │ UDP:50000      │
│           │            │                 │
│  ┌────────▼────────┐  │                 │
│  │ SSH Tunnel      │  │                 │
│  │ 50001→PC2→      │  │                 │
│  │ Leader:50001    │  │                 │
│  └─────────────────┘  │                 │
│                       │                 │
│  ┌────────────────────▼───────────┐    │
│  │ socat (UDP→TCP)                │    │
│  │ UDP:50000 → TCP:localhost:15000│    │
│  └────────────────┬───────────────┘    │
│                   │ TCP:15000          │
│  ┌────────────────▼───────────────┐    │
│  │ SSH Tunnel                     │    │
│  │ 15000→PC2:15000                │    │
│  └────────────────────────────────┘    │
└──────────────────│──────────────────────┘
                   │ WiFi (192.168.2.x)
┌──────────────────▼──────────────────────┐
│              PC2 (192.168.2.138)         │
│  ┌─────────────────────────────────┐    │
│  │ SSH receives TCP on port 15000  │    │
│  └────────────────┬────────────────┘    │
│                   │                     │
│  ┌────────────────▼────────────────┐    │
│  │ socat (TCP→UDP)                 │    │
│  │ TCP:15000 → UDP:192.168.1.2:50000│   │
│  └────────────────┬────────────────┘    │
│                   │ Ethernet            │
│                   │                     │
│  ┌────────────────▼────────────────┐    │
│  │ Leader Robot                    │    │
│  │ 192.168.1.2                     │    │
│  │ TCP:50001 ✓  UDP:50000 ✓       │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

## Port Mapping

| Port  | Protocol | PC1 Process          | PC2 Process              | Destination              |
|-------|----------|----------------------|--------------------------|--------------------------|
| 50001 | TCP      | SSH tunnel (direct)  | -                        | Leader 192.168.1.2:50001 |
| 50000 | UDP      | socat (UDP listener) | -                        | → TCP:15000              |
| 15000 | TCP      | SSH tunnel           | socat (TCP listener)     | → Leader UDP:50000       |

## Setup Commands

### Start Everything

```bash
cd /home/tensi/tensi-trossen-studio
./deployment/start-all-tunnels.sh
```

### Stop Everything

```bash
cd /home/tensi/tensi-trossen-studio
./deployment/stop-all-tunnels.sh
```

### Verify Setup

```bash
# Check PC1 socat
pgrep -af "socat.*UDP4-LISTEN:50000"

# Check PC2 socat
ssh hadi@192.168.2.138 'pgrep -af "socat.*TCP4-LISTEN:15000"'

# Check SSH tunnels
ps aux | grep 'ssh -f -N -L' | grep -v grep

# Test ports
nc -zv localhost 50001  # TCP to leader
nc -zv localhost 15000  # UDP relay
```

## Why This Works

1. **SSH limitation**: SSH only forwards TCP, not UDP
2. **socat conversion**: Converts UDP↔TCP at each endpoint
3. **TCP tunneling**: SSH tunnels the intermediate TCP (port 15000)
4. **End-to-end UDP**: lerobot sends/receives UDP, leader receives UDP
5. **Transparency**: lerobot code unchanged, still uses localhost:50000

## Startup Process

**Automatic (with start-all-tunnels.sh):**
1. PC2 socat starts (TCP:15000 → Leader UDP:50000)
2. SSH tunnels established (TCP:50001 and TCP:15000)
3. PC1 socat starts (UDP:50000 → TCP:15000)
4. Verification runs
5. Ready for teleoperation

**Manual Steps:**
```bash
# On PC2
socat TCP4-LISTEN:15000,reuseaddr,fork UDP4:192.168.1.2:50000 &

# On PC1
ssh -f -N -L 50001:192.168.1.2:50001 hadi@192.168.2.138
ssh -f -N -L 15000:localhost:15000 hadi@192.168.2.138
socat UDP4-LISTEN:50000,reuseaddr,fork TCP4:localhost:15000 &
```

## Configuration

**~/.tensi_trossen_studio/config.json:**
```json
{
  "robot": {
    "leader_ip": "127.0.0.1",      // Tunneled to PC2 → Leader
    "follower_ip": "192.168.1.5"   // Direct Ethernet
  }
}
```

## Troubleshooting

### UDP Connection Refused

```bash
# Verify complete chain
pgrep -af socat  # Both PC1 and PC2 should show
ps aux | grep 'ssh.*15000'  # Should show tunnel

# Test intermediate port
nc -zv localhost 15000  # Should succeed

# Check PC2 relay
ssh hadi@192.168.2.138 'pgrep -af socat'
```

### TCP Works But UDP Fails

```bash
# Restart PC1 socat
pkill -f "socat.*UDP4-LISTEN:50000"
socat UDP4-LISTEN:50000,reuseaddr,fork TCP4:localhost:15000 &

# Verify
pgrep -af "socat.*UDP4-LISTEN:50000"
```

### Complete Reset

```bash
./deployment/stop-all-tunnels.sh
sleep 2
./deployment/start-all-tunnels.sh
```

## Performance

- **Latency**: ~2-5ms added (WiFi + conversion overhead)
- **Bandwidth**: UDP datagrams wrapped in TCP segments
- **Reliability**: TCP stream may batch/split UDP datagrams (usually OK for control signals)

## Alternative: Direct UDP Access

If PC1 and PC2 could route directly between Ethernet networks (without separate WiFi):
- No tunnels needed
- Direct UDP/TCP to both robots
- Lower latency, simpler setup

Current setup is necessary because robots are on isolated Ethernet segments.
