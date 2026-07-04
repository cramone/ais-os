import subprocess
from typing import Any

# 2026-07-04: repointed from the retired Windows Docker Hermes container
# (`docker exec hermes ...`) to Claudia's bare-metal profile on cortex, reached
# over Tailscale SSH. `cortex` resolves via Tailscale MagicDNS (same alias used
# throughout the setup guide / migration plan — confirm `ssh chase@cortex` works
# non-interactively, i.e. key-based auth with no passphrase prompt, from whatever
# host runs the Tower).
CORTEX_HOST = "chase@cortex"


def send_to_claudia(message: str) -> dict[str, Any]:
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
