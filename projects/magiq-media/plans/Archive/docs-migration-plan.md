# Plan: Move spec/ADRs into magiq-media/docs, auto-publish to the ADO wiki

**Owner:** Chase Ramone
**Status:** Draft — not yet executed
**Goal:** Stop hand-syncing spec/ADRs to the Azure DevOps wiki. Co-locate spec with
the code it describes so spec drift gets caught in PR review, and automate the
wiki publish step via GitHub Actions. Keep the Z:\ docs project as the
in-flight "AI operating system" workspace (memory, todos, meetings, decisions
log, plans) — that layer does not move.

---

## 0. Decisions to lock in before starting

These are judgment calls — defaults are recommended, but confirm before Phase 2.

| Question | Recommendation |
|---|---|
| Does `spec/prompts/` move to `docs/`? | No — leave in Z:\, it's process/meta (how the spec was authored), not the spec itself |
| Does `spec/reviews/` move to `docs/`? | No — same reasoning, informal review artifacts |
| What's the new home for `spec/prompts/` and `spec/reviews/` once `spec/` is otherwise gone from Z:\? | Promote to top-level `Z:\...\magiq-media\prompts\` and `Z:\...\magiq-media\reviews\`, siblings to `meetings/`, `plans/`, `decisions/` |
| Which branch triggers the wiki-publish Action? | `develop` — matches the existing "current truth" convention (develop auto-deploys dev); `main`/release would lag behind what people are actually working against |
| ADO PAT scope for the publish step | Generate a PAT scoped to **Code (Read & Write)** for the `Media` ADO project (the wiki is a git repo under the hood) — confirm this in ADO's token UI since exact scope naming varies by org config |

---

## 1. Fix the one link that will break in the move

