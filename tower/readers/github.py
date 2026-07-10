import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

_FIELDS = "number,title,repository,url,createdAt,isDraft,author"


def _gh(*args: str, timeout: int = 15) -> Any:
    result = subprocess.run(["gh"] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if result.returncode != 0:
        return None
    return json.loads(result.stdout or "null")


def _current_user() -> str:
    try:
        data = _gh("api", "user", "--jq", ".login")
        return data.strip('"') if isinstance(data, str) else ""
    except Exception:
        return ""


def _last_activity(repo: str, number: int, me: str) -> dict[str, Any] | None:
    try:
        data = _gh("pr", "view", str(number), "--repo", repo, "--json", "comments,reviews")
        if not data:
            return None

        candidates = []

        for c in data.get("comments", []):
            login = c.get("author", {}).get("login", "")
            if login and login != me:
                candidates.append({"author": login, "body": c.get("body", ""), "date": c.get("createdAt", ""), "type": "comment"})

        for r in data.get("reviews", []):
            login = r.get("author", {}).get("login", "")
            state = r.get("state", "")
            if login and login != me and state != "PENDING":
                candidates.append({"author": login, "body": r.get("body", ""), "date": r.get("submittedAt", ""), "type": "review", "state": state})

        if not candidates:
            return None
        return max(candidates, key=lambda x: x["date"])
    except Exception:
        return None


_THREADS_QUERY = """
query($owner:String!,$name:String!,$number:Int!){
  repository(owner:$owner,name:$name){
    pullRequest(number:$number){
      reviewThreads(first:100){
        nodes{
          isResolved isOutdated
          comments(first:1){nodes{author{login} bodyText createdAt path}}
        }
      }
    }
  }
}
"""


def _review_threads(repo: str, number: int) -> dict[str, Any]:
    """Unresolved review-thread count + newest unresolved comment for a PR."""
    if "/" not in repo:
        return {"unresolved": 0, "lastUnresolved": None}
    owner, name = repo.split("/", 1)
    try:
        data = _gh(
            "api", "graphql",
            "-f", f"query={_THREADS_QUERY}",
            "-f", f"owner={owner}", "-f", f"name={name}",
            "-F", f"number={number}",
            timeout=20,
        )
        nodes = (data or {}).get("data", {}).get("repository", {}).get("pullRequest", {}).get("reviewThreads", {}).get("nodes", [])
    except Exception:
        return {"unresolved": 0, "lastUnresolved": None}

    open_threads = []
    for t in nodes:
        if t.get("isResolved"):
            continue
        comments = t.get("comments", {}).get("nodes", [])
        c = comments[0] if comments else {}
        body = (c.get("bodyText", "") or "").strip()
        if len(body) > 140:
            body = body[:137] + "..."
        open_threads.append({
            "author": (c.get("author") or {}).get("login", ""),
            "body": body,
            "date": c.get("createdAt", ""),
            "path": c.get("path", ""),
            "outdated": t.get("isOutdated", False),
        })
    last = max(open_threads, key=lambda x: x["date"]) if open_threads else None
    return {"unresolved": len(open_threads), "lastUnresolved": last}


def _enrich(prs: list[dict[str, Any]], me: str) -> list[dict[str, Any]]:
    if not prs:
        return prs

    def fetch(pr: dict) -> tuple[int, dict | None, dict]:
        activity = _last_activity(pr["repo"], pr["number"], me) if me else None
        threads = _review_threads(pr["repo"], pr["number"])
        return pr["number"], activity, threads

    activity_map: dict[int, dict | None] = {}
    threads_map: dict[int, dict] = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetch, pr): pr["number"] for pr in prs}
        for f in as_completed(futures):
            num, activity, threads = f.result()
            activity_map[num] = activity
            threads_map[num] = threads

    for pr in prs:
        pr["lastActivity"] = activity_map.get(pr["number"])
        t = threads_map.get(pr["number"], {})
        pr["unresolvedThreads"] = t.get("unresolved", 0)
        pr["lastUnresolved"] = t.get("lastUnresolved")
    return prs


def _search_prs(extra_args: list[str]) -> list[dict[str, Any]]:
    try:
        result = subprocess.run(
            ["gh", "search", "prs", "--state", "open", "--json", _FIELDS, "--limit", "50"] + extra_args,
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
        )
        if result.returncode != 0:
            return []
        prs = json.loads(result.stdout or "[]")
        return [
            {
                "number": pr["number"],
                "title": pr["title"],
                "repo": pr.get("repository", {}).get("nameWithOwner", ""),
                "url": pr.get("url", ""),
                "createdAt": pr.get("createdAt", ""),
                "reviewDecision": "",
                "isDraft": pr.get("isDraft", False),
                "author": pr.get("author", {}).get("login", "") if isinstance(pr.get("author"), dict) else str(pr.get("author", "")),
                "lastActivity": None,
            }
            for pr in prs
        ]
    except Exception:
        return []


_me: str = ""


def _get_me() -> str:
    global _me
    if not _me:
        _me = _current_user()
    return _me


def read_github_prs() -> list[dict[str, Any]]:
    return _enrich(_search_prs(["--author", "@me"]), _get_me())


def read_github_review_requested() -> list[dict[str, Any]]:
    return _enrich(_search_prs(["--review-requested", "@me"]), _get_me())
