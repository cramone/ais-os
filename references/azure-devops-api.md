# Azure DevOps REST API Reference

Source: [Microsoft Learn — Azure DevOps REST API 7.1/7.2](https://learn.microsoft.com/en-us/rest/api/azure/devops/?view=azure-devops-rest-7.2)

---

## Authentication

PAT via Basic Auth. Empty username, PAT as password.

```
Authorization: Basic {base64(:<PAT>)}
```

Encode in bash:
```bash
echo -n ":YOUR_PAT" | base64
```

Headers for every request:
```
Authorization: Basic {BASE64_ENCODED_PAT}
Content-Type: application/json
Accept: application/json
```

For PATCH (work items): `Content-Type: application/json-patch+json`

---

## Base URLs

| Service | Base URL |
|---|---|
| Most APIs | `https://dev.azure.com/{organization}/` |
| Releases | `https://vsrm.dev.azure.com/{organization}/` |
| Identities / Graph | `https://vssps.dev.azure.com/{organization}/` |
| User Entitlements | `https://vsaex.dev.azure.com/{organization}/` |

---

## Common Query Parameters

| Param | Purpose |
|---|---|
| `api-version` | Required. Use `7.1` unless noted |
| `$top` | Max items per page |
| `$skip` | Pagination offset |
| `continuationToken` | Paged results token |
| `$expand` | Include related data |

---

## Status Codes

| Code | Meaning |
|---|---|
| 200 | Success with body |
| 201 | Created |
| 204 | Success, no body |
| 400 | Bad request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not found |
| 409 | Conflict |

---

## 1. Work Items

**Base:** `https://dev.azure.com/{org}/{project}/_apis/wit/`

```
# Get
GET /workitems/{id}?api-version=7.1&$expand=relations

# Get multiple
GET /workitems?ids={id1},{id2}&api-version=7.1

# Create
POST /workitems/{type}?api-version=7.1
Content-Type: application/json-patch+json
[
  { "op": "add", "path": "/fields/System.Title", "value": "Title" },
  { "op": "add", "path": "/fields/System.Description", "value": "Description" },
  { "op": "add", "path": "/fields/System.AssignedTo", "value": "user@company.com" },
  { "op": "add", "path": "/fields/System.AreaPath", "value": "ProjectName\\AreaPath" }
]

# Update
PATCH /workitems/{id}?api-version=7.1
Content-Type: application/json-patch+json
[
  { "op": "replace", "path": "/fields/System.State", "value": "Active" },
  { "op": "replace", "path": "/fields/System.AssignedTo", "value": "user@company.com" }
]

# Batch update
PATCH /$batch?api-version=6.1
[
  {
    "method": "PATCH",
    "uri": "/{org}/{project}/_apis/wit/workitems/{id}",
    "body": [{ "op": "replace", "path": "/fields/System.State", "value": "Done" }]
  }
]

# Delete
DELETE /workitems/{id}?api-version=7.1

# Add comment
POST /workitems/{id}/comments?api-version=7.0-preview.3
{ "text": "Comment text" }

# Get comments
GET /workitems/{id}/comments?api-version=7.1

# Link work items
PATCH /workitems/{id}?api-version=7.1
Content-Type: application/json-patch+json
[{
  "op": "add",
  "path": "/relations/-",
  "value": {
    "rel": "System.LinkTypes.Dependency-forward",
    "url": "https://dev.azure.com/{org}/{project}/_apis/wit/workitems/{relatedId}"
  }
}]
```

### Common field paths
```
/fields/System.Title
/fields/System.State           — New, Active, Resolved, Closed, Done
/fields/System.AssignedTo
/fields/System.Description
/fields/System.AreaPath
/fields/System.IterationPath
/fields/System.WorkItemType    — Bug, Task, User Story, Feature, Epic
/fields/Microsoft.VSTS.Common.Priority
/fields/Microsoft.VSTS.Scheduling.StoryPoints
/fields/Microsoft.VSTS.Scheduling.RemainingWork
```

---

## 2. WIQL Queries

**Base:** `https://dev.azure.com/{org}/{project}/_apis/wit/`

```
# Run WIQL query
POST /wiql?api-version=7.1
{
  "query": "SELECT [System.Id], [System.Title], [System.State], [System.AssignedTo]
            FROM workitems
            WHERE [System.TeamProject] = @project
            AND [System.WorkItemType] = 'Task'
            AND [System.State] <> 'Done'
            ORDER BY [System.ChangedDate] DESC"
}

# Get saved query
GET /queries/{queryId}?api-version=7.1

# List saved queries
GET /queries?$depth=2&api-version=7.1

# Create saved query
POST /queries?api-version=7.1
{
  "name": "My Query",
  "wiql": "SELECT [System.Id] FROM workitems WHERE [System.TeamProject] = @project"
}
```

### Useful WIQL snippets
```sql
-- Active items assigned to me
WHERE [System.AssignedTo] = @me AND [System.State] <> 'Done'

-- Current sprint
WHERE [System.IterationPath] = @currentIteration('[Team]\\<IterationPath>')

-- Recently changed
WHERE [System.ChangedDate] >= @today - 7

-- By type
WHERE [System.WorkItemType] IN ('Bug', 'Task', 'User Story')
```

---

## 3. Boards & Backlogs

**Base:** `https://dev.azure.com/{org}/{project}/{team}/_apis/work/`

```
# List backlogs
GET /backlogs?api-version=7.1

# Get backlog work items
GET /backlogs/{backlogId}/workitems?api-version=7.1

# List boards
GET /boards?api-version=7.1

# Get board
GET /boards/{boardId}?api-version=7.1

# Get board cards
GET /boards/{boardId}/cards?api-version=7.1

# Reorder backlog items
PATCH /workitemsorder?api-version=7.1
{ "ids": [1, 2, 3], "parentId": 0, "previousId": 0 }
```

---

## 4. Sprints / Iterations

**Base:** `https://dev.azure.com/{org}/{project}/{team}/_apis/work/teamsettings/`

```
# List iterations
GET /iterations?$timeframe=current&api-version=7.1
GET /iterations?$timeframe=past&api-version=7.1
GET /iterations?$timeframe=future&api-version=7.1

# Get iteration
GET /iterations/{iterationId}?api-version=7.1

# Get iteration work items
GET /iterations/{iterationId}/workitems?api-version=7.1

# Get team capacity for iteration
GET /iterations/{iterationId}/capacities?api-version=6.0

# Update team member capacity
PATCH /iterations/{iterationId}/capacities/{teamMemberId}?api-version=7.1
{
  "activities": [{ "name": "Development", "capacityPerDay": 8 }],
  "daysOff": []
}
```

---

## 5. Git Repositories

**Base:** `https://dev.azure.com/{org}/{project}/_apis/git/`

```
# List repos
GET /repositories?api-version=7.1

# Get repo
GET /repositories/{repoId}?api-version=7.1

# List commits
GET /repositories/{repoId}/commits?api-version=7.1
GET /repositories/{repoId}/commits?searchCriteria.itemVersion.version={branch}&api-version=7.1

# Get commit
GET /repositories/{repoId}/commits/{commitId}?api-version=7.1

# List branches
GET /repositories/{repoId}/branches?api-version=7.1

# Create/delete/move branch (all via refs)
POST /repositories/{repoId}/refs?api-version=7.1
{
  "refUpdates": [{
    "name": "refs/heads/branch-name",
    "oldObjectId": "0000000000000000000000000000000000000000",
    "newObjectId": "{commitId}"
  }]
}
# Delete: set newObjectId to 40 zeros
```

---

## 6. Pull Requests

**Base:** `https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repoId}/`

```
# List PRs
GET /pullrequests?api-version=7.1
GET /pullrequests?searchCriteria.status=active&api-version=7.1
GET /pullrequests?searchCriteria.creatorId={userId}&api-version=7.1
GET /pullrequests?searchCriteria.reviewerId={userId}&api-version=7.1

# Get PR
GET /pullrequests/{prId}?api-version=7.1

# Create PR
POST /pullrequests?api-version=7.1
{
  "sourceRefName": "refs/heads/feature-branch",
  "targetRefName": "refs/heads/main",
  "title": "PR Title",
  "description": "Description"
}

# Update PR (complete)
PATCH /pullrequests/{prId}?api-version=7.1
{
  "status": "completed",
  "lastMergeSourceCommit": { "commitId": "{commitId}" },
  "completionOptions": {
    "mergeCommitMessage": "Squash merge",
    "deleteSourceBranch": true,
    "mergeStrategy": "squash"
  }
}

# Get PR threads (comments)
GET /pullrequests/{prId}/threads?api-version=7.1

# Add PR comment thread
POST /pullrequests/{prId}/threads?api-version=7.1
{
  "comments": [{ "content": "Comment text", "commentType": 1 }],
  "status": 1
}

# Add reply to thread
POST /pullrequests/{prId}/threads/{threadId}/comments?api-version=7.1
{ "content": "Reply text", "commentType": 1 }

# List reviewers
GET /pullrequests/{prId}/reviewers?api-version=7.1

# Add reviewer
PUT /pullrequests/{prId}/reviewers/{userId}?api-version=7.1
{ "vote": 0, "isRequired": false }

# Vote values: 10=approved, 5=approved-with-suggestions, 0=no-vote, -5=waiting, -10=rejected

# Get linked work items
GET /pullrequests/{prId}/workitems?api-version=7.1

# Get CI statuses
GET /pullrequests/{prId}/statuses?api-version=7.1
```

---

## 7. Pipelines & Builds

**Base:** `https://dev.azure.com/{org}/{project}/_apis/`

```
# List pipelines
GET /pipelines/pipelines?api-version=7.1

# Run pipeline
POST /pipelines/pipelines/{pipelineId}/runs?api-version=7.1
{
  "variables": { "varName": { "value": "varValue" } },
  "templateParameters": {}
}

# Get pipeline run
GET /pipelines/pipelines/{pipelineId}/runs/{runId}?api-version=7.1

# List pipeline runs
GET /pipelines/pipelines/{pipelineId}/runs?api-version=7.1

# List builds (legacy but widely used)
GET /build/builds?api-version=7.1
GET /build/builds?definitions={defId}&$top=10&api-version=7.1

# Get build
GET /build/builds/{buildId}?api-version=7.1

# Get build logs
GET /build/builds/{buildId}/logs?api-version=7.1
GET /build/builds/{buildId}/logs/{logId}?api-version=7.1

# Get artifacts
GET /build/builds/{buildId}/artifacts?api-version=7.1

# Queue build
POST /build/builds?api-version=7.1
{
  "definition": { "id": {definitionId} },
  "sourceBranch": "refs/heads/main"
}

# List build definitions
GET /build/definitions?api-version=7.1
```

---

## 8. Releases

**Base:** `https://vsrm.dev.azure.com/{org}/{project}/_apis/release/`

```
# List releases
GET /releases?api-version=7.1
GET /releases?definitionId={defId}&statusFilter=active&api-version=7.1

# Get release
GET /releases/{releaseId}?api-version=7.1

# Create release
POST /releases?api-version=7.1
{
  "definitionId": {definitionId},
  "description": "Release description",
  "artifacts": [{ "alias": "drop", "instanceReference": { "id": "{buildId}" } }]
}

# List release definitions
GET /definitions?api-version=7.1

# Get environment (deployment) status
GET /releases/{releaseId}/environments?api-version=7.1
```

---

## 9. Projects & Teams

**Base:** `https://dev.azure.com/{org}/_apis/`

```
# List projects
GET /projects?api-version=7.2

# Get project
GET /projects/{projectId}?api-version=7.2

# List teams
GET /projects/{projectId}/teams?api-version=7.1

# Get team
GET /projects/{projectId}/teams/{teamId}?api-version=7.1

# List team members
GET /projects/{projectId}/teams/{teamId}/members?api-version=7.1
```

---

## 10. Users & Identities

**Base:** `https://vssps.dev.azure.com/{org}/_apis/`

```
# Search identity by email
GET /identities?searchFilter=MailAddress&filterValue={email}&api-version=7.1

# Search by display name
GET /identities?searchFilter=DisplayName&filterValue={name}&api-version=7.1

# List users (Graph API)
GET /graph/users?api-version=7.1

# Get user (Graph API)
GET /graph/users/{userId}?api-version=7.1
```

---

## 11. Service Hooks / Webhooks

**Base:** `https://dev.azure.com/{org}/_apis/`

```
# List subscriptions
GET /hooks/subscriptions?api-version=7.1

# Create webhook subscription
POST /hooks/subscriptions?api-version=7.1
{
  "publisherId": "tfs",
  "eventType": "workitem.updated",
  "consumerId": "webHooks",
  "consumerActionId": "httpRequest",
  "consumerInputs": { "url": "https://your-endpoint.com" }
}

# Common eventType values:
#   build.complete
#   ms.vss-release.deployment-completed-event
#   git.push
#   git.pullrequest.created
#   git.pullrequest.updated
#   git.pullrequest.merged
#   workitem.created
#   workitem.updated
```

---

## 12. Test Plans & Runs

**Base:** `https://dev.azure.com/{org}/{project}/_apis/`

```
# List test plans
GET /testplan/plans?api-version=7.1

# List test runs
GET /test/runs?api-version=7.1

# Get test results
GET /test/runs/{runId}/results?api-version=7.1
```

---

## Tips

- WIQL `@project` macro = current project. `@me` = authenticated user.
- Work item types vary by process template (Agile, Scrum, CMMI). Scrum uses "Product Backlog Item", Agile uses "User Story".
- Rate limits: 200 requests per 30 seconds per user per org.
- Pagination: always check `x-ms-continuationtoken` response header for more pages.
- `{team}` in URLs = team name or team ID (GUID). Default team = `{project} Team`.
