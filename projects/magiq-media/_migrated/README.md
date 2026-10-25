# Migrated to the repo — kept for rollback

These plans and reviews moved to `Sprbrk-Standard/mgq-magiq-media` → `docs/briefs/` as ado-flow briefs (2026-10-23, PR #200; MM-202 and MM-203 on 2026-10-25). The repo is now the source of truth. This folder is **outside** the review-cycle scan (`tower/cycle.py` `DOC_FOLDERS` + `_archive/`), so nothing here projects onto the Control Tower board.

- `manifest.json` — every move (`from` → `to`) and the brief id each document became.
- Their todo cards moved with them: `tower/data/todos-migrated/magiq-media.json` (the live store was backed up first as `tower/data/todos/magiq-media.json.bak-migrated-<timestamp>`).
- Still live in `plans/`: the 7 cdk-magiq-media plans and WS-02a (MM-025, magiq-auth), plus finished plans and reference docs.

## Rollback

```bash
cd Z:/claudia/magiq   # AIS-OS root
python - <<'PY'
import json, os, subprocess
m = json.load(open("projects/magiq-media/_migrated/manifest.json"))
for mv in reversed(m["moves"]):
    os.makedirs(os.path.dirname(mv["from"]), exist_ok=True)
    subprocess.run(["git", "mv", mv["to"], mv["from"]], check=True)
store, moved = "tower/data/todos/magiq-media.json", "tower/data/todos-migrated/magiq-media.json"
live, back = json.load(open(store, encoding="utf-8")), json.load(open(moved, encoding="utf-8"))
for i in back:
    i["source"] = next((mv["from"] + i["source"][len(mv["to"]):] for mv in m["moves"]
                        if i["source"] == mv["to"] or i["source"].startswith(mv["to"] + "/")), i["source"])
json.dump(live + back, open(store, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
os.remove(moved)
PY
```

Then restart the Tower container. Cards keep their ids (derived from the document id), so nothing is duplicated.
