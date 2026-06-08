#!/usr/bin/env python
"""Single-command launcher for AIS-OS Control Tower.

Usage:
    python tower/start.py
    python tower/start.py --port 9000
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    _env = Path(__file__).parent.parent / ".env"
    if _env.exists():
        load_dotenv(_env, override=False)
except ImportError:
    pass

_default_port = int(os.getenv("TOWER_PORT", "8765"))


def main() -> None:
    parser = argparse.ArgumentParser(description="AIS-OS Control Tower")
    parser.add_argument("--port", type=int, default=_default_port, help="Port (default from TOWER_PORT)")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")
    args = parser.parse_args()

    here = Path(__file__).parent.parent  # AIS-OS root
    cmd = [
        sys.executable, "-m", "uvicorn",
        "tower.server:app",
        "--host", "0.0.0.0",
        "--port", str(args.port),
    ]
    if not args.no_reload:
        cmd.append("--reload")

    print(f"Starting AIS-OS Control Tower on http://localhost:{args.port}")
    subprocess.run(cmd, cwd=str(here))


if __name__ == "__main__":
    main()
