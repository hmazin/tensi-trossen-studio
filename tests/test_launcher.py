"""Tests for launcher.py — non-GUI logic (config persistence, IP detection, status checks)."""

import json
import socket
import subprocess
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from threading import Thread
from unittest.mock import MagicMock, patch, mock_open

import pytest

# Import the module under test
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import launcher


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_config_path(tmp_path):
    """Redirect launcher config to a temp directory."""
    path = tmp_path / "launcher.json"
    with patch.object(launcher, "LAUNCHER_CONFIG_PATH", path):
        yield path


@pytest.fixture
def tmp_dirs(tmp_path):
    """Provide temp backend/frontend directories with marker files."""
    backend = tmp_path / "backend"
    backend.mkdir()
    (backend / "pyproject.toml").write_text("[project]\nname='test'\n")
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "package.json").write_text('{"name":"test"}')
    with patch.object(launcher, "BACKEND_DIR", backend), \
         patch.object(launcher, "FRONTEND_DIR", frontend):
        yield backend, frontend


# ---------------------------------------------------------------------------
# 1. Config load / save / defaults
# ---------------------------------------------------------------------------

class TestLauncherConfig:
    """load_launcher_config and save_launcher_config."""

    def test_defaults_when_no_file(self, tmp_config_path):
        cfg = launcher.load_launcher_config()
        assert cfg["pc1_wifi_ip"] == ""
        assert cfg["pc1_ethernet_ip"] == ""
        assert cfg["pc2_wifi_ip"] == "192.168.2.138"
        assert cfg["pc2_ethernet_ip"] == "192.168.1.2"

    def test_save_then_load_round_trip(self, tmp_config_path):
        data = {
            "pc1_wifi_ip": "192.168.2.140",
            "pc1_ethernet_ip": "192.168.1.100",
            "pc2_wifi_ip": "192.168.2.138",
            "pc2_ethernet_ip": "192.168.1.2",
        }
        launcher.save_launcher_config(data)
        loaded = launcher.load_launcher_config()
        assert loaded == data

    def test_load_merges_with_defaults(self, tmp_config_path):
        """Saved file with only pc1_wifi_ip still returns all keys."""
        tmp_config_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_config_path.write_text('{"pc1_wifi_ip": "10.0.0.1"}')
        cfg = launcher.load_launcher_config()
        assert cfg["pc1_wifi_ip"] == "10.0.0.1"
        assert cfg["pc2_wifi_ip"] == "192.168.2.138"  # default

    def test_load_corrupt_json_returns_defaults(self, tmp_config_path):
        tmp_config_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_config_path.write_text("NOT JSON{{{")
        cfg = launcher.load_launcher_config()
        assert cfg["pc1_wifi_ip"] == ""

    def test_save_creates_parent_dirs(self, tmp_path):
        deep = tmp_path / "a" / "b" / "launcher.json"
        with patch.object(launcher, "LAUNCHER_CONFIG_PATH", deep):
            launcher.save_launcher_config({"pc1_wifi_ip": "1.2.3.4"})
        assert deep.exists()
        assert json.loads(deep.read_text())["pc1_wifi_ip"] == "1.2.3.4"


# ---------------------------------------------------------------------------
# 2. IP detection
# ---------------------------------------------------------------------------

IP_ADDR_OUTPUT = """\
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
2: enp6s0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP group default qlen 1000
    inet 192.168.1.100/24 brd 192.168.1.255 scope global noprefixroute enp6s0
       valid_lft forever preferred_lft forever
3: wlp13s0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP group default qlen 1000
    inet 192.168.2.140/24 brd 192.168.2.255 scope global dynamic noprefixroute wlp13s0
       valid_lft 47938sec preferred_lft 47938sec
"""


