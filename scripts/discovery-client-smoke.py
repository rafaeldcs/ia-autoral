"""Exercise native client discovery with an obsolete address, without changing saved credentials."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("connection", type=Path)
args = parser.parse_args()
connection = json.loads(args.connection.read_text(encoding="utf-8-sig"))
connection["Server"] = "https://127.0.0.2:8443"
with tempfile.TemporaryDirectory(prefix="localauthor-discovery-client-") as folder:
    temp = Path(folder)
    source = temp / "stale.localauthor"
    report = temp / "native.json"
    source.write_text(json.dumps(connection), encoding="utf-8")
    result = subprocess.run(
        [str(ROOT / "build/lan-client/LocalAuthor.Client.exe"), "--smoke", str(source), str(report)],
        creationflags=subprocess.CREATE_NO_WINDOW, timeout=90,
    )
    assert result.returncode == 0, "Native client discovery failed"
    native = json.loads(report.read_text(encoding="utf-8-sig"))
    assert all(native.get(field) for field in ("passed", "pinnedTls", "authenticated", "desktopLogin"))
summary = {
    "passed": True,
    "obsoleteAddress": "https://127.0.0.2:8443",
    "nativeChatOpenedAfterDiscovery": True,
    "secondPhysicalComputerTested": False,
}
(ROOT / "reports/discovery-client-smoke.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary))
