import subprocess
import json
import sys
from typing import Any
from tower import config


def read_ado_sprint() -> dict[str, Any]:
    """Run devops_summary.py and return parsed sprint data."""
    try:
        raw = _run_script()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Script outputs plain text — wrap it
            return {"items": [], "raw_text": raw}
    except Exception as e:
        return {"items": [], "error": str(e)}


def _run_script() -> str:
    if not config.ADO_SCRIPT.exists():
        raise FileNotFoundError(f"devops_summary.py not found at {config.ADO_SCRIPT}")
    result = subprocess.run(
        [sys.executable, str(config.ADO_SCRIPT)],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or "script exited non-zero")
    return result.stdout
