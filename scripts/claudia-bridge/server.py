#!/usr/bin/env python3
"""
Minimal host-side HTTP bridge: containerized Control Tower -> bare-metal
Claudia (Hermes profile) on Cortex.

Stdlib only — no venv/pip install needed on the host. Runs OUTSIDE Docker as
its own systemd --user service, bound to 127.0.0.1. The Tower container
reaches it via host.docker.internal:8901 (same extra_hosts:host-gateway
pattern already used for Open WebUI -> Ollama in ~/stack/docker-compose.yml).

SECURITY: keep this bound to 127.0.0.1 only. It shells out with --yolo.
Never put it on the tailnet or public entrypoint.

VERIFY BEFORE ENABLING: the exact non-interactive CLI invocation for
Claudia. The Cortex setup guide shows `claudia gateway install/start` as a
top-level command, implying a `claudia` shell entrypoint exists (confirm
with `which claudia` / `type claudia`) as a scoped wrapper around
`hermes --profile claudia`. If that's wrong, CLAUDIA_CMD below is the only
line that needs to change — everything else (HTTP handling, systemd unit,
Tower's client) stays the same.
"""
import json
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST, PORT = "127.0.0.1", 8901
CLAUDIA_CMD = ["claudia", "chat", "-q"]   # <-- verify on Cortex, see note above
TIMEOUT_S = 120


class Handler(BaseHTTPRequestHandler):
    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"ok": True})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/chat":
            self._json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._json(400, {"error": "invalid JSON"})
            return
        message = (body.get("message") or "").strip()
        if not message:
            self._json(400, {"error": "message required"})
            return
        try:
            result = subprocess.run(
                [*CLAUDIA_CMD, message, "--yolo"],
                capture_output=True, text=True, timeout=TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            self._json(504, {"ok": False, "response": f"Timed out waiting for Claudia ({TIMEOUT_S}s)"})
            return
        except FileNotFoundError:
            self._json(500, {"ok": False, "response": f"'{CLAUDIA_CMD[0]}' not found on PATH — check CLAUDIA_CMD"})
            return
        if result.returncode != 0:
            self._json(500, {"ok": False, "response": result.stderr.strip() or "claudia returned an error"})
            return
        self._json(200, {"ok": True, "response": result.stdout.strip() or "(no output)"})

    def log_message(self, fmt, *args):
        pass  # keep the systemd journal quiet; add real logging if this needs debugging later


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"claudia-bridge listening on {HOST}:{PORT}")
    server.serve_forever()
