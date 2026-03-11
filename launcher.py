#!/usr/bin/env python3
"""
TENSI Trossen Studio Launcher (PC1).
GUI to start/stop backend and frontend, and view/edit PC1/PC2 IPs.
Run from repo root: python launcher.py
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

# Repo root (where launcher.py lives)
REPO_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"
LAUNCHER_CONFIG_PATH = Path.home() / ".tensi_trossen_studio" / "launcher.json"

BACKEND_PORT = 8000
FRONTEND_PORT = 5173  # Vite default; may use 5174 if 5173 busy
LEADER_SERVICE_PORT = 5555
LEADER_SERVICE_SCRIPT = REPO_ROOT / "deployment" / "leader_service.py"


def load_launcher_config():
    """Load launcher config (IPs, SSH user, etc.)."""
    default = {
        "pc1_wifi_ip": "",
        "pc1_ethernet_ip": "",
        "follower_ip": "192.168.1.5",
        "pc2_wifi_ip": "192.168.2.138",
        "pc2_ethernet_ip": "192.168.1.200",
        "leader_ip": "192.168.1.2",
        "pc2_ssh_user": "",
    }
    if not LAUNCHER_CONFIG_PATH.exists():
        return default
    try:
        data = json.loads(LAUNCHER_CONFIG_PATH.read_text())
        out = {**default, **data}
        # Backward compat: old configs used pc2_ethernet_ip for the leader robot IP
        if "leader_ip" not in data and data.get("pc2_ethernet_ip"):
            out["leader_ip"] = data["pc2_ethernet_ip"]
        return out
    except Exception:
        return default


def save_launcher_config(config: dict):
    LAUNCHER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAUNCHER_CONFIG_PATH.write_text(json.dumps(config, indent=2))


def detect_pc1_ips():
    """Try to detect PC1 WiFi and Ethernet IPs (Linux)."""
    wifi, ethernet = "", ""
    try:
        out = subprocess.run(
            ["ip", "-4", "addr", "show"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode != 0:
            return wifi, ethernet
        current_interface = None
        for line in out.stdout.splitlines():
            line = line.strip()
            # New interface line: "2: enp6s0: ..." or "3: wlp13s0: ..."
            if line and not line.startswith("inet ") and line[0].isdigit() and ":" in line:
                parts = line.split(":", 2)
                if len(parts) >= 2:
                    current_interface = parts[1].strip()
            if line.startswith("inet "):
                addr = line.split()[1].split("/")[0]
                if addr.startswith("127."):
                    continue
                if current_interface:
                    if current_interface.startswith("wl") or "wlan" in current_interface.lower():
                        if not wifi:
                            wifi = addr
                    elif current_interface.startswith(("en", "eth")):
                        if not ethernet:
                            ethernet = addr
        # Fallback: first two non-loopback IPs
        if not wifi and not ethernet:
            for line in out.stdout.splitlines():
                if line.strip().startswith("inet ") and "127.0.0" not in line:
                    addr = line.strip().split()[1].split("/")[0]
                    if not ethernet:
                        ethernet = addr
                    elif not wifi:
                        wifi = addr
                        break
    except Exception:
        pass
    return wifi, ethernet


def scan_usb_video_devices():
    """List USB video devices (Linux /dev/video*). Returns list of {index, path, name}."""
    import glob
    devices = []
    try:
        for path in sorted(glob.glob("/dev/video*"), key=lambda p: (len(p), p)):
            try:
                base = os.path.basename(path)
                if not base.startswith("video"):
                    continue
                idx_str = base.replace("video", "")
                if not idx_str.isdigit():
                    continue
                index = int(idx_str)
                name = ""
                sys_name = f"/sys/class/video4linux/{base}/name"
                if os.path.exists(sys_name):
                    try:
                        name = open(sys_name).read().strip()
                    except Exception:
                        pass
                devices.append({"index": index, "path": path, "name": name or path})
            except Exception:
                continue
    except Exception:
        pass
    return devices


def _port_in_use(port: int) -> bool:
    """True if something is listening on the given port."""
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            return s.connect_ex(("127.0.0.1", port)) == 0
    except Exception:
        return False


def backend_status():
    """True if backend health responds."""
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{BACKEND_PORT}/health", method="GET")
        with urllib.request.urlopen(req, timeout=2) as r:
            return r.getcode() == 200
    except Exception:
        return False


def frontend_status():
    """True if frontend port is in use (process listening)."""
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            return s.connect_ex(("127.0.0.1", FRONTEND_PORT)) == 0
    except Exception:
        return False


def _post_request(url: str, timeout: int = 5) -> tuple[bool, str]:
    """POST to a local HTTP endpoint. Returns (ok, response/error text)."""
    try:
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", errors="replace").strip()
            return 200 <= r.getcode() < 300, body
    except Exception as e:
        return False, str(e)


def _terminate_process(proc, timeout: int = 5) -> None:
    """Terminate a local child process, force-killing if needed."""
    if proc is None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()


def _kill_tcp_port(port: int, timeout: int = 3) -> None:
    """Best-effort kill for any process listening on the given TCP port."""
    try:
        subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True, timeout=timeout)
    except Exception:
        pass


def stop_remote_leader_service(pc2_wifi: str, ssh_user: str) -> tuple[bool, str]:
    """Stop leader_service.py on PC2 over SSH and verify it is gone."""
    user = (ssh_user or "hadi").strip()
    if not pc2_wifi:
        return False, "PC2 WiFi IP is empty."
    if not user:
        return False, "PC2 SSH user is empty."

    code, out = _ssh_run(user, pc2_wifi, "pkill -f leader_service.py 2>/dev/null || true", timeout=10)
    if code != 0:
        return False, out or f"Failed to stop leader service on {pc2_wifi}."

    time.sleep(1)
    code, out = _ssh_run(user, pc2_wifi, "pgrep -f leader_service.py", timeout=5)
    if code == 0 and out.strip():
        return False, "leader_service.py is still running on PC2."
    return True, "Leader service stopped on PC2."


def _ssh_run(user: str, host: str, command: str, timeout: int = 10) -> tuple[int, str]:
    """Run command on host via SSH. Returns (exit_code, combined stdout+stderr)."""
    try:
        r = subprocess.run(
            [
                "ssh",
                "-o", "ConnectTimeout=5",
                "-o", "BatchMode=yes",
                "-o", "StrictHostKeyChecking=no",
                f"{user}@{host}",
                command,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return -1, "SSH command timed out"
    except Exception as e:
        return -1, str(e)


def _scp(local_path: Path, user: str, host: str, remote_path: str, timeout: int = 15) -> tuple[int, str]:
    """Copy local_path to user@host:remote_path. Returns (exit_code, stderr)."""
    try:
        r = subprocess.run(
            [
                "scp",
                "-o", "ConnectTimeout=5",
                "-o", "BatchMode=yes",
                "-o", "StrictHostKeyChecking=no",
                str(local_path),
                f"{user}@{host}:{remote_path}",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return -1, "SCP timed out"
    except Exception as e:
        return -1, str(e)


def run_pc2_leader_setup(pc2_wifi: str, leader_ip: str, ssh_user: str) -> tuple[bool, str]:
    """
    Setup PC2 for leader: copy leader_service.py, start service, verify.
    Returns (success, message). Run from a background thread.
    """
    user = (ssh_user or "hadi").strip()
    if not user:
        return False, "PC2 SSH user is empty. Set it in section 4 and click Save IPs."
    if not pc2_wifi or not leader_ip:
        return False, "PC2 WiFi IP and Ethernet (leader) IP must be set in section 4."
    if not LEADER_SERVICE_SCRIPT.exists():
        return False, f"Leader script not found: {LEADER_SERVICE_SCRIPT}"

    # 1. Ping PC2
    try:
        r = subprocess.run(
            ["ping", "-c", "1", "-W", "2", pc2_wifi],
            capture_output=True,
            timeout=5,
        )
        if r.returncode != 0:
            return False, f"Cannot reach PC2 at {pc2_wifi}. Is it on the same network?"
    except Exception as e:
        return False, f"Ping failed: {e}"

    # 2. SSH test
    code, out = _ssh_run(user, pc2_wifi, "echo ok", timeout=8)
    if code != 0:
        return False, (
            f"SSH to {user}@{pc2_wifi} failed.\n\n"
            "Set up SSH keys first: ssh-copy-id " + user + "@" + pc2_wifi + "\n\n" + (out or "")
        )

    # 3. Copy leader_service.py to PC2
    code, out = _scp(LEADER_SERVICE_SCRIPT, user, pc2_wifi, "~/leader_service.py", timeout=15)
    if code != 0:
        return False, f"Failed to copy leader_service.py to PC2:\n{out or 'unknown'}"

    # 4. Stop any existing leader service
    _ssh_run(user, pc2_wifi, "pkill -f leader_service.py 2>/dev/null || true", timeout=5)
    time.sleep(1)

    # 5. Check leader robot reachable from PC2
    code, _ = _ssh_run(user, pc2_wifi, f"ping -c 1 -W 2 {leader_ip}", timeout=5)
    if code != 0:
        return False, (
            f"PC2 cannot reach the leader robot at {leader_ip}.\n"
            "Is the leader iNerve powered on (green LED) and connected via the NetGear switch?"
        )

    # 6. Start leader service on PC2
    start_cmd = (
        f"nohup python3 -u ~/leader_service.py --ip {leader_ip} --port {LEADER_SERVICE_PORT} --fps 60 "
        f"> /tmp/leader_service.log 2>&1 & echo $!"
    )
    code, out = _ssh_run(user, pc2_wifi, start_cmd, timeout=15)
    if code != 0:
        return False, f"Failed to start leader service on PC2:\n{out or 'unknown'}"

    time.sleep(2)

    # 7. Verify process is running
    code, check = _ssh_run(user, pc2_wifi, "pgrep -f leader_service.py", timeout=5)
    if code != 0 or not check.strip():
        _, log_out = _ssh_run(user, pc2_wifi, "tail -25 /tmp/leader_service.log 2>/dev/null")
        return False, (
            "Leader service exited shortly after start. Common causes:\n"
            "- Python 3 or trossen_arm not installed on PC2 (install: pip install trossen_arm)\n"
            "- Leader robot not ready (power cycle iNerve, wait for green LED)\n\n"
            f"Log from PC2:\n{log_out or '(no log)'}"
        )

    # 8. Verify port from PC1 (optional; may be blocked by firewall)
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(3)
            if s.connect_ex((pc2_wifi, LEADER_SERVICE_PORT)) == 0:
                return True, (
                    f"PC2 setup complete. Leader service is running on {pc2_wifi}:{LEADER_SERVICE_PORT}.\n\n"
                    "In Studio: enable Remote Leader Mode, set Leader Service Host to this PC2 IP and port 5555, then Start Teleoperation."
                )
    except Exception:
        pass
    return True, (
        f"Leader service started on PC2 (process running). Port {LEADER_SERVICE_PORT} not reachable from this PC yet "
        f"(firewall on PC2? run: sudo ufw allow {LEADER_SERVICE_PORT}/tcp).\n\n"
        "In Studio: enable Remote Leader Mode and set Leader Service Host to PC2 IP, then Start Teleoperation."
    )


def _show_copyable_error(parent, title, message, log_path=None):
    """Show error in a window with selectable text and Copy / Open log buttons."""
    import tkinter as tk
    from tkinter import ttk

    win = tk.Toplevel(parent)
    win.title(title)
    win.geometry("760x480")
    win.minsize(560, 320)
    win.transient(parent)
    win.grab_set()
    win.columnconfigure(0, weight=1)
    win.rowconfigure(0, weight=1)

    f = ttk.Frame(win, padding=10)
    f.grid(row=0, column=0, sticky="nsew")
    f.columnconfigure(0, weight=1)
    f.rowconfigure(0, weight=1)

    text_frame = ttk.Frame(f)
    text_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
    text_frame.columnconfigure(0, weight=1)
    text_frame.rowconfigure(0, weight=1)

    scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL)
    text = tk.Text(
        text_frame,
        wrap=tk.WORD,
        font=("TkDefaultFont", 10),
        state=tk.DISABLED,
        cursor="arrow",
        yscrollcommand=scrollbar.set,
    )
    text.grid(row=0, column=0, sticky="nsew")
    scrollbar.configure(command=text.yview)
    scrollbar.grid(row=0, column=1, sticky="ns")
    text.configure(state=tk.NORMAL)
    text.insert(tk.END, message)
    text.configure(state=tk.DISABLED)

    def copy_all():
        parent.clipboard_clear()
        parent.clipboard_append(message)
        try:
            parent.update()
        except Exception:
            pass

    def open_log():
        if log_path and Path(log_path).exists():
            try:
                if sys.platform == "win32":
                    os.startfile(log_path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", log_path], start_new_session=True)
                else:
                    subprocess.Popen(["xdg-open", log_path], start_new_session=True)
            except Exception:
                copy_all()

    bf = ttk.Frame(f)
    bf.grid(row=1, column=0, sticky="ew")
    ttk.Button(bf, text="Copy to clipboard", command=copy_all).pack(side=tk.LEFT, padx=(0, 8))
    if log_path:
        ttk.Button(bf, text="Open log file", command=open_log).pack(side=tk.LEFT, padx=(0, 8))
    ttk.Button(bf, text="OK", command=win.destroy).pack(side=tk.LEFT)
    win.wait_window(win)


def _add_form_row(parent, row: int, label_text: str, variable, entry_width: int = 22):
    """Add a label/entry row to a form frame."""
    import tkinter as tk
    from tkinter import ttk

    ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=(0, 8))
    entry = ttk.Entry(parent, textvariable=variable, width=entry_width)
    entry.grid(row=row, column=1, sticky="ew", pady=(0, 8))
    return entry


def _add_helper_label(parent, text: str, row: int, column: int = 0, columnspan: int = 1, wraplength: int = 520):
    """Add wrapped helper text without relying on theme-specific colors."""
    import tkinter as tk
    from tkinter import ttk

    label = ttk.Label(parent, text=text, wraplength=wraplength, justify=tk.LEFT)
    label.grid(row=row, column=column, columnspan=columnspan, sticky="w", pady=(0, 10))
    return label


def build_launcher_ui(root):
    """Build the launcher UI on an existing Tk root."""
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox
    except ImportError:
        print("tkinter is required. On Debian/Ubuntu: sudo apt install python3-tk")
        sys.exit(1)

    config = load_launcher_config()
    pc1_wifi, pc1_eth = detect_pc1_ips()
    if not config.get("pc1_wifi_ip") and pc1_wifi:
        config["pc1_wifi_ip"] = pc1_wifi
    if not config.get("pc1_ethernet_ip") and pc1_eth:
        config["pc1_ethernet_ip"] = pc1_eth
    save_launcher_config(config)

    # Mutable container so nested functions can read/write without `global`
    procs = {"backend": None, "frontend": None}

    root.title("TENSI Trossen Studio - Launcher (PC1)")
    root.minsize(720, 560)
    root.geometry("860x680")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    main = ttk.Frame(root, padding=14)
    main.grid(row=0, column=0, sticky="nsew")
    main.columnconfigure(0, weight=1)
    main.rowconfigure(1, weight=1)

    header = ttk.Frame(main)
    header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
    header.columnconfigure(0, weight=1)
    ttk.Label(header, text="TENSI Trossen Studio Launcher", font=("", 14, "bold")).grid(row=0, column=0, sticky="w")
    ttk.Label(
        header,
        text="Start local services, manage network settings, and run PC2 tools from one place.",
        wraplength=780,
        justify=tk.LEFT,
    ).grid(row=1, column=0, sticky="w", pady=(4, 0))

    notebook = ttk.Notebook(main)
    notebook.grid(row=1, column=0, sticky="nsew")

    services_tab = ttk.Frame(notebook, padding=14)
    network_tab = ttk.Frame(notebook, padding=14)
    tools_tab = ttk.Frame(notebook, padding=14)
    notebook.add(services_tab, text="Services")
    notebook.add(network_tab, text="Network")
    notebook.add(tools_tab, text="Tools")

    for tab in (services_tab, network_tab, tools_tab):
        tab.columnconfigure(0, weight=1)

    services_tab.columnconfigure(1, weight=1)
    network_tab.columnconfigure(1, weight=1)
    tools_tab.columnconfigure(1, weight=1)

    # --- Services tab ---
    backend_frame = ttk.LabelFrame(services_tab, text="Backend", padding=12)
    backend_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 12))
    backend_frame.columnconfigure(1, weight=1)
    _add_helper_label(backend_frame, "Runs the Studio API server on port 8000.", row=0, columnspan=3, wraplength=300)

    be_status_var = tk.StringVar(value="Checking...")
    ttk.Label(backend_frame, text="Status").grid(row=1, column=0, sticky="w", padx=(0, 8))
    ttk.Label(backend_frame, textvariable=be_status_var).grid(row=1, column=1, sticky="w")

    def refresh_backend_status():
        be_status_var.set("Running" if backend_status() else "Stopped")

    def start_backend():
        if procs["backend"] is not None:
            messagebox.showinfo("Backend", "Backend already started from this launcher.")
            refresh_backend_status()
            return
        if backend_status():
            refresh_backend_status()
            return
        if not (BACKEND_DIR / "pyproject.toml").exists():
            messagebox.showerror("Backend", f"Backend dir not found: {BACKEND_DIR}")
            return
        if _port_in_use(BACKEND_PORT):
            if messagebox.askyesno(
                "Port 8000 in use",
                "Port 8000 is already in use (another backend or process).\n\n"
                "Free the port and start backend?",
                default=messagebox.YES,
            ):
                try:
                    subprocess.run(
                        ["fuser", "-k", f"{BACKEND_PORT}/tcp"],
                        capture_output=True,
                        timeout=5,
                    )
                    time.sleep(1.5)
                except Exception:
                    pass
            else:
                return
        try:
            env = os.environ.copy()
            stderr_file = tempfile.NamedTemporaryFile(mode="w+", suffix=".log", delete=False)
            stderr_path = stderr_file.name
            stderr_file.close()
            stderr_handle = open(stderr_path, "w")
            procs["backend"] = subprocess.Popen(
                ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", str(BACKEND_PORT)],
                cwd=BACKEND_DIR,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=stderr_handle,
                text=True,
            )
            be_status_var.set("Starting...")

            def check_backend_started(attempt=0):
                if backend_status():
                    be_status_var.set("Running")
                    return
                p = procs["backend"]
                if p is not None and p.poll() is not None:
                    procs["backend"] = None
                    be_status_var.set("Stopped")
                    err = ""
                    try:
                        with open(stderr_path, "r", errors="replace") as f:
                            err = f.read().strip()
                    except Exception:
                        pass
                    # Save full log so user can open it
                    log_dir = Path.home() / ".tensi_trossen_studio"
                    log_dir.mkdir(parents=True, exist_ok=True)
                    full_log = log_dir / "backend_stderr.log"
                    try:
                        with open(full_log, "w", errors="replace") as f:
                            f.write(err or "(no stderr output)")
                    except Exception:
                        full_log = None
                    try:
                        os.unlink(stderr_path)
                    except Exception:
                        pass
                    rc = p.returncode
                    msg = f"Backend process exited (code {rc})."
                    if full_log:
                        msg += f"\n\nFull log saved to:\n{full_log}"
                    if err:
                        lines = err.splitlines()[-30:]
                        msg += "\n\nLast output:\n" + "\n".join(lines)
                    else:
                        msg += "\n\nRun in a terminal to see errors:\ncd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"
                    try:
                        _show_copyable_error(root, "Backend error", msg, str(full_log) if full_log else None)
                    except Exception:
                        messagebox.showerror("Backend", msg)
                    return
                if attempt < 10:
                    root.after(1500, lambda: check_backend_started(attempt + 1))
                else:
                    refresh_backend_status()

            root.after(1500, lambda: check_backend_started(0))
        except FileNotFoundError:
            messagebox.showerror("Backend", "uv not found. Install uv and run from repo root.")
        except Exception as e:
            messagebox.showerror("Backend", str(e))

    def stop_backend():
        if procs["backend"] is not None:
            _terminate_process(procs["backend"], timeout=5)
            procs["backend"] = None
        _kill_tcp_port(BACKEND_PORT)
        be_status_var.set("Stopped")

    ttk.Button(backend_frame, text="Start backend", command=start_backend).grid(row=2, column=0, sticky="w", pady=(10, 0))
    ttk.Button(backend_frame, text="Stop backend", command=stop_backend).grid(row=2, column=1, sticky="w", padx=(8, 0), pady=(10, 0))
    root.after(500, refresh_backend_status)

    frontend_frame = ttk.LabelFrame(services_tab, text="Frontend", padding=12)
    frontend_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 12))
    frontend_frame.columnconfigure(1, weight=1)
    _add_helper_label(frontend_frame, "Runs the Studio web UI with the Vite dev server.", row=0, columnspan=4, wraplength=300)

    fe_status_var = tk.StringVar(value="Checking...")
    ttk.Label(frontend_frame, text="Status").grid(row=1, column=0, sticky="w", padx=(0, 8))
    ttk.Label(frontend_frame, textvariable=fe_status_var).grid(row=1, column=1, sticky="w")

    def refresh_frontend_status():
        fe_status_var.set("Running" if frontend_status() else "Stopped")

    def start_frontend():
        if procs["frontend"] is not None:
            messagebox.showinfo("Frontend", "Frontend already started from this launcher.")
            refresh_frontend_status()
            return
        if frontend_status():
            refresh_frontend_status()
            return
        if not (FRONTEND_DIR / "package.json").exists():
            messagebox.showerror("Frontend", f"Frontend dir not found: {FRONTEND_DIR}")
            return
        try:
            stderr_file = tempfile.NamedTemporaryFile(mode="w+", suffix=".log", delete=False)
            fe_stderr_path = stderr_file.name
            stderr_file.close()
            fe_stderr_handle = open(fe_stderr_path, "w")
            procs["frontend"] = subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=FRONTEND_DIR,
                stdout=subprocess.DEVNULL,
                stderr=fe_stderr_handle,
                text=True,
            )
            fe_status_var.set("Starting...")

            def check_frontend_started(attempt=0):
                if frontend_status():
                    fe_status_var.set("Running")
                    return
                p = procs["frontend"]
                if p is not None and p.poll() is not None:
                    procs["frontend"] = None
                    fe_status_var.set("Stopped")
                    err = ""
                    try:
                        with open(fe_stderr_path, "r", errors="replace") as f:
                            err = f.read().strip()
                    except Exception:
                        pass
                    log_dir = Path.home() / ".tensi_trossen_studio"
                    log_dir.mkdir(parents=True, exist_ok=True)
                    full_log = log_dir / "frontend_stderr.log"
                    try:
                        with open(full_log, "w", errors="replace") as f:
                            f.write(err or "(no stderr output)")
                    except Exception:
                        full_log = None
                    try:
                        os.unlink(fe_stderr_path)
                    except Exception:
                        pass
                    rc = p.returncode
                    msg = f"Frontend process exited (code {rc})."
                    if full_log:
                        msg += f"\n\nFull log saved to:\n{full_log}"
                    if err:
                        msg += "\n\nLast output:\n" + "\n".join(err.splitlines()[-30:])
                    else:
                        msg += "\n\nRun in a terminal: cd frontend && npm run dev"
                    try:
                        _show_copyable_error(root, "Frontend error", msg, str(full_log) if full_log else None)
                    except Exception:
                        messagebox.showerror("Frontend", msg)
                    return
                if attempt < 12:
                    root.after(1500, lambda: check_frontend_started(attempt + 1))
                else:
                    refresh_frontend_status()

            root.after(2000, lambda: check_frontend_started(0))
        except FileNotFoundError:
            messagebox.showerror("Frontend", "npm not found. Install Node.js and run from repo root.")
        except Exception as e:
            messagebox.showerror("Frontend", str(e))

    def stop_frontend():
        if procs["frontend"] is not None:
            _terminate_process(procs["frontend"], timeout=5)
            procs["frontend"] = None
        fe_status_var.set("Stopped")

    def open_frontend_browser():
        url = f"http://127.0.0.1:{FRONTEND_PORT}"
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            messagebox.showinfo("Frontend", f"Open in browser: {url}")

    ttk.Button(frontend_frame, text="Start frontend", command=start_frontend).grid(row=2, column=0, sticky="w", pady=(10, 0))
    ttk.Button(frontend_frame, text="Stop frontend", command=stop_frontend).grid(row=2, column=1, sticky="w", padx=(8, 0), pady=(10, 0))
    ttk.Button(frontend_frame, text="Open frontend", command=open_frontend_browser).grid(row=2, column=2, sticky="w", padx=(8, 0), pady=(10, 0))
    root.after(600, refresh_frontend_status)

    services_footer = ttk.LabelFrame(services_tab, text="Studio access", padding=12)
    services_footer.grid(row=1, column=0, columnspan=2, sticky="ew")
    services_footer.columnconfigure(0, weight=1)
    _add_helper_label(
        services_footer,
        f"Open the frontend in your browser once it is running at http://127.0.0.1:{FRONTEND_PORT}.",
        row=0,
        wraplength=720,
    )
    ttk.Button(services_footer, text="Open Studio in browser", command=open_frontend_browser).grid(row=1, column=0, sticky="w")

    # --- Network tab ---
    pc1_frame = ttk.LabelFrame(network_tab, text="PC1 network", padding=12)
    pc1_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 12))
    pc1_frame.columnconfigure(1, weight=1)

    pc1_wifi_var = tk.StringVar(value=config.get("pc1_wifi_ip", ""))
    _add_form_row(pc1_frame, 0, "PC1 WiFi IP (192.168.2.x)", pc1_wifi_var)
    pc1_eth_var = tk.StringVar(value=config.get("pc1_ethernet_ip", ""))
    _add_form_row(pc1_frame, 1, "PC1 Ethernet IP (192.168.1.x)", pc1_eth_var)
    follower_ip_var = tk.StringVar(value=config.get("follower_ip", "192.168.1.5"))
    _add_form_row(pc1_frame, 2, "Follower IP (192.168.1.x) - robot", follower_ip_var)

    pc2_frame = ttk.LabelFrame(network_tab, text="PC2 network", padding=12)
    pc2_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 12))
    pc2_frame.columnconfigure(1, weight=1)

    pc2_wifi_var = tk.StringVar(value=config.get("pc2_wifi_ip", "192.168.2.138"))
    _add_form_row(pc2_frame, 0, "PC2 WiFi IP (192.168.2.x)", pc2_wifi_var)
    pc2_eth_var = tk.StringVar(value=config.get("pc2_ethernet_ip", "192.168.1.200"))
    _add_form_row(pc2_frame, 1, "PC2 Ethernet IP (192.168.1.x)", pc2_eth_var)
    leader_ip_var = tk.StringVar(value=config.get("leader_ip", "192.168.1.2"))
    _add_form_row(pc2_frame, 2, "Leader IP (192.168.1.x) - robot", leader_ip_var)
    pc2_ssh_user_var = tk.StringVar(value=config.get("pc2_ssh_user", ""))
    _add_form_row(pc2_frame, 3, "SSH user (for Setup PC2)", pc2_ssh_user_var)

    def save_ips():
        c = load_launcher_config()
        c["pc1_wifi_ip"] = pc1_wifi_var.get().strip()
        c["pc1_ethernet_ip"] = pc1_eth_var.get().strip()
        c["follower_ip"] = follower_ip_var.get().strip()
        c["pc2_wifi_ip"] = pc2_wifi_var.get().strip()
        c["pc2_ethernet_ip"] = pc2_eth_var.get().strip()
        c["leader_ip"] = leader_ip_var.get().strip()
        c["pc2_ssh_user"] = pc2_ssh_user_var.get().strip()
        save_launcher_config(c)
        messagebox.showinfo("Saved", "IPs and SSH user saved to launcher config.")

    network_actions = ttk.Frame(network_tab)
    network_actions.grid(row=1, column=0, columnspan=2, sticky="ew")
    ttk.Button(network_actions, text="Save IPs", command=save_ips).grid(row=0, column=0, sticky="w")
    ttk.Label(
        network_actions,
        text="Launcher network values are saved to ~/.tensi_trossen_studio/launcher.json.",
        wraplength=720,
        justify=tk.LEFT,
    ).grid(row=1, column=0, sticky="w", pady=(6, 0))

    # --- Tools tab ---
    pc2_setup_frame = ttk.LabelFrame(tools_tab, text="PC2 leader setup", padding=12)
    pc2_setup_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
    pc2_setup_frame.columnconfigure(1, weight=1)
    _add_helper_label(
        pc2_setup_frame,
        "Copy leader_service.py to PC2, start the service, and verify the connection. SSH keys are required (ssh-copy-id).",
        row=0,
        columnspan=2,
        wraplength=720,
    )
    pc2_setup_status_var = tk.StringVar(value="")
    pc2_setup_btn = ttk.Button(pc2_setup_frame, text="Setup PC2 and start leader")

    def do_pc2_setup():
        pc2_wifi = pc2_wifi_var.get().strip()
        leader_ip = leader_ip_var.get().strip()
        ssh_user = pc2_ssh_user_var.get().strip() or "hadi"
        pc2_setup_btn.configure(state=tk.DISABLED)
        pc2_setup_status_var.set("Setting up PC2...")

        def run():
            ok, msg = run_pc2_leader_setup(pc2_wifi, leader_ip, ssh_user)

            def show_result():
                pc2_setup_btn.configure(state=tk.NORMAL)
                if ok:
                    pc2_setup_status_var.set("Last run: Success")
                    messagebox.showinfo("PC2 Leader Setup", msg)
                else:
                    pc2_setup_status_var.set("Last run: Failed")
                    try:
                        _show_copyable_error(root, "PC2 Leader Setup failed", msg)
                    except Exception:
                        messagebox.showerror("PC2 Leader Setup failed", msg)

            try:
                root.after(0, show_result)
            except Exception:
                pc2_setup_btn.configure(state=tk.NORMAL)
                pc2_setup_status_var.set("Last run: Error")

        import threading
        threading.Thread(target=run, daemon=True).start()

    pc2_setup_btn.configure(command=do_pc2_setup)
    pc2_setup_btn.grid(row=1, column=0, sticky="w")
    ttk.Label(pc2_setup_frame, textvariable=pc2_setup_status_var).grid(row=1, column=1, sticky="w", padx=(12, 0))

    usb_scan_frame = ttk.LabelFrame(tools_tab, text="USB cameras", padding=12)
    usb_scan_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
    usb_scan_frame.columnconfigure(0, weight=1)
    _add_helper_label(
        usb_scan_frame,
        "Find the device index for the operator view camera in Studio Settings.",
        row=0,
        wraplength=320,
    )

    def show_usb_scan():
        devices = scan_usb_video_devices()
        win = tk.Toplevel(root)
        win.title("USB video devices")
        win.geometry("640x360")
        win.minsize(480, 280)
        win.transient(root)
        win.columnconfigure(0, weight=1)
        win.rowconfigure(0, weight=1)
        f = ttk.Frame(win, padding=10)
        f.grid(row=0, column=0, sticky="nsew")
        f.columnconfigure(0, weight=1)
        f.rowconfigure(1, weight=1)
        ttk.Label(
            f,
            text="Use the index below in Studio Settings -> Operator view camera -> Device index.",
            wraplength=600,
            justify=tk.LEFT,
        ).grid(row=0, column=0, sticky="w")
        text_frame = ttk.Frame(f)
        text_frame.grid(row=1, column=0, sticky="nsew", pady=(6, 8))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL)
        text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=("TkFixedFont", 10),
            state=tk.DISABLED,
            cursor="arrow",
            height=12,
            yscrollcommand=scrollbar.set,
        )
        text.grid(row=0, column=0, sticky="nsew")
        scrollbar.configure(command=text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        if not devices:
            msg = "No /dev/video* devices found (Linux only)."
        else:
            msg = "\n".join(f"Index {d['index']}: {d['path']} - {d['name']}" for d in devices)
        text.configure(state=tk.NORMAL)
        text.insert(tk.END, msg)
        text.configure(state=tk.DISABLED)

        def copy_usb_list():
            root.clipboard_clear()
            root.clipboard_append(msg)
            try:
                root.update()
            except Exception:
                pass

        button_row = ttk.Frame(f)
        button_row.grid(row=2, column=0, sticky="w")
        ttk.Button(button_row, text="Copy to clipboard", command=copy_usb_list).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(button_row, text="Close", command=win.destroy).pack(side=tk.LEFT)

    ttk.Button(usb_scan_frame, text="Scan USB cameras", command=show_usb_scan).grid(row=1, column=0, sticky="w")

    studio_tools_frame = ttk.LabelFrame(tools_tab, text="Studio and shutdown", padding=12)
    studio_tools_frame.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
    studio_tools_frame.columnconfigure(0, weight=1)

    def open_studio():
        url = f"http://127.0.0.1:{FRONTEND_PORT}"
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            messagebox.showinfo("Studio", f"Open in browser: {url}")

    _add_helper_label(
        studio_tools_frame,
        f"Open Studio in your browser at http://127.0.0.1:{FRONTEND_PORT}.",
        row=0,
        wraplength=320,
    )
    ttk.Button(studio_tools_frame, text="Open Studio in browser", command=open_studio).grid(row=1, column=0, sticky="w")

    shutdown_frame = ttk.Frame(studio_tools_frame)
    shutdown_frame.grid(row=2, column=0, sticky="ew", pady=(14, 0))
    shutdown_status_var = tk.StringVar(value="")

    def shutdown_all_and_close():
        if not messagebox.askyesno(
            "Stop All & Close",
            "Stop the active Studio process, stop the PC2 leader service, stop frontend/backend, and close the launcher?",
        ):
            return

        shutdown_btn.configure(state=tk.DISABLED)
        shutdown_status_var.set("Stopping Studio...")

        def run_shutdown():
            warnings = []

            if backend_status():
                ok, out = _post_request(f"http://127.0.0.1:{BACKEND_PORT}/api/process/stop", timeout=20)
                if not ok:
                    warnings.append(f"Could not stop active Studio process gracefully: {out}")

                ok, out = _post_request(f"http://127.0.0.1:{BACKEND_PORT}/api/leader-service/stop", timeout=10)
                if not ok:
                    warnings.append(f"Could not stop PC2 leader service via backend: {out}")
            else:
                cfg = load_launcher_config()
                pc2_wifi = cfg.get("pc2_wifi_ip", "").strip()
                ssh_user = cfg.get("pc2_ssh_user", "").strip()
                if pc2_wifi:
                    ok, out = stop_remote_leader_service(pc2_wifi, ssh_user)
                    if not ok:
                        warnings.append(f"Could not stop PC2 leader service directly: {out}")

            if procs["frontend"] is not None:
                _terminate_process(procs["frontend"], timeout=5)
                procs["frontend"] = None
            if procs["backend"] is not None:
                _terminate_process(procs["backend"], timeout=5)
                procs["backend"] = None
            _kill_tcp_port(BACKEND_PORT)

            def finish():
                fe_status_var.set("Stopped")
                be_status_var.set("Stopped")
                shutdown_status_var.set("Stopped")
                if warnings:
                    try:
                        _show_copyable_error(root, "Shutdown warnings", "\n\n".join(warnings))
                    except Exception:
                        messagebox.showwarning("Shutdown warnings", "\n\n".join(warnings))
                root.destroy()

            root.after(0, finish)

        import threading
        threading.Thread(target=run_shutdown, daemon=True).start()

    shutdown_btn = ttk.Button(shutdown_frame, text="Stop All & Close", command=shutdown_all_and_close)
    shutdown_btn.grid(row=0, column=0, sticky="w")
    ttk.Label(
        shutdown_frame,
        text="Gracefully stop local services and the PC2 leader service before closing the launcher.",
        wraplength=320,
        justify=tk.LEFT,
    ).grid(row=1, column=0, sticky="w", pady=(6, 4))
    ttk.Label(shutdown_frame, textvariable=shutdown_status_var).grid(row=2, column=0, sticky="w")

    def poll_status():
        refresh_backend_status()
        refresh_frontend_status()
        root.after(3000, poll_status)

    root.after(3000, poll_status)

    def on_closing():
        if procs["backend"] or procs["frontend"] or backend_status() or frontend_status():
            if messagebox.askokcancel(
                "Quit",
                "Studio services may still be running.\n\nUse 'Stop All & Close' for graceful shutdown, or press OK to close only the launcher.",
            ):
                root.destroy()
        else:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    return {
        "procs": procs,
        "be_status_var": be_status_var,
        "fe_status_var": fe_status_var,
        "pc2_setup_status_var": pc2_setup_status_var,
        "shutdown_status_var": shutdown_status_var,
        "notebook": notebook,
    }


def run_tk():
    try:
        import tkinter as tk
    except ImportError:
        print("tkinter is required. On Debian/Ubuntu: sudo apt install python3-tk")
        sys.exit(1)

    root = tk.Tk()
    build_launcher_ui(root)
    root.mainloop()


if __name__ == "__main__":
    run_tk()
