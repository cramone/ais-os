import subprocess
import json
import sys
import time
from typing import Any
from tower import config

_TTL = 300  # seconds
_cache: dict[str, Any] | None = None
_cache_ts: float = 0.0

_xp_cache: dict[str, Any] | None = None
_xp_cache_ts: float = 0.0


def invalidate_cache() -> None:
    global _cache, _cache_ts, _xp_cache, _xp_cache_ts
    _cache = None
    _cache_ts = 0.0
    _xp_cache = None
    _xp_cache_ts = 0.0


def read_ado_cross_project() -> dict[str, Any]:
    """My open work items across ALL ADO projects, grouped by project."""
    global _xp_cache, _xp_cache_ts
    if _xp_cache is not None and (time.monotonic() - _xp_cache_ts) < _TTL:
        return _xp_cache
    try:
        raw = _run_script("--cross-project", "--comments", "--json")
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            result = {"projects": [], "error": "bad JSON", "raw_text": raw}
    except Exception as e:
        result = {"projects": [], "error": str(e)}
    _xp_cache = result
    _xp_cache_ts = time.monotonic()
    return _xp_cache


def read_ado_sprint() -> dict[str, Any]:
    global _cache, _cache_ts
    if _cache is not None and (time.monotonic() - _cache_ts) < _TTL:
        return _cache
    try:
        raw = _run_script()
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            result = {"items": [], "raw_text": raw}
    except Exception as e:
        result = {"items": [], "error": str(e)}
    _cache = result
    _cache_ts = time.monotonic()
    return _cache


def _run_script(*args: str) -> str:
    if not config.ADO_SCRIPT.exists():
        raise FileNotFoundError(f"devops_summary.py not found at {config.ADO_SCRIPT}")
    script_args = list(args) if args else ["--sprint", "--all", "--json"]
    result = subprocess.run(
        [sys.executable, str(config.ADO_SCRIPT), *script_args],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or "script exited non-zero")
    return result.stdout
