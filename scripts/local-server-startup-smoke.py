"""Cold-start the native client with no connection file; use only isolated QA data."""
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
from localauthor.application import Application
from localauthor.config import Settings
from localauthor.server import create_server

CLIENT = ROOT / "build/lan-client/LocalAuthor.Client.exe"
GATEWAY = ROOT / "build/lan-server/LocalAuthor.Lan.exe"
checks = []


def check(name, condition):
    assert condition, name
    checks.append(name)


def run(*args, success=True):
    value = subprocess.run([str(a) for a in args], capture_output=True,
                           creationflags=subprocess.CREATE_NO_WINDOW, timeout=100)
    assert (value.returncode == 0) == success, "Unexpected native command result"


def ps_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


with tempfile.TemporaryDirectory(prefix="LocalAuthor local startup ") as temporary:
    base = Path(temporary)
    local = base / "local-data"
    home = base / "client-data"
    lan = local / "LocalAuthor/lan"
    runtime = local / "LocalAuthor/lan-runtime"
    runtime.mkdir(parents=True)
    settings = Settings.load(base / "backend")
    app = Application(settings)
    app.start()
    backend = create_server(app, ROOT / "ui", port=0)
    thread = threading.Thread(target=backend.serve_forever, daemon=True)
    thread.start()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    run(GATEWAY, "init", "--data", lan, "--home", settings.home, "--bind", "127.0.0.1",
        "--prefix", "32", "--port", port, "--backend-port", backend.server_port, "--discover")
    # Use a separate discovery port so a running real server is unaffected.
    config_path = lan / "server.json"
    config = json.loads(config_path.read_text())
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        config["DiscoveryPort"] = sock.getsockname()[1]
    config_path.write_text(json.dumps(config))
    (lan / "runtime.json").write_text(json.dumps({"Gateway": str(GATEWAY)}))
    launches = base / "launches.txt"
    gateway_pid = base / "gateway.pid"
    # Deliberately slow startup proves the app waits instead of displaying an import prompt.
    (runtime / "Start-Server.ps1").write_text(
        "param([switch]$Supervise)\n$ErrorActionPreference='Stop'\n"
        f"Add-Content -LiteralPath {ps_literal(launches)} -Value started\n"
        "Start-Sleep -Seconds 3\n"
        f"$p=Start-Process -FilePath {ps_literal(GATEWAY)} "
        f"-ArgumentList @('serve','--data',{ps_literal(chr(34)+str(lan)+chr(34))}) "
        "-WindowStyle Hidden -PassThru\n"
        f"$p.Id | Set-Content -LiteralPath {ps_literal(gateway_pid)}\n", encoding="utf-8-sig")
    report = base / "result.json"

    def prepare(success=True, data=local, client_home=home):
        run(CLIENT, "--local-startup-smoke", data, client_home, report, success=success)
        return json.loads(report.read_text())

    try:
        check("Unconfigured client does not invent a server or enroll", not prepare(False, base / "absent", base / "unpaired")["passed"])
        native = ROOT / "reports/local-server-desktop.json"
        native.parent.mkdir(exist_ok=True)
        run(CLIENT, "--startup", "--smoke-local-server", local, home, native)
        check("Cold startup with no imported file opens authenticated native chat", json.loads(native.read_text())["desktopLogin"])
        shell = json.loads(native.read_text())
        check("Native header is absent from the connected workspace", shell["nativeHeaderAbsent"])
        check("Local administration lives inside Tools", shell["desktopSettingsInTools"])
        check("Bridge rejects foreign origins and commands that mutate data", shell["bridgeRestricted"])
        check("Malformed and unsupported WebView messages are ignored", shell["bridgeIgnoresInvalidMessages"])
        check("Tools opens the native connection and update menu", shell["desktopSettingsMenuOpened"])
        devices_file = lan / "devices.json"
        devices = json.loads(devices_file.read_text())
        check("One local device enrolled with least privilege", len(devices) == 1 and devices[0]["Role"] == "client")
        check("Enrollment leaves no plaintext connection file", not list(lan.glob("*.localauthor")))
        encrypted = (home / "connection.bin").read_bytes()
        check("Saved connection is encrypted instead of JSON", b"AccessKey" not in encrypted and b"https://" not in encrypted)
        check("Local connection uses loopback", prepare()["server"] == f"https://127.0.0.1:{port}")
        check("Repeated startup preserves enrollment and avoids duplicate server", len(json.loads(devices_file.read_text())) == 1 and len(launches.read_text().splitlines()) == 1)
        # A separately paired remote server must be preserved, even on a server machine.
        config_path.write_text(json.dumps({**config, "CertificateSha256": "0" * 64}))
        before = (home / "connection.bin").read_bytes()
        check("Different saved server remains selected without replacement", not prepare()["local"] and before == (home / "connection.bin").read_bytes())
        config_path.write_text(json.dumps(config))
        devices[0]["Enabled"] = False
        devices_file.write_text(json.dumps(devices))
        check("Revocation fails closed without minting another key", prepare(False)["error"] == "AuthenticationException" and len(json.loads(devices_file.read_text())) == 1)
        devices[0]["Enabled"] = True
        devices_file.write_text(json.dumps(devices))
        (home / "connection.bin").write_bytes(b"corrupt encrypted connection")
        check("Corrupt saved credentials are not silently overwritten", prepare(False)["error"] == "CryptographicException" and (home / "connection.bin").read_bytes() == b"corrupt encrypted connection")
        (home / "connection.bin").write_bytes(encrypted)
        script = runtime / "Start-Server.ps1"
        script.rename(runtime / "Start-Server.saved")
        check("Incomplete server installation produces an explicit failure", prepare(False)["error"] == "FileNotFoundException")
    finally:
        if gateway_pid.exists():
            pid = int(gateway_pid.read_text(encoding="utf-8-sig").strip())
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True,
                           creationflags=subprocess.CREATE_NO_WINDOW, timeout=20)
        backend.shutdown()
        backend.server_close()
        thread.join()
        app.close()

summary = {"passed": len(checks), "checks": checks, "rebootTested": False, "temporaryDataOnly": True}
(ROOT / "reports/local-server-startup-smoke.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary))
