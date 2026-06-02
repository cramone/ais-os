#!/usr/bin/env python3
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

HERMES_HOME = Path.home() / ".hermes"
TOKEN_PATH = HERMES_HOME / "google_token.json"
MEMORY_PATH = HERMES_HOME / "memories" / "USER.md"

DASHBOARD_DIR = "/mnt/c/Users/chase/OneDrive/Magiq/AIS-OS/dashboards/claudia"
AIOS_ROOT = Path("/mnt/c/Users/chase/OneDrive/Magiq/AIS-OS")
DEVOPS_SCRIPT = AIOS_ROOT / "scripts" / "devops_summary.py"
PRIORITIES_PATH = AIOS_ROOT / "context" / "priorities.md"

_brief_cache: dict = {"generated_at": None, "content": None}

app = FastAPI(title="Claudia Dashboard API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def serve_dashboard():
    return FileResponse(DASHBOARD_DIR + "/index.html")

def get_google_creds():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    if not TOKEN_PATH.exists():
        raise HTTPException(status_code=503, detail="Google not authenticated")
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_PATH.write_text(creds.to_json())
    return creds

def get_service(name, version):
    from googleapiclient.discovery import build
    return build(name, version, credentials=get_google_creds())

@app.get("/api/status")
def get_status():
    try:
        r = subprocess.run(["systemctl","--user","is-active","hermes-gateway"], capture_output=True, text=True, timeout=5)
        gw = r.stdout.strip() == "active"
    except Exception:
        gw = False
    return {"gateway": gw, "google": TOKEN_PATH.exists(), "memory_seeded": MEMORY_PATH.exists()}

@app.get("/api/calendar/today")
def get_today_events():
    svc = get_service("calendar","v3")
    tz_offset = timedelta(hours=10)
    now_utc = datetime.now(timezone.utc)
    local_now = now_utc + tz_offset
    start = local_now.replace(hour=0,minute=0,second=0,microsecond=0)
    end = start + timedelta(days=1)
    time_min = (start - tz_offset).strftime("%Y-%m-%dT%H:%M:%SZ")
    time_max = (end - tz_offset).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = svc.events().list(calendarId="primary",timeMin=time_min,timeMax=time_max,singleEvents=True,orderBy="startTime",maxResults=20).execute()
    events = []
    for e in result.get("items",[]):
        start_str = e.get("start",{}).get("dateTime",e.get("start",{}).get("date",""))
        end_str = e.get("end",{}).get("dateTime",e.get("end",{}).get("date",""))
        if "T" in start_str:
            dt = datetime.fromisoformat(start_str.replace("Z","+00:00"))
            time_label = (dt + tz_offset).strftime("%H:%M")
        else:
            time_label = "all day"
        duration_min = None
        if "T" in start_str and "T" in end_str:
            s = datetime.fromisoformat(start_str.replace("Z","+00:00"))
            en = datetime.fromisoformat(end_str.replace("Z","+00:00"))
            duration_min = int((en-s).total_seconds()/60)
        conf = e.get("conferenceData",{})
        meet_link = next((ep.get("uri","") for ep in conf.get("entryPoints",[]) if ep.get("entryPointType")=="video"),"")
        events.append({"id":e.get("id"),"title":e.get("summary","(no title)"),"time":time_label,"duration_min":duration_min,"location":e.get("location",""),"meet_link":meet_link})
    return {"events":events,"date":local_now.strftime("%A, %-d %B %Y")}

@app.get("/api/calendar/week")
def get_week_events():
    svc = get_service("calendar","v3")
    tz_offset = timedelta(hours=10)
    now_utc = datetime.now(timezone.utc)
    local_now = now_utc + tz_offset
    start = local_now.replace(hour=0,minute=0,second=0,microsecond=0)
    end = start + timedelta(days=7)
    time_min = (start - tz_offset).strftime("%Y-%m-%dT%H:%M:%SZ")
    time_max = (end - tz_offset).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = svc.events().list(calendarId="primary",timeMin=time_min,timeMax=time_max,singleEvents=True,orderBy="startTime",maxResults=50).execute()
    events = []
    for e in result.get("items",[]):
        start_str = e.get("start",{}).get("dateTime",e.get("start",{}).get("date",""))
        if "T" in start_str:
            dt = datetime.fromisoformat(start_str.replace("Z","+00:00"))
            local_dt = dt + tz_offset
            day_label = local_dt.strftime("%a %-d %b")
            time_label = local_dt.strftime("%H:%M")
        else:
            day_label = start_str
            time_label = "all day"
        events.append({"title":e.get("summary","(no title)"),"day":day_label,"time":time_label})
    return {"events":events}

@app.get("/api/gmail/unread")
def get_unread_emails():
    svc = get_service("gmail","v1")
    result = svc.users().messages().list(userId="me",q="is:unread in:inbox",maxResults=8).execute()
    messages = []
    for msg in result.get("messages",[]):
        m = svc.users().messages().get(userId="me",id=msg["id"],format="metadata",metadataHeaders=["From","Subject","Date"]).execute()
        headers = {h["name"]:h["value"] for h in m.get("payload",{}).get("headers",[])}
        raw_from = headers.get("From","")
        sender = raw_from.split("<")[0].strip().strip('"') or raw_from
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(headers.get("Date",""))
            now = datetime.now(timezone.utc)
            delta = now - dt.astimezone(timezone.utc)
            time_label = dt.astimezone().strftime("%H:%M") if delta.days==0 else ("Yesterday" if delta.days==1 else dt.strftime("%-d %b"))
        except Exception:
            time_label = ""
        messages.append({"id":msg["id"],"sender":sender[:30],"subject":headers.get("Subject","(no subject)")[:80],"time":time_label,"unread":True})
    return {"messages":messages,"total_unread":result.get("resultSizeEstimate",len(messages))}

@app.get("/api/memory")
def get_memory():
    if not MEMORY_PATH.exists():
        return {"content":"","tags":[]}
    content = MEMORY_PATH.read_text()
    tags = [p for p in ["C#","DDD","CQRS","event sourcing","DynamoDB","SQS","Lambda","CloudWatch","Azure DevOps","FastEndpoints","MediatR","Docker","Rider","microservices","Git","Postman"] if p.lower() in content.lower()]
    return {"content":content,"tags":tags}

@app.get("/api/gateway/status")
def get_gateway_status():
    try:
        r = subprocess.run(["systemctl","--user","is-active","hermes-gateway"],capture_output=True,text=True,timeout=5)
        active = r.stdout.strip() == "active"
    except Exception:
        active = False
    return {"gateway_active":active,"services":[
        {"name":"Telegram","detail":"claudia_chase_bot","online":active},
        {"name":"Google Calendar","detail":"ramonechase@gmail.com","online":TOKEN_PATH.exists()},
        {"name":"Gmail","detail":"ramonechase@gmail.com","online":TOKEN_PATH.exists()},
        {"name":"Discord","detail":"no token configured","online":False},
    ]}

@app.get("/api/brief")
def get_brief(force: bool = False):
    """Generate or return cached daily brief. Caches for 1 hour unless force=true."""
    now_utc = datetime.now(timezone.utc)
    tz_offset = timedelta(hours=10)
    local_now = now_utc + tz_offset

    # Return cache if fresh (< 1 hour) and not forced
    if not force and _brief_cache["generated_at"]:
        age = (now_utc - _brief_cache["generated_at"]).total_seconds()
        if age < 3600:
            return {
                "content": _brief_cache["content"],
                "generated_at": _brief_cache["generated_at"].strftime("%H:%M"),
                "cached": True
            }

    sections = []

    # --- Date header ---
    sections.append(f"# Morning Brief — {local_now.strftime('%A, %-d %B %Y')}")

    # --- Q2 Priorities ---
    try:
        priorities = PRIORITIES_PATH.read_text().strip()
        sections.append(f"## Q2 Priorities\n{priorities}")
    except Exception:
        sections.append("## Q2 Priorities\n_(priorities.md not found)_")

    # --- Calendar today ---
    try:
        cal_data = get_today_events()
        events = cal_data.get("events", [])
        if events:
            ev_lines = "\n".join(
                f"- {e['time']} — {e['title']}" +
                (f" ({e['duration_min']}min)" if e.get('duration_min') else "") +
                (" 📹" if e.get('meet_link') else "")
                for e in events
            )
            sections.append(f"## Today's Calendar ({len(events)} events)\n{ev_lines}")
        else:
            sections.append("## Today's Calendar\nClear — no events today.")
    except Exception as ex:
        sections.append(f"## Today's Calendar\n_(unavailable: {ex})_")

    # --- DevOps summary ---
    try:
        if DEVOPS_SCRIPT.exists():
            env_file = AIOS_ROOT / ".env"
            env_vars = {}
            if env_file.exists():
                for line in env_file.read_text().splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        env_vars[k.strip()] = v.strip()
            import os
            run_env = {**os.environ, **env_vars}
            result = subprocess.run(
                ["python3", str(DEVOPS_SCRIPT)],
                capture_output=True, text=True, timeout=30, env=run_env
            )
            if result.returncode == 0 and result.stdout.strip():
                # Trim to essential lines only (first 30 lines)
                devops_lines = result.stdout.strip().splitlines()[:30]
                sections.append(f"## Azure DevOps\n```\n{chr(10).join(devops_lines)}\n```")
            else:
                err = result.stderr.strip().splitlines()[0] if result.stderr.strip() else "no output"
                sections.append(f"## Azure DevOps\n_(script error: {err})_")
        else:
            sections.append("## Azure DevOps\n_(devops_summary.py not found)_")
    except subprocess.TimeoutExpired:
        sections.append("## Azure DevOps\n_(timed out — check network/PAT)_")
    except Exception as ex:
        sections.append(f"## Azure DevOps\n_(unavailable: {ex})_")

    content = "\n\n".join(sections)
    _brief_cache["generated_at"] = now_utc
    _brief_cache["content"] = content

    return {
        "content": content,
        "generated_at": local_now.strftime("%H:%M"),
        "cached": False
    }

@app.get("/api/devops")
def get_devops():
    """Return structured DevOps work items as JSON for card rendering."""
    import os, urllib.request, urllib.parse, base64, json as _json

    env_file = AIOS_ROOT / ".env"
    env_vars = {}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env_vars[k.strip()] = v.strip()

    PAT = env_vars.get("AZURE_DEVOPS_PAT") or os.environ.get("AZURE_DEVOPS_PAT")
    ORG = env_vars.get("AZURE_DEVOPS_ORG") or os.environ.get("AZURE_DEVOPS_ORG")
    PROJECT = env_vars.get("AZURE_DEVOPS_PROJECT") or os.environ.get("AZURE_DEVOPS_PROJECT")

    if not all([PAT, ORG, PROJECT]):
        raise HTTPException(status_code=503, detail="Azure DevOps credentials not configured")

    token = base64.b64encode(f":{PAT}".encode()).decode()
    headers = {"Authorization": f"Basic {token}", "Content-Type": "application/json"}
    base_url = f"https://dev.azure.com/{ORG}/{PROJECT}/_apis"

    def api_post(path, body):
        data = _json.dumps(body).encode()
        req = urllib.request.Request(f"{base_url}{path}", data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as r:
            return _json.loads(r.read())

    def api_get(path):
        req = urllib.request.Request(f"{base_url}{path}", headers=headers)
        with urllib.request.urlopen(req, timeout=15) as r:
            return _json.loads(r.read())

    # WIQL — active items assigned to me
    wiql_result = api_post("/wit/wiql?api-version=7.1", {
        "query": "SELECT [System.Id] FROM workitems WHERE [System.TeamProject] = @project AND [System.AssignedTo] = @me AND [System.State] NOT IN ('Done','Closed','Removed') ORDER BY [System.ChangedDate] DESC"
    })
    item_ids = [i["id"] for i in wiql_result.get("workItems", [])]

    if not item_ids:
        return {"items": [], "total": 0, "by_state": {}, "code_review": []}

    # Fetch item details in chunks
    fields = ["System.Id","System.Title","System.WorkItemType","System.State","System.IterationPath","Microsoft.VSTS.Common.Priority","System.Tags"]
    items = []
    for i in range(0, len(item_ids), 200):
        chunk = item_ids[i:i+200]
        id_str = ",".join(str(x) for x in chunk)
        field_str = ",".join(fields)
        data = api_get(f"/wit/workitems?ids={id_str}&fields={field_str}&api-version=7.1")
        items.extend(data.get("value", []))

    # Structure output
    by_state = {}
    code_review = []
    result_items = []

    for item in items:
        f = item["fields"]
        wit = f.get("System.WorkItemType", "Task")
        state = f.get("System.State", "Unknown")
        title = f.get("System.Title", "")
        priority = f.get("Microsoft.VSTS.Common.Priority")
        item_id = f["System.Id"]

        structured = {
            "id": item_id,
            "title": title[:80],
            "type": wit,
            "state": state,
            "priority": priority,
            "iteration": f.get("System.IterationPath", "").split("\\")[-1],
        }
        result_items.append(structured)

        if state not in by_state:
            by_state[state] = []
        by_state[state].append(structured)

        if state == "Code Review":
            code_review.append(structured)

    return {
        "items": result_items,
        "total": len(result_items),
        "by_state": by_state,
        "code_review": code_review,
        "state_counts": {s: len(v) for s, v in by_state.items()},
    }

@app.get("/api/projects")
def get_projects():
    """Return list of projects from AIS-OS projects/ folder with brief content."""
    projects_dir = AIOS_ROOT / "projects"
    projects = []
    if not projects_dir.exists():
        return {"projects": []}

    for project_dir in sorted(projects_dir.iterdir()):
        if not project_dir.is_dir():
            continue
        brief_path = project_dir / "brief.md"
        decisions_path = project_dir / "decisions"
        log_path = AIOS_ROOT / "decisions" / "log.md"

        brief_text = brief_path.read_text(encoding="utf-8") if brief_path.exists() else ""

        # Parse key fields from brief
        name = project_dir.name.replace("-", " ").title()
        status = "active"
        stack = ""
        owner = ""

        for line in brief_text.splitlines():
            if line.startswith("# "):
                name = line[2:].replace("Project Brief —", "").replace("Project Brief -", "").strip()
            if "stack" in line.lower() and "|" in line:
                pass
            if line.lower().startswith("**owner"):
                owner = line.split(":", 1)[-1].strip().strip("*")

        # Get decisions relevant to this project from log.md
        decisions = []
        if log_path.exists():
            content = log_path.read_text(encoding="utf-8")
            entries = content.split("## ")
            for entry in entries[1:]:
                lines = entry.strip().splitlines()
                if lines:
                    decisions.append({"title": lines[0].strip(), "body": "\n".join(lines[1:6]).strip()})

        projects.append({
            "id": project_dir.name,
            "name": name,
            "status": status,
            "owner": owner or "Chase Ramone",
            "brief_preview": brief_text[:600] if brief_text else "",
            "has_brief": brief_path.exists(),
            "decisions_count": len(decisions),
            "decisions": decisions[:10],
        })

    return {"projects": projects}
