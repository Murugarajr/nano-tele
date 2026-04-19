import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
NANOBOT_PORT = os.environ.get("NANOBOT_PORT", "18790")

nanobot_bin = shutil.which("nanobot")
if nanobot_bin:
    cmd = [nanobot_bin, "gateway", "--config", str(CONFIG_PATH)]
else:
    cmd = [sys.executable, "-m", "nanobot", "gateway", "--config", str(CONFIG_PATH)]

port = os.environ.get("PORT")
cmd.extend(["--port", NANOBOT_PORT])


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"ok\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def start_health_server(bind_port: str) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("0.0.0.0", int(bind_port)), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server

print(f"Starting nanobot from {ROOT}", flush=True)
print(f"Using config: {CONFIG_PATH}", flush=True)
print(f"Launch command: {' '.join(cmd)}", flush=True)
if port:
    print(f"Starting health server on platform PORT={port}", flush=True)
    print(f"Running nanobot gateway on NANOBOT_PORT={NANOBOT_PORT}", flush=True)
    health_server = start_health_server(port)
else:
    health_server = None

try:
    subprocess.run(cmd, check=True, cwd=str(ROOT))
finally:
    if health_server is not None:
        health_server.shutdown()
