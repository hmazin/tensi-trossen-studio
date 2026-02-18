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


def load_launcher_config():
    """Load launcher config (IPs, etc.)."""
    default = {
        "pc1_wifi_ip": "",
        "pc1_ethernet_ip": "",
        "pc2_wifi_ip": "192.168.2.138",
        "pc2_ethernet_ip": "192.168.1.2",
    }
    if not LAUNCHER_CONFIG_PATH.exists():
        return default
    try:
        data = json.loads(LAUNCHER_CONFIG_PATH.read_text())
        return {**default, **data}
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


def _show_copyable_error(parent, title, message, log_path=None):
    """Show error in a window with selectable text and Copy / Open log buttons."""
    import tkinter as tk
    from tkinter import ttk

    win = tk.Toplevel(parent)
    win.title(title)
    win.geometry("620x380")
    win.transient(parent)
    win.grab_set()

    f = ttk.Frame(win, padding=10)
    f.pack(fill=tk.BOTH, expand=True)
    text = tk.Text(f, wrap=tk.WORD, font=("TkDefaultFont", 10), state=tk.DISABLED, cursor="arrow")
    text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
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
    bf.pack(fill=tk.X)
    ttk.Button(bf, text="Copy to clipboard", command=copy_all).pack(side=tk.LEFT, padx=(0, 8))
    if log_path:
        ttk.Button(bf, text="Open log file", command=open_log).pack(side=tk.LEFT, padx=(0, 8))
    ttk.Button(bf, text="OK", command=win.destroy).pack(side=tk.LEFT)
    win.wait_window(win)


def run_tk():
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox, font
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

    root = tk.Tk()
    root.title("TENSI Trossen Studio — Launcher (PC1)")
    root.minsize(420, 420)
    root.geometry("480x520")

    main = ttk.Frame(root, padding=12)
    main.pack(fill=tk.BOTH, expand=True)

    # --- 1. Backend ---
    ttk.Label(main, text="1. Backend", font=("", 11, "bold")).pack(anchor=tk.W)
    be_frame = ttk.Frame(main)
    be_frame.pack(fill=tk.X, pady=(4, 12))
    be_status_var = tk.StringVar(value="Checking…")
    ttk.Label(be_frame, textvariable=be_status_var, width=24).pack(side=tk.LEFT, padx=8)

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
            be_status_var.set("Starting…")

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
            procs["backend"].terminate()
            try:
                procs["backend"].wait(timeout=5)
            except subprocess.TimeoutExpired:
                procs["backend"].kill()
            procs["backend"] = None
        try:
            subprocess.run(["fuser", "-k", f"{BACKEND_PORT}/tcp"], capture_output=True, timeout=3)
        except Exception:
            pass
        be_status_var.set("Stopped")

    ttk.Button(be_frame, text="Start backend", command=start_backend).pack(side=tk.LEFT, padx=4)
    ttk.Button(be_frame, text="Stop backend", command=stop_backend).pack(side=tk.LEFT)
    root.after(500, refresh_backend_status)

    def poll_status():
        refresh_backend_status()
        refresh_frontend_status()
        root.after(3000, poll_status)
    root.after(3000, poll_status)

    # --- 2. Frontend ---
    ttk.Label(main, text="2. Frontend", font=("", 11, "bold")).pack(anchor=tk.W, pady=(8, 0))
    fe_frame = ttk.Frame(main)
    fe_frame.pack(fill=tk.X, pady=(4, 12))
    fe_status_var = tk.StringVar(value="Checking…")
    ttk.Label(fe_frame, textvariable=fe_status_var, width=24).pack(side=tk.LEFT, padx=8)

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
            fe_status_var.set("Starting…")

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
            procs["frontend"].terminate()
            try:
                procs["frontend"].wait(timeout=5)
            except subprocess.TimeoutExpired:
                procs["frontend"].kill()
            procs["frontend"] = None
        fe_status_var.set("Stopped")

    ttk.Button(fe_frame, text="Start frontend", command=start_frontend).pack(side=tk.LEFT, padx=4)
    ttk.Button(fe_frame, text="Stop frontend", command=stop_frontend).pack(side=tk.LEFT)
    root.after(600, refresh_frontend_status)

    # --- 3. PC1 IPs ---
    ttk.Label(main, text="3. PC1 IPs", font=("", 11, "bold")).pack(anchor=tk.W, pady=(8, 0))
    p1_frame = ttk.Frame(main)
    p1_frame.pack(fill=tk.X, pady=(4, 12))
    ttk.Label(p1_frame, text="WiFi (192.168.2.x):", width=20, anchor=tk.W).pack(anchor=tk.W)
    pc1_wifi_var = tk.StringVar(value=config.get("pc1_wifi_ip", ""))
    ttk.Entry(p1_frame, textvariable=pc1_wifi_var, width=18).pack(anchor=tk.W, pady=2)
    ttk.Label(p1_frame, text="Ethernet (192.168.1.x):", width=20, anchor=tk.W).pack(anchor=tk.W, pady=(6, 0))
    pc1_eth_var = tk.StringVar(value=config.get("pc1_ethernet_ip", ""))
    ttk.Entry(p1_frame, textvariable=pc1_eth_var, width=18).pack(anchor=tk.W, pady=2)

    # --- 4. PC2 IPs ---
    ttk.Label(main, text="4. PC2 IPs", font=("", 11, "bold")).pack(anchor=tk.W, pady=(8, 0))
    p2_frame = ttk.Frame(main)
    p2_frame.pack(fill=tk.X, pady=(4, 12))
    ttk.Label(p2_frame, text="WiFi (192.168.2.x):", width=20, anchor=tk.W).pack(anchor=tk.W)
    pc2_wifi_var = tk.StringVar(value=config.get("pc2_wifi_ip", "192.168.2.138"))
    ttk.Entry(p2_frame, textvariable=pc2_wifi_var, width=18).pack(anchor=tk.W, pady=2)
    ttk.Label(p2_frame, text="Ethernet (192.168.1.x):", width=20, anchor=tk.W).pack(anchor=tk.W, pady=(6, 0))
    pc2_eth_var = tk.StringVar(value=config.get("pc2_ethernet_ip", "192.168.1.2"))
    ttk.Entry(p2_frame, textvariable=pc2_eth_var, width=18).pack(anchor=tk.W, pady=2)

    def save_ips():
        c = load_launcher_config()
        c["pc1_wifi_ip"] = pc1_wifi_var.get().strip()
        c["pc1_ethernet_ip"] = pc1_eth_var.get().strip()
        c["pc2_wifi_ip"] = pc2_wifi_var.get().strip()
        c["pc2_ethernet_ip"] = pc2_eth_var.get().strip()
        save_launcher_config(c)
        messagebox.showinfo("Saved", "IPs saved to launcher config.")

    ttk.Button(main, text="Save IPs", command=save_ips).pack(anchor=tk.W, pady=(8, 0))

    # Open Studio link
    def open_studio():
        url = f"http://127.0.0.1:{FRONTEND_PORT}"
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            messagebox.showinfo("Studio", f"Open in browser: {url}")

    ttk.Separator(main, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=16)
    ttk.Button(main, text="Open Studio in browser", command=open_studio).pack(anchor=tk.W)
    ttk.Label(main, text=f"  (http://127.0.0.1:{FRONTEND_PORT})", foreground="gray").pack(anchor=tk.W)

    def on_closing():
        if procs["backend"] or procs["frontend"]:
            if messagebox.askokcancel("Quit", "Backend/Frontend started by this launcher will keep running. Stop them from this window first if you want."):
                root.destroy()
        else:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    run_tk()
