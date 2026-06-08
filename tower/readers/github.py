import json
import subprocess
from typing import Any

_FIELDS = "number,title,headRepository,url,createdAt,reviewDecision,isDraft"


def _fetch_prs(extra_args: list[str]) -> list[dict[str, Any]]:
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--state", "open", "--json", _FIELDS, "--limit", "50"] + extra_args,
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return []
        prs = json.loads(result.stdout or "[]")
        return [
            {
                "number": pr["number"],
                "title": pr["title"],
                "repo": pr.get("headRepository", {}).get("nameWithOwner", ""),
                "url": pr["url"],
                "createdAt": pr["createdAt"],
                "reviewDecision": pr.get("reviewDecision") or "",
                "isDraft": pr.get("isDraft", False),
            }
            for pr in prs
        ]
    except Exception:
        return []


def read_github_prs() -> list[dict[str, Any]]:
    return _fetch_prs(["--author", "@me"])


def read_github_review_requested() -> list[dict[str, Any]]:
    return _fetch_prs(["--review-requested", "@me"])