I found exactly one file with relative links that reach *outside* `spec/`/`adrs/` into
content that is **not** moving: `mediaitem.checkout-cr-saga.md` has three links to
`../../../../../decisions/log.md`. That file doesn't exist yet either way, but once
`spec/` is nested one level deeper (`docs/spec/...` instead of `spec/...`), the same
relative path resolves to the wrong place (`docs/decisions/log.md` instead of the
Z:\ docs project's `decisions/log.md`).

**Action:** In `Z:\claudia\magiq\projects\magiq-media\spec\contexts\Catalog\aggregates\MediaItem\mediaitem.checkout-cr-saga.md`,
replace the three `](../../../../../decisions/log.md)` relative links with a plain-text
pointer, e.g. `(see the decision log in the magiq-media docs project — not
version-controlled with this repo)`. A relative link can't span two different
git repos, so this has to stop being a clickable link either way.

Everything else was already checked — no other links cross the spec/adrs ↔
everything-else boundary in either direction, and no links cross between `spec/`
and `adrs/` in a way that breaks (they stay siblings under `docs/`, so `../spec/...`
references from ADR files keep working unchanged).

---

## 2. Prep the target structure in the code repo

In `D:\source\github\magiq-media`:

1. Confirm `docs/` exists (it does, currently empty).
2. Create `docs/spec/` and `docs/adrs/` as the new homes.
3. Add a short `docs/README.md` explaining the split: "This folder is the
   versioned, code-reviewed spec — it publishes to the ADO wiki automatically on
   merge to `develop`. For in-flight design notes, meeting logs, the decision
   journal, and project memory, see the docs project at
   `Z:\claudia\magiq\projects\magiq-media`."

## 3. Move the content

From `Z:\claudia\magiq\projects\magiq-media`:

1. `spec\architecture\`, `spec\contexts\`, `spec\shared\` → `D:\source\github\magiq-media\docs\spec\` (same three subfolders, same relative structure — no internal link rewriting needed, this is a straight move)
2. `adrs\` → `D:\source\github\magiq-media\docs\adrs\` (same — sibling relationship to `spec/` is preserved under `docs/`, so ADR → spec relative links keep working)
3. `spec\prompts\` → `Z:\...\magiq-media\prompts\` (promoted to top-level, per §0)
4. `spec\reviews\` → `Z:\...\magiq-media\reviews\` (same)
5. Delete the now-empty `spec\` folder from Z:\.

Because Z:\claudia\magiq\projects\magiq-media is a Cowork-managed folder, files
written there can't be deleted without explicit confirmation — when this gets
executed in a Cowork session, expect a confirmation prompt (`allow_cowork_file_delete`)
before step 5 goes through. Do the move as copy-then-verify-then-delete, not a
blind move, so nothing is lost if something goes wrong mid-step.

## 4. Commit to magiq-media

1. New branch off `develop`: `deploy/chase/docs-migration` (matches the
   Infra/CI branch pattern in the repo's branching table).
2. Commit the moved `docs/spec/` and `docs/adrs/`, plus `docs/README.md`.
3. Open a PR into `develop`. Since this is a pure content move (no code
   changes), this can likely be a fast self-approve, but running it through
   the normal PR flow now establishes the habit for future spec-touching PRs.

## 5. Build the GitHub Actions publish workflow

Add `docs/tools/sync-wiki.py` to the repo — this is the same link-rewrite script
used for today's manual sync (spec-relative `../../../` links → ADO's absolute
`/Module/Page` format), just re-rooted to read from `docs/spec/` and `docs/adrs/`
instead of the Z:\ path. Key change from the script already used for the manual
sync: `SPEC` becomes `${{ github.workspace }}/docs`, and it needs a working
clone of `Media.wiki` to write into before committing/pushing.

Add `.github/workflows/publish-wiki.yml`:

```yaml
name: Publish spec to ADO wiki

on:
  push:
    branches: [develop]
    paths:
      - 'docs/spec/**'
      - 'docs/adrs/**'
      - 'docs/tools/sync-wiki.py'

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout magiq-media
        uses: actions/checkout@v4
        with:
          path: magiq-media

      - name: Checkout Media.wiki
        run: |
          git clone https://$ADO_WIKI_PAT@dev.azure.com/MAGIQSoftware/Media/_git/Media.wiki wiki
        env:
          ADO_WIKI_PAT: ${{ secrets.ADO_WIKI_PAT }}

      - name: Run sync
        run: python3 magiq-media/docs/tools/sync-wiki.py --spec magiq-media/docs --wiki wiki

      - name: Commit and push if changed
        run: |
          cd wiki
          git config user.name "magiq-media-bot"
          git config user.email "bot@magiqsoftware.com"
          git add -A
          if ! git diff --cached --quiet; then
            git commit -m "Sync spec from magiq-media@${{ github.sha }}"
            git push
          else
            echo "No wiki changes"
          fi
```

Repo setup needed: add `ADO_WIKI_PAT` as a repository secret in
`magiqsoftware/magiq-media` (Settings → Secrets and variables → Actions).

## 6. One-time cutover sync

Before relying on the Action, run `sync-wiki.py` once by hand (or trigger the
workflow manually via `workflow_dispatch`) and diff the result against the
wiki state from today's manual sync — they should be identical, since it's the
same link-rewrite logic against the same content, just re-rooted. This
confirms the ported script works before the manual sync habit is retired.

## 7. Update CLAUDE.md files for consistency

**`D:\source\github\magiq-media\CLAUDE.md`** — replace the "Spec and architecture
— source of truth" table's `Z:\claudia\...\spec\` and `Z:\claudia\...\adrs\` rows
with local paths (`docs/spec/`, `docs/adrs/`). Keep the other rows (brief,
todos, memory, plans) pointing at Z:\ — those aren't moving. Add a line noting
`docs/spec` and `docs/adrs` publish to the ADO wiki automatically on merge to
`develop` via `.github/workflows/publish-wiki.yml` — don't hand-edit
`Media.wiki` anymore, it's a generated artifact.

**`Z:\claudia\magiq\projects\magiq-media\CLAUDE.md`** — update the File Map
table: remove the `spec/` and `adrs/` rows (or mark them "moved to
`D:\source\github\magiq-media\docs\`"), add rows for the promoted `prompts/`
and `reviews/` folders. Leave everything else (todos.md, MEMORY.md, plans/,
decisions/, brief.md, use-cases.md, architecture.md) as-is — this file's job
now is purely "the AI operating system layer," not spec custody.

No changes needed in `aspnetcore-platform` or `cdk-magiq-media` CLAUDE.md —
neither references the Z:\ spec/adrs paths directly (confirmed by grep).

## 8. Update the Cowork project instructions

This lives in Cowork project settings, not a repo file — update it directly in
the UI. Replace the routing guidance so it reads:

> Default routing: code changes and reviews → magiq-media repo. **Spec, API
> contracts, and architecture decisions (ADRs) → `D:\source\github\magiq-media\docs\`.**
> In-flight design exploration, meeting notes, the decision journal, project
> memory, and todos → the Z:\ docs project. Deploy/infra questions →
> cdk-magiq-media. Platform SDK internals → aspnetcore-platform.

This keeps both folders connected in Cowork sessions exactly as they are today
— nothing about the folder connections changes, only which folder is
authoritative for which content type.

## 9. Verify both session types after cutover

- **Cowork session:** open this project, ask a spec question (e.g. "what's the
  MediaProfile publish guard behavior?") and confirm Claude reads from
  `D:\source\github\magiq-media\docs\spec\...` rather than a stale Z:\ copy.
  Ask a "what did we decide in last week's sync meeting" question and confirm
  it still reads `Z:\...\meetings\`.
- **Normal Claude Code session** (run directly in `D:\source\github\magiq-media`):
  confirm the repo's CLAUDE.md correctly points it at `docs/spec` locally, and
  that it still knows to reach across to `Z:\claudia\magiq\projects\magiq-media`
  for MEMORY.md, todos, and decisions when the task calls for it — full local
  filesystem access means this cross-drive reference works the same as it does
  today, no sandboxing constraint like Cowork has.

## 10. Cleanup / rollback safety

- Keep the pre-migration state of `Z:\...\magiq-media\spec\` and `adrs\` in a
  local zip or a throwaway git tag until the first real PR touching spec has
  gone through the new flow successfully — cheap insurance during cutover.
- Once confident, retire the manual `sync_wiki.py` one-off script from the
  outputs scratch folder — its logic now lives in `docs/tools/sync-wiki.py` in
  the repo, which is the version that should be maintained going forward.

---

## Summary of what moves vs. stays

| Location | Content |
|---|---|
| **Stays:** `Z:\claudia\magiq\projects\magiq-media` | `MEMORY.md`, `todos.md`, `meetings/`, `plans/`, `decisions/`, `brief.md`, `use-cases.md`, `architecture.md`, `files/`, `gitignored/`, promoted `prompts/`, `reviews/` |
| **Moves:** → `D:\source\github\magiq-media\docs\` | `spec/architecture/`, `spec/contexts/`, `spec/shared/` → `docs/spec/`; `adrs/` → `docs/adrs/` |
| **Generated, not authored:** `C:\Users\chase\OneDrive\repos\Media.wiki` | Fully bot-managed via `publish-wiki.yml` — stop hand-editing |