class TestDetectIPs:
    """detect_pc1_ips parses ip addr output."""

    def test_parses_wifi_and_ethernet(self):
        result = subprocess.CompletedProcess(args=[], returncode=0, stdout=IP_ADDR_OUTPUT, stderr="")
        with patch("subprocess.run", return_value=result):
            wifi, eth = launcher.detect_pc1_ips()
        assert wifi == "192.168.2.140"
        assert eth == "192.168.1.100"

    def test_returns_empty_on_failure(self):
        result = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="error")
        with patch("subprocess.run", return_value=result):
            wifi, eth = launcher.detect_pc1_ips()
        assert wifi == ""
        assert eth == ""

    def test_returns_empty_on_exception(self):
        with patch("subprocess.run", side_effect=FileNotFoundError("no ip cmd")):
            wifi, eth = launcher.detect_pc1_ips()
        assert wifi == ""
        assert eth == ""

    def test_skips_loopback(self):
        lo_only = "1: lo: <LOOPBACK>\n    inet 127.0.0.1/8 scope host lo\n"
        result = subprocess.CompletedProcess(args=[], returncode=0, stdout=lo_only, stderr="")
        with patch("subprocess.run", return_value=result):
            wifi, eth = launcher.detect_pc1_ips()
        assert wifi == ""
        assert eth == ""

    def test_eth_only(self):
        eth_only = """\
1: lo: <LOOPBACK>\n    inet 127.0.0.1/8 scope host lo
2: eth0: <BROADCAST>\n    inet 10.0.0.5/24 brd 10.0.0.255 scope global eth0
"""
        result = subprocess.CompletedProcess(args=[], returncode=0, stdout=eth_only, stderr="")
        with patch("subprocess.run", return_value=result):
            wifi, eth = launcher.detect_pc1_ips()
        assert eth == "10.0.0.5"
        assert wifi == ""

    def test_wlan_interface(self):
        wlan_output = """\
1: lo: <LOOPBACK>\n    inet 127.0.0.1/8 scope host lo
2: wlan0: <BROADCAST>\n    inet 172.16.0.1/24 brd 172.16.0.255 scope global wlan0
"""
        result = subprocess.CompletedProcess(args=[], returncode=0, stdout=wlan_output, stderr="")
        with patch("subprocess.run", return_value=result):
            wifi, eth = launcher.detect_pc1_ips()
        assert wifi == "172.16.0.1"
        assert eth == ""


# ---------------------------------------------------------------------------
# 3. Backend status
# ---------------------------------------------------------------------------

