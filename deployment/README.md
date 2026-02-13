# Deployment Documentation

This directory contains all documentation and scripts for deploying the distributed teleoperation system across two PCs.

## Current Status

**⏸️ READY FOR TESTING - Waiting for Hardware**

The distributed teleoperation system is fully implemented and ready for testing. Testing is blocked pending delivery of a second NetGear GS305E switch (ETA: 2 days from 2026-02-13).

**What's Working:**
- ✅ UDP-over-SSH tunneling infrastructure
- ✅ Automated startup/shutdown scripts
- ✅ Camera management system
- ✅ Backend API and frontend UI
- ✅ SSH authentication configured

**What's Blocked:**
- ⏸️ Leader robot connectivity (needs NetGear switch)

## Quick Links

### For Daily Use
📋 **[PRE-FLIGHT-CHECKLIST.md](./PRE-FLIGHT-CHECKLIST.md)** - Step-by-step checklist for when the switch arrives

📖 **[QUICK-START.md](./QUICK-START.md)** - Quick reference for starting/stopping the system

### For Setup & Configuration
🔧 **[SETUP-WITH-TWO-SWITCHES.md](./SETUP-WITH-TWO-SWITCHES.md)** - Complete setup guide

📊 **[IMPLEMENTATION-SUMMARY.md](./IMPLEMENTATION-SUMMARY.md)** - What we built and why

🌐 **[UDP-ARCHITECTURE.md](./UDP-ARCHITECTURE.md)** - Technical details of UDP tunneling

## Scripts

### Automated Control
- **`start-all-tunnels.sh`** - Start all tunneling infrastructure (SSH + socat)
- **`stop-all-tunnels.sh`** - Stop all tunnels and clean up processes
- **`test-setup.sh`** - Verify system configuration

### Individual Components
- **`ssh-tunnel-complete.sh`** - Create SSH tunnels (TCP + UDP wrapper)
- **`setup-pc1-udp-wrapper.sh`** - Start UDP-to-TCP wrapper on PC1
- **`setup-pc2-udp-relay.sh`** - Start TCP-to-UDP relay on PC2

### Deployment Scripts
- **`deploy-pc1.sh`** - Deploy backend/frontend on PC1 (unused in current setup)
- **`deploy-pc2.sh`** - Deploy camera service on PC2 (unused in current setup)

## Documentation Overview

### PRE-FLIGHT-CHECKLIST.md
**Use this when the NetGear switch arrives!**

Complete step-by-step checklist covering:
- Hardware connection verification
- Network testing
- System startup sequence
- Teleoperation testing
- Success criteria
- Troubleshooting

### QUICK-START.md
**Daily usage reference**

Quick commands for:
- Starting the system
- Stopping the system
- Troubleshooting common issues
- Verification checks

### SETUP-WITH-TWO-SWITCHES.md
**Complete setup documentation**

Comprehensive guide covering:
- Physical network topology
- Prerequisites and dependencies
- Hardware requirements
- Step-by-step setup instructions
- Troubleshooting guide
- Network flow diagrams

### IMPLEMENTATION-SUMMARY.md
**Technical implementation details**

Documents:
- Architecture decisions
- Problems solved and solutions
- Known issues and limitations
- Testing plan
- Key learnings

### UDP-ARCHITECTURE.md
**UDP tunneling technical details**

Explains:
- Why UDP tunneling was needed
- How the dual-socat solution works
- Data flow diagrams
- Port mapping
- Testing procedures

## Hardware Requirements

### Current Setup (PC1)
- Ubuntu PC with WiFi + Ethernet
- NetGear GS305E switch
- Follower robot with iNerve controller
- 2x RealSense cameras

### Required Addition (PC2)
- ⏳ **NetGear GS305E switch** (ETA: 2 days)
- Ubuntu PC with WiFi + Ethernet (already have)
- Leader robot with iNerve controller (already have)

### Network Topology After Switch Arrives

```
PC1: 192.168.2.140 (WiFi), 192.168.1.100 (Ethernet)
  └── NetGear 1
      ├── Follower iNerve (192.168.1.5)
      └── Cameras (USB to PC1)

PC2: 192.168.2.138 (WiFi), 192.168.1.x (Ethernet)
  └── NetGear 2
      └── Leader iNerve (192.168.1.2)

WiFi (192.168.2.x): SSH tunnels between PC1 ↔ PC2
```

## Critical Information

### Why the Second Switch is Required

The Leader robot's iNerve controller **cannot function** with a direct PC-to-iNerve connection. Testing revealed:
- Direct connection: `ping 192.168.1.2` from PC2 fails
- Direct connection: TCP/UDP ports unreachable
- Direct connection: iNerve LED goes red (fault state)

The iNerve controllers require proper network infrastructure provided by switches (ARP, broadcast, specific timing, etc.).

### Configuration Changes

The `config.json` has been updated for distributed operation:

