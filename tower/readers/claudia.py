import os
import subprocess
from typing import Any

import httpx

# Set on Cortex only (.env). Points at scripts/claudia-bridge/server.py, a
# host-side (non-Docker) HTTP wrapper around the bare-metal `claudia` CLI.
# This is the ONLY working path from inside Cortex's containerized Tower —
# the container has no SSH client/keys (Dockerfile only adds git/gh), so
# _send_via_docker's SSH command below can't actually run from there.
#
# Single-.env wrinkle (2026-07-05): Windows/WSL and Cortex now share one
# .env. If CLAUDIA_BRIDGE_URL is set there, a Windows/WSL dev instance of
# Tower (`python tower/start.py`, not in Docker) will also try the bridge —
# and host.docker.internal doesn't resolve outside a container, so "Ask
# Claudia" specifically fails there even though everything else works fine.
CLAUDIA_BRIDGE_URL = os.getenv("CLAUDIA_BRIDGE_URL", "")

# Fallback when CLAUDIA_BRIDGE_URL is unset — i.e. Windows/WSL dev today, or
# a future Cortex path if a way to reach the bridge without it is ever added.
# NOTE: despite the function name below, this has NOT called `docker exec`
# since 2026-07-04 — it was repointed from the retired Windows Docker Hermes
# container to SSH straight into Claudia's bare-metal profile on cortex.
# `cortex` resolves via Tailscale MagicDNS (same alias used throughout the
# setup guide / migration plan — confirm `ssh chase@cortex` works
# non-interactively, i.e. key-based auth with no passphrase prompt, from
# whatever host runs this).
CORTEX_HOST = "chase@cortex"


def send_to_claudia(message: str) -> dict[str, Any]:
    if CLAUDIA_BRIDGE_URL:
        return _send_via_bridge(message)
    return _send_via_docker(message)


def _send_via_bridge(message: str) -> dict[str, Any]:
    """Cortex, containerized Tower: bare-metal Claudia via the host-side HTTP bridge."""
    try:
        r = httpx.post(
            f"{CLAUDIA_BRIDGE_URL.rstrip('/')}/chat",
            json={"message": message},
            timeout=125,
        )
        data = r.json()
        if r.status_code != 200:
            return {
                "ok": False,
                "response": data.get("response") or data.get("error") or "Claudia returned an error.",
            }
        return data
    except httpx.TimeoutException:
        return {"ok": False, "response": "Timed out waiting for Claudia (bridge)."}
    except Exception as e:
        return {"ok": False, "response": str(e)}


def _send_via_docker(message: str) -> dict[str, Any]:
    """Windows/WSL dev fallback (name kept for history — this is an SSH call,
    not `docker exec`; see the CORTEX_HOST comment above for why)."""
    try:
        result = subprocess.run(
            ["ssh", CORTEX_HOST, "claudia", "chat", "-q", message, "--yolo"],
            capture_output=True, text=True, timeout=120,
        )
        output = result.stdout.strip()
        if result.returncode != 0:
            err = result.stderr.strip()
            return {"ok": False, "response": err or "Claudia returned an error.", "raw": err}
        return {"ok": True, "response": output or "(no output)"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "response": "Timed out waiting for Claudia (120s)."}
    except FileNotFoundError:
        return {"ok": False, "response": "ssh not found on PATH."}
    except Exception as e:
        return {"ok": False, "response": str(e)}
