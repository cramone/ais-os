import subprocess
from typing import Any


def send_to_claudia(message: str) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["docker", "exec", "hermes", "hermes", "chat", "-q", message, "--yolo"],
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
        return {"ok": False, "response": "Docker not found — is it running?"}
    except Exception as e:
        return {"ok": False, "response": str(e)}