```json
{
  "robot": {
    "leader_ip": "127.0.0.1",     // ← Routes through SSH tunnel
    "follower_ip": "192.168.1.5", // ← Direct Ethernet
    ...
  }
}
```

**Do not change `leader_ip` back to `192.168.1.2`** - the tunneling architecture requires localhost.

## Getting Started (When Switch Arrives)

1. **Read:** [PRE-FLIGHT-CHECKLIST.md](./PRE-FLIGHT-CHECKLIST.md)
2. **Connect:** Leader iNerve → NetGear 2 → PC2
3. **Verify:** Network connectivity from PC2
4. **Run:** `./start-all-tunnels.sh`
5. **Test:** Follow checklist to verify teleoperation

## Troubleshooting

### Common Issues

**Leader LED is red:**
```bash
# Power cycle the iNerve controller
# Wait for green LED
```

**Can't reach leader from PC2:**
```bash
ssh hadi@192.168.2.138 'ping -c 2 192.168.1.2'
# If fails: Check switch connection
```

**Tunnels not starting:**
```bash
./stop-all-tunnels.sh
./start-all-tunnels.sh
```

**Cameras unavailable:**
```bash
pkill -f lerobot
# Restart backend
```

### Logs

**PC1 socat log:**
```bash
tail -f /tmp/socat-pc1.log
```

**PC2 socat log:**
```bash
ssh hadi@192.168.2.138 'tail -f /tmp/socat.log'
```

**Backend logs:**
Check the terminal running `uvicorn`

## Architecture Highlights

### UDP-over-SSH Tunneling

Since SSH cannot tunnel UDP natively, we implemented a dual-socat architecture:

1. **PC1 Wrapper:** Converts UDP:50000 → TCP:15000
2. **SSH Tunnel:** Forwards TCP:15000 to PC2
3. **PC2 Relay:** Converts TCP:15000 → UDP:50000 → Robot

This allows bidirectional UDP communication over SSH.

### Camera Management

Implemented singleton `CameraManager` to handle RealSense camera lifecycle:
- Only one process can access cameras at a time
- Auto-releases cameras before teleoperation
- Restarts streaming after teleoperation ends
- Thread-safe operations

### Distributed Architecture

- **PC1:** Operator station with UI, cameras, follower robot
- **PC2:** Leader robot station (minimal, just robot control)
- **Communication:** SSH tunnels over WiFi network
- **Benefit:** Physical separation of leader/follower robots

## Files in This Directory

### Documentation
- `README.md` - This file
- `PRE-FLIGHT-CHECKLIST.md` - Testing checklist
- `QUICK-START.md` - Quick reference
- `SETUP-WITH-TWO-SWITCHES.md` - Complete setup guide
- `IMPLEMENTATION-SUMMARY.md` - Technical summary
- `UDP-ARCHITECTURE.md` - UDP tunneling details
- `QUICKSTART-TUNNELS.md` - Tunnel quick reference

### Scripts
- `start-all-tunnels.sh` - Start everything
- `stop-all-tunnels.sh` - Stop everything
- `test-setup.sh` - Verify setup
- `ssh-tunnel-complete.sh` - SSH tunnel setup
- `setup-pc1-udp-wrapper.sh` - PC1 socat wrapper
- `setup-pc2-udp-relay.sh` - PC2 socat relay
- `ssh-tunnel-leader.sh` - TCP tunnel only (deprecated)
- `ssh-tunnel-udp.sh` - Early UDP attempt (deprecated)

### Legacy/Unused
- `deploy-pc1.sh` - Deployment automation (not needed for tunnel setup)
- `deploy-pc2.sh` - PC2 deployment (not needed, PC2 only runs socat)
- `tensi-backend.service` - Systemd service (deferred)
- `tensi-camera.service` - Systemd service (deferred)

### Other Files
- `CHECKLIST.md` - Original deployment checklist
- `IMPLEMENTATION.md` - Original implementation plan
- `QUICKREF.md` - Original quick reference
- `PC2-SETUP-GUIDE.md` - Original PC2 guide

## Next Steps

1. ⏳ **Wait** for NetGear switch delivery
2. 🔌 **Connect** hardware per topology diagram
3. ✅ **Verify** network connectivity
4. 🚀 **Test** using PRE-FLIGHT-CHECKLIST.md
5. 🎉 **Celebrate** distributed teleoperation!

## Support

For issues or questions:
1. Check [QUICK-START.md](./QUICK-START.md) troubleshooting section
2. Review [SETUP-WITH-TWO-SWITCHES.md](./SETUP-WITH-TWO-SWITCHES.md) detailed guide
3. Check logs: `/tmp/socat-pc1.log` and `ssh hadi@192.168.2.138 'cat /tmp/socat.log'`

---

**Last Updated:** 2026-02-13  
**Status:** Ready for testing when switch arrives  
**Project:** TENSI Trossen Studio - Distributed Teleoperation
