#!/usr/bin/env python
"""Single-command launcher for AIS-OS Control Tower.

Usage:
    python tower/start.py
    python tower/start.py --port 9000
"""
import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="AIS-OS Control Tower")
    parser.add_argument("--port", type=int, default=8765, help="Port (default: 8765)")
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
