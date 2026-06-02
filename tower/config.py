import os
from pathlib import Path

# Resolve AIS-OS root — env override for portability
AIOS_ROOT = Path(os.getenv("AIOS_ROOT", r"C:\Users\chase\OneDrive\Magiq\AIS-OS"))
HERMES_DATA = Path(os.getenv("HERMES_DATA", r"C:\Users\chase\.hermes\data"))
TOWER_DIR = AIOS_ROOT / "tower"
PROJECTS_DIR = AIOS_ROOT / "projects"
DECISIONS_LOG = AIOS_ROOT / "decisions" / "log.md"
ADO_SCRIPT = AIOS_ROOT / "references" / "devops_summary.py"
INTERRUPTS_FILE = TOWER_DIR / "data" / "interrupts.json"
ADO_PENDING = HERMES_DATA / "ado-pending.json"
ADHOC_NOTES = HERMES_DATA / "adhoc-notes.md"
HERMES_PROJECTS = HERMES_DATA / "projects"
PORT = int(os.getenv("TOWER_PORT", "8765"))
