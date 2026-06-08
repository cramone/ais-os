import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from AIS-OS root before reading any env vars
_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    load_dotenv(_env_file, override=False)

# Resolve AIS-OS root — env override for portability
AIOS_ROOT = Path(os.getenv("AIOS_ROOT", r"C:\Users\chase\OneDrive\Magiq\AIS-OS"))
_hermes_root = Path(os.getenv("HERMES", r"C:\Users\chase\.hermes"))
HERMES_DATA = _hermes_root / "data"
TOWER_DIR = AIOS_ROOT / "tower"
PROJECTS_DIR = AIOS_ROOT / "projects"
DECISIONS_LOG = AIOS_ROOT / "decisions" / "log.md"
ADO_SCRIPT = AIOS_ROOT / "scripts" / "devops_summary.py"
INTERRUPTS_FILE = TOWER_DIR / "data" / "interrupts.json"
ADO_PENDING = HERMES_DATA / "ado-pending.json"
ADHOC_NOTES = HERMES_DATA / "adhoc-notes.md"
HERMES_PROJECTS = HERMES_DATA / "projects"
try:
    PORT = int(os.getenv("TOWER_PORT", "8765"))
except (ValueError, TypeError):
    PORT = 8765
