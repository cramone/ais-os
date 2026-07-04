import os
import subprocess
from typing import Any

import httpx

# Set on Cortex only (.env). Points at scripts/claudia-bridge/server.py, a
# host-side (non-Docker) HTTP wrapper around the bare-metal `claudia` CLI.
# Unset on Windows dev, where Hermes still runs as a Docker container named
# 'hermes' — see _send_via_docker below.
CLAUDIA_BRIDGE_URL = os.getenv("CLAUDIA_BRIDGE_URL", "")

# 2026-07-04: repointed from the retired Windows Docker Hermes container
# (`docker exec hermes ...`) to Claudia's bare-metal profile on cortex, reached
# over Tailscale SSH. `cortex` resolves via Tailscale MagicDNS (same alias used
# throughout the setup guide / migration plan — confirm `ssh chase@cortex` works
# non-interactively, i.e. key-based auth with no passphrase prompt, from whatever
# host runs the Tower).
CORTEX_HOST = "chase@cortex"


def send_to_claudia(message: str) -> dict[str, Any]:
    if CLAUDIA_BRIDGE_URL:
        return _send_via_bridge(message)
    return _send_via_docker(message)


def _send_via_bridge(message: str) -> dict[str, Any]:
    """Cortex: bare-metal Claudia via the host-side HTTP bridge."""
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
    """Windows dev: Hermes runs as a Docker container named 'hermes'."""
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
