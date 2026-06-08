---
name: github-my-prs
description: Look up all open pull requests assigned to Chase across all his GitHub repos. Reports count, project, PR number, title, branch, and who requested review. Use when Chase says "show my PRs", "pending PRs", "pull requests assigned", "open PRs", or "what's my PR queue".
triggers:
  - "show my PRs"
  - "pending PRs"
  - "pull requests assigned"
  - "open PRs"
  - "what's my PR queue"
  - "PRs waiting on me"
---

# github-my-prs

## Purpose

Give Chase a single summary of every open PR assigned to him across all his GitHub repos — count, project, title, branch, and who requested it.

---

## Prerequisites

- `gh` must be authenticated (check: `gh auth status`)
- If not authenticated, stop and tell Chase to run: `gh auth login --with-token`

---

## Procedure

### Step 1 — Get the authenticated user's login

```bash
ME=$(gh api user --jq '.login')
```

This is the only account you query — never look up PRs for others.

---

### Step 2 — Collect open PRs across all repos

For each repo owned by the authenticated user:

```bash
for repo in $(gh repo list "$ME" --limit 50 --json name -q '.[].name'); do
  gh pr list --repo "$ME/$repo" \
    --state open \
    --search "assignee:$ME" \
    --json number,title,url,createdAt,headRefName,baseRefName,author,reviewers 2>/dev/null
done
```

`reviewers` returns the array of accounts that requested Chase's review.

If no repos are found, report: "No GitHub repos found for $ME."

---

### Step 3 — Format the output

**If there are open PRs:**

```
📬 Open Pull Requests — [count] total

**cramone/repo-name** (N PRs)
  #12 — Fix login redirect after OAuth callback
     Branch: fix/login-redirect → main
     Requested by: @teammate · 3 days ago

  #15 — Add JWT token refresh endpoint
     Branch: feat/token-refresh → main
     Requested by: @another-dev · 1 week ago

**cramone/another-repo** (1 PR)
  #3 — ...
```

**If no open PRs:**
```
No open PRs assigned to you. Clean slate.
```

---

### Step 4 — Summary line

End with a one-line summary:
```
Total: N PRs · M repos · oldest pending: X days
```

---

## Rules

- Only show PRs where Chase is a requested reviewer (assignee), not PRs he authored.
- Do not include merged or closed PRs.
- Do not show draft PRs unless explicitly asked — filter with `--search "assignee:$ME draft:false"` to exclude them.
- Do not modify any PRs.
- If `gh` errors on a specific repo, skip it and continue — do not abort the whole scan.

---

## What to say to use this skill

**Trigger phrase:** "show my open PRs" or "pending PRs"

The skill activates automatically on those phrases. No extra context needed — it reads the authenticated account and scans all repos.
