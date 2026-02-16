# Archived Documentation

These files document the **earlier SSH tunnel / UDP relay approach** for distributed teleoperation. This approach was superseded by the **Remote Leader** architecture (see `../REMOTE-LEADER-SETUP.md`).

The SSH tunnel approach attempted to relay the Trossen iNerve's raw TCP/UDP protocol over the network, which failed due to:
- Sub-millisecond latency requirements of the iNerve protocol
- UDP tunneling complexity (socat double-hop)
- Data corruption over WiFi latency

The Remote Leader architecture solved this by running the Trossen driver locally on each robot's PC and streaming only high-level joint positions over a simple TCP connection.

These files are kept for historical reference only.