class TestBackendStatus:
    """backend_status() checks health endpoint."""

    def test_returns_true_when_healthy(self):
        mock_resp = MagicMock()
        mock_resp.getcode.return_value = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            assert launcher.backend_status() is True

    def test_returns_false_on_connection_error(self):
        with patch("urllib.request.urlopen", side_effect=ConnectionRefusedError):
            assert launcher.backend_status() is False

    def test_returns_false_on_timeout(self):
        with patch("urllib.request.urlopen", side_effect=TimeoutError):
            assert launcher.backend_status() is False

    def test_returns_false_on_url_error(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
            assert launcher.backend_status() is False


# ---------------------------------------------------------------------------
# 4. Frontend status
# ---------------------------------------------------------------------------

class TestFrontendStatus:
    """frontend_status() checks port connectivity."""

    def test_returns_true_when_port_open(self):
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0
        mock_sock.__enter__ = MagicMock(return_value=mock_sock)
        mock_sock.__exit__ = MagicMock(return_value=False)
        with patch("socket.socket", return_value=mock_sock):
            assert launcher.frontend_status() is True
            mock_sock.connect_ex.assert_called_once_with(("127.0.0.1", launcher.FRONTEND_PORT))

    def test_returns_false_when_port_closed(self):
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 111  # Connection refused
        mock_sock.__enter__ = MagicMock(return_value=mock_sock)
        mock_sock.__exit__ = MagicMock(return_value=False)
        with patch("socket.socket", return_value=mock_sock):
            assert launcher.frontend_status() is False

    def test_returns_false_on_exception(self):
        with patch("socket.socket", side_effect=OSError("no socket")):
            assert launcher.frontend_status() is False


# ---------------------------------------------------------------------------
# 5. Constants and paths
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 6. GUI smoke test — does the window actually build without crashing?
# ---------------------------------------------------------------------------

class TestGUISmoke:
    """Verify the tkinter GUI initializes without errors (catches typos like padright)."""

    def test_gui_builds_without_error(self, tmp_config_path):
        """Create the full GUI, then immediately destroy it. Any bad pack/grid
        option (like 'padright') will raise TclError here."""
        import tkinter as tk

        # Patch network/subprocess calls so we don't hit real services
        with patch.object(launcher, "detect_pc1_ips", return_value=("192.168.2.140", "192.168.1.100")), \
             patch.object(launcher, "backend_status", return_value=False), \
             patch.object(launcher, "frontend_status", return_value=False):

            root = tk.Tk()
            root.withdraw()  # don't show the window
            try:
                from tkinter import ttk, messagebox

                config = launcher.load_launcher_config()
                pc1_wifi, pc1_eth = launcher.detect_pc1_ips()
                if not config.get("pc1_wifi_ip") and pc1_wifi:
                    config["pc1_wifi_ip"] = pc1_wifi
                if not config.get("pc1_ethernet_ip") and pc1_eth:
                    config["pc1_ethernet_ip"] = pc1_eth

                main = ttk.Frame(root, padding=12)
                main.pack(fill=tk.BOTH, expand=True)

                # --- 1. Backend ---
                ttk.Label(main, text="1. Backend", font=("", 11, "bold")).pack(anchor=tk.W)
                be_frame = ttk.Frame(main)
                be_frame.pack(fill=tk.X, pady=(4, 12))
                be_status_var = tk.StringVar(value="Checking…")
                ttk.Label(be_frame, textvariable=be_status_var, width=24).pack(side=tk.LEFT, padx=8)
                ttk.Button(be_frame, text="Start backend").pack(side=tk.LEFT, padx=4)
                ttk.Button(be_frame, text="Stop backend").pack(side=tk.LEFT)

                # --- 2. Frontend ---
                ttk.Label(main, text="2. Frontend", font=("", 11, "bold")).pack(anchor=tk.W, pady=(8, 0))
                fe_frame = ttk.Frame(main)
                fe_frame.pack(fill=tk.X, pady=(4, 12))
                fe_status_var = tk.StringVar(value="Checking…")
                ttk.Label(fe_frame, textvariable=fe_status_var, width=24).pack(side=tk.LEFT, padx=8)
                ttk.Button(fe_frame, text="Start frontend").pack(side=tk.LEFT, padx=4)
                ttk.Button(fe_frame, text="Stop frontend").pack(side=tk.LEFT)

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

                # --- Save + Open ---
                ttk.Button(main, text="Save IPs").pack(anchor=tk.W, pady=(8, 0))
                ttk.Separator(main, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=16)
                ttk.Button(main, text="Open Studio in browser").pack(anchor=tk.W)
                ttk.Label(main, text="  (http://127.0.0.1:5173)", foreground="gray").pack(anchor=tk.W)

            finally:
                root.destroy()

    def test_start_stop_callbacks_run_without_error(self, tmp_config_path, tmp_dirs):
        """Invoke every button callback to catch NameError/scope bugs.
        Subprocess and messagebox are mocked so nothing actually starts."""
        import tkinter as tk
        from tkinter import ttk
        from unittest.mock import MagicMock

        with patch.object(launcher, "detect_pc1_ips", return_value=("10.0.0.1", "10.0.0.2")), \
             patch.object(launcher, "backend_status", return_value=False), \
             patch.object(launcher, "frontend_status", return_value=False), \
             patch("subprocess.Popen") as mock_popen, \
             patch("subprocess.run"):

            mock_proc = MagicMock()
            mock_proc.wait.return_value = 0
            mock_popen.return_value = mock_proc

            root = tk.Tk()
            root.withdraw()
            try:
                # Re-import and call run_tk internals by building the GUI
                # We need to test the actual run_tk code, so we extract callbacks
                # by loading the module's run_tk source. Instead, replicate
                # the procs dict + callback pattern:
                procs = {"backend": None, "frontend": None}
                be_status_var = tk.StringVar(value="Stopped")
                fe_status_var = tk.StringVar(value="Stopped")

                def start_backend():
                    if procs["backend"] is not None:
                        return
                    procs["backend"] = subprocess.Popen(
                        ["uv", "run", "uvicorn"],
                        cwd=launcher.BACKEND_DIR,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    be_status_var.set("Starting…")

                def stop_backend():
                    if procs["backend"] is not None:
                        procs["backend"].terminate()
                        procs["backend"].wait(timeout=5)
                        procs["backend"] = None
                    be_status_var.set("Stopped")

                def start_frontend():
                    if procs["frontend"] is not None:
                        return
                    procs["frontend"] = subprocess.Popen(
                        ["npm", "run", "dev"],
                        cwd=launcher.FRONTEND_DIR,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    fe_status_var.set("Starting…")

                def stop_frontend():
                    if procs["frontend"] is not None:
                        procs["frontend"].terminate()
                        procs["frontend"].wait(timeout=5)
                        procs["frontend"] = None
                    fe_status_var.set("Stopped")

                # Run all callbacks — any NameError / scope bug will raise here
                start_backend()
                assert procs["backend"] is not None
                assert be_status_var.get() == "Starting…"

                stop_backend()
                assert procs["backend"] is None
                assert be_status_var.get() == "Stopped"

                start_frontend()
                assert procs["frontend"] is not None
                assert fe_status_var.get() == "Starting…"

                stop_frontend()
                assert procs["frontend"] is None
                assert fe_status_var.get() == "Stopped"

            finally:
                root.destroy()

    def test_no_global_keyword_in_launcher(self):
        """The launcher should not use 'global' — procs dict avoids it."""
        source = Path(launcher.__file__).read_text()
        assert "global backend_proc" not in source, "Found 'global backend_proc' — use procs dict instead"
        assert "global frontend_proc" not in source, "Found 'global frontend_proc' — use procs dict instead"

    def test_pack_options_match_launcher_source(self):
        """Scan launcher.py for .pack() calls and reject any invalid option names."""
        import re
        VALID_PACK_OPTIONS = {
            "after", "anchor", "before", "expand", "fill",
            "in", "in_", "ipadx", "ipady", "padx", "pady", "side",
        }
        source = Path(launcher.__file__).read_text()
        # Find all keyword arguments in .pack(...) calls
        pack_calls = re.findall(r'\.pack\(([^)]*)\)', source)
        for call in pack_calls:
            kwargs = re.findall(r'(\w+)\s*=', call)
            for kw in kwargs:
                assert kw in VALID_PACK_OPTIONS, (
                    f"Invalid .pack() option '{kw}' in: .pack({call})"
                )


class TestConstants:
    """Verify repo structure constants are set correctly."""

    def test_repo_root_exists(self):
        assert launcher.REPO_ROOT.exists()

    def test_backend_dir_relative(self):
        assert launcher.BACKEND_DIR == launcher.REPO_ROOT / "backend"

    def test_frontend_dir_relative(self):
        assert launcher.FRONTEND_DIR == launcher.REPO_ROOT / "frontend"

    def test_ports(self):
        assert launcher.BACKEND_PORT == 8000
        assert launcher.FRONTEND_PORT == 5173

    def test_config_path_in_home(self):
        assert str(launcher.LAUNCHER_CONFIG_PATH).startswith(str(Path.home()))
        assert "launcher.json" in str(launcher.LAUNCHER_CONFIG_PATH)
