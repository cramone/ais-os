import os
import httpx
from typing import Any

ADO_ORG = os.getenv("AZURE_DEVOPS_ORG", "")
ADO_PROJECT = os.getenv("AZURE_DEVOPS_PROJECT", "")
ADO_PAT = os.getenv("AZURE_DEVOPS_PAT", "")


def update_work_item_state(item_id: int, state: str) -> dict[str, Any]:
    if not all([ADO_ORG, ADO_PROJECT, ADO_PAT]):
        raise EnvironmentError("ADO_ORG, ADO_PROJECT, ADO_PAT env vars required")
    url = (
        f"https://dev.azure.com/{ADO_ORG}/{ADO_PROJECT}/_apis/wit/workitems/{item_id}"
        "?api-version=7.1"
    )
    body = [{"op": "add", "path": "/fields/System.State", "value": state}]
    r = httpx.patch(
        url, json=body,
        headers={"Content-Type": "application/json-patch+json"},
        auth=("", ADO_PAT), timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    return {
        "id": data["id"],
        "state": data["fields"].get("System.State", state),
    }
