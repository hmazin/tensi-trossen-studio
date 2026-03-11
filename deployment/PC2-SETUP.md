# PC2 setup — what to run to start the leader

PC2 is the machine **connected to the leader robot** (Ethernet). To use **Start Leader** from the Studio (or to run distributed teleoperation), PC2 must be running the **Leader Service**.

---

## 1. One-time setup on PC2

### 1.1 Install Python and the Trossen arm package

- **Python 3.10+**
- **trossen_arm** (Trossen’s driver for the leader arm):

  ```bash
  pip install trossen_arm
  # or, if you use the Trossen/LeRobot environment:
  # follow https://docs.trossenrobotics.com/ and use their venv/uv
  ```

### 1.2 Copy the Leader Service script to PC2

The script is `leader_service.py`. Put it on PC2 so it can be run by hand or by the Studio (via SSH).

**Option A — Copy from your repo (from PC1 or a clone):**

```bash
# On PC1 (or any machine with the repo):
scp tensi-trossen-studio/deployment/leader_service.py USER@PC2_IP:~/

# Example:
scp deployment/leader_service.py hadi@192.168.2.138:~/
```

**Option B — On PC2, clone the repo and use the file:**

```bash
# On PC2:
git clone https://github.com/hmazin/tensi-trossen-studio.git
# Then run from the deployment folder (see below) or copy:
cp tensi-trossen-studio/deployment/leader_service.py ~/
```

After this, PC2 should have `~/leader_service.py` (or the file inside a cloned repo).

### 1.3 (Optional) Allow SSH from PC1 and open port 5555

- So the Studio can **Start Leader** via SSH, set up SSH from PC1 to PC2 (e.g. `ssh-copy-id USER@PC2_IP`).
- On PC2, allow TCP port **5555** (e.g. `sudo ufw allow 5555/tcp`).

---

## 2. Run the Leader Service on PC2

You only need **one** of these.

### Option A — One-click from the Launcher (PC1) — recommended

1. On PC1, open the **Launcher** (`python launcher.py` from the repo root).
2. In **section 4**, set **PC2 WiFi IP**, **PC2 Ethernet** (leader robot IP), and **PC2 SSH user** (e.g. your username on PC2). Click **Save IPs**.
3. Ensure SSH from PC1 to PC2 works (e.g. `ssh-copy-id USER@PC2_IP`).
4. In **section 5**, click **Setup PC2 & start Leader**. The launcher will copy `leader_service.py` to PC2, start the service, and verify. A success or error message will appear; on success you can use **Start Teleoperation** in Studio.

### Option B — From the Studio (PC1)

1. In Studio **Settings**: enable **Remote Leader Mode**, set **Leader Service Host** to PC2’s **192.168.2.x** IP and port **5555**, set **Remote Leader SSH user** to your PC2 username.
2. Save, then in the dashboard click **Start Leader**.  
   The backend will SSH to PC2 and run `python3 -u ~/leader_service.py --ip 192.168.1.2 --port 5555 --fps 60`.

### Option C — Manually on PC2 (terminal)

On **PC2**:

```bash
python3 -u ~/leader_service.py --ip 192.168.1.2 --port 5555 --fps 60
```

- `--ip 192.168.1.2` = leader robot’s Ethernet IP (on PC2’s 192.168.1.x network).
- `--port 5555` = port the service listens on (PC1 will connect to PC2_IP:5555).
- Leave this terminal open; when you see “Waiting for client connection…”, the leader is ready. Stop with Ctrl+C when done.

### Option D — On PC2 using the repo script (if you have the repo on PC2)

From the repo’s deployment folder (and with `trossen_arm` in that environment):

```bash
cd ~/tensi-trossen-studio
./deployment/start-leader-service.sh
# Or with custom leader IP/port:
./deployment/start-leader-service.sh 192.168.1.2 5555 60
```

(That script expects `leader_service.py` to be run from a directory where it’s available; adjust or copy to `~/leader_service.py` if needed.)

### Option E — Auto-start on boot (PC2)

See [REMOTE-LEADER-SETUP.md](REMOTE-LEADER-SETUP.md): install `leader-service.service` on PC2 and enable it.

---

## 3. Check that it’s running

- **From PC1:** In the Studio, the Leader Service card should show **Running** (green).
- **From PC1 terminal:** `nc -zv PC2_192.168.2.x 5555` should succeed.
- **On PC2:** `pgrep -f leader_service.py` should show a PID; logs: `tail -f /tmp/leader_service.log` (if started by the script that logs there).

---

## 4. Summary

| What | Where |
|------|--------|
| **Leader Service script** | PC2: `~/leader_service.py` (copy from repo `deployment/leader_service.py`) |
| **Python package** | PC2: `trossen_arm` |
| **Command to run on PC2** | `python3 -u ~/leader_service.py --ip 192.168.1.2 --port 5555 --fps 60` |
| **Or** | Use **Start Leader** in the Studio (PC1) so it runs the same command on PC2 via SSH |

Once the Leader Service is running on PC2, you can click **Start Teleoperation** in the Studio and the leader on PC2 will drive the follower on PC1.
