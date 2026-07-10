import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from AIS-OS root before reading any env vars
_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    load_dotenv(_env_file, override=False)

# Resolve AIS-OS root — self-locate from this file; env override wins.
# config.py lives at <root>/tower/config.py, so parent.parent == root.
AIOS_ROOT = Path(os.getenv("AIOS_ROOT") or Path(__file__).resolve().parent.parent)
TOWER_DIR = AIOS_ROOT / "tower"
PROJECTS_DIR = AIOS_ROOT / "projects"
DECISIONS_LOG = AIOS_ROOT / "decisions" / "log.md"
ADO_SCRIPT = AIOS_ROOT / "scripts" / "devops_summary.py"
INTERRUPTS_FILE = TOWER_DIR / "data" / "interrupts.json"
TODOS_DATA_DIR = TOWER_DIR / "data" / "todos"


def todos_file(slug: str) -> Path:
    """Per-project todo store (same JSON schema as interrupts)."""
    return TODOS_DATA_DIR / f"{slug}.json"


try:
    PORT = int(os.getenv("TOWER_PORT", "8765"))
except (ValueError, TypeError):
    PORT = 8765

# Shared access token. When set, /api requests must send `Authorization: Bearer <token>`.
# Empty = open (localhost dev).
TOWER_TOKEN = os.getenv("TOWER_TOKEN", "")
