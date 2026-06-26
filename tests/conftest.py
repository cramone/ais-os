import pytest
from pathlib import Path
import json

@pytest.fixture
def tmp_aios(tmp_path):
    """Minimal AIS-OS directory structure for testing."""
    projects = tmp_path / "projects"
    projects.mkdir()
    mm = projects / "magiq-media"
    mm.mkdir()
    (mm / "MEMORY.md").write_text(
        "# magiq-media\n**Status**: Active delivery\n**Priority**: High\n"
    )
    ma = projects / "magiq-auth"
    ma.mkdir()
    (ma / "MEMORY.md").write_text(
        "# magiq-auth\n**Status**: Draft\n**Priority**: High\n"
    )
    decisions = tmp_path / "decisions"
    decisions.mkdir()
    (decisions / "log.md").write_text(
        "## 2026-06-01 - Some decision\n*Project: magiq-media*\n\n## 2026-05-30 - Another decision\n*Project: aios*\n"
    )
    return tmp_path

@pytest.fixture
def tmp_interrupts(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    f = data / "interrupts.json"
    f.write_text(json.dumps([
        {
            "id": "test-id-1",
            "title": "Fix export bug",
            "source": "Support",
            "dueDate": "2026-06-01",
            "priority": "urgent",
            "status": "new",
            "tags": [],
            "adoItemId": None,
            "capturedAt": "2026-05-29T08:00:00Z",
            "updatedAt": "2026-05-29T08:00:00Z",
            "activity": []
        }
    ]))
    return f
