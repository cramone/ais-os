"""Push an interrupt to ADO as a Task via the ADO REST API."""
import os
import httpx
from typing import Any

ADO_ORG = os.getenv("ADO_ORG", "")
ADO_PROJECT = os.getenv("ADO_PROJECT", "")
ADO_PAT = os.getenv("ADO_PAT", "")


def push_to_ado(interrupt: dict[str, Any]) -> dict[str, Any]:
    """Create an ADO Task for the given interrupt. Returns {"adoItemId": int}."""
    if not all([ADO_ORG, ADO_PROJECT, ADO_PAT]):
        raise EnvironmentError("ADO_ORG, ADO_PROJECT, ADO_PAT env vars required")

    comments = "\n".join(
        f"[{e['timestamp']}] {e.get('author', '')}: {e['text']}"
        for e in interrupt.get("activity", [])
        if e["type"] == "comment"
    )
    url = (
        f"https://dev.azure.com/{ADO_ORG}/{ADO_PROJECT}/_apis/wit/workitems/$Task"
        "?api-version=7.1"
    )
    body = [
        {"op": "add", "path": "/fields/System.Title",
         "value": f"[Interrupt] {interrupt['title']}"},
        {"op": "add", "path": "/fields/System.Description",
         "value": f"Source: {interrupt['source']}. Captured: {interrupt['capturedAt']}.\n\n{comments}"},
        {"op": "add", "path": "/fields/System.AreaPath", "value": ADO_PROJECT},
    ]
    if interrupt.get("dueDate"):
        body.append({"op": "add", "path": "/fields/Microsoft.VSTS.Scheduling.DueDate",
                     "value": interrupt["dueDate"]})

    r = httpx.patch(url, json=body,
                    headers={"Content-Type": "application/json-patch+json"},
                    auth=("", ADO_PAT), timeout=15)
    r.raise_for_status()
    return {"adoItemId": r.json()["id"]}
