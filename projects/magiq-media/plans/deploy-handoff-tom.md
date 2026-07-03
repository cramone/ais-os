# Deploy Handoff — Tom

_Created: 2026-07-03_

What remains to finish the magiq-media → cdk-magiq-media deploy pipeline. Ordered so
dev/qa light up first, then staging/prod after their AWS accounts + approvals are ready.

**Context:** magiq-media CI (`build-and-push.yml`) builds all hosts, pushes images to the
shared ECR in the **DevOps** account (738608577325), then dispatches to `cdk-magiq-media`,
which runs `cdk deploy` into each environment's own AWS account (Model A). See
`spec/architecture/branching-and-deployment.md` for the full strategy.

**Account map:** dev=Development (989143135668) · qa=QA (835494934465) ·
staging=Demo (727517389921) · prod=Prod (614323302920) · shared ECR=DevOps (738608577325).
Region: ap-southeast-2.

---

## A. GitHub — `magiq-media` repo

1. **Create the deploy-dispatch token — THE blocker for any auto-deploy.**
   - Add repo **secret** `CDK_DISPATCH_TOKEN`.
   - Value = fine-grained **PAT** (or GitHub App installation token) with **`contents: write`**
     (repository-dispatch) permission on **`magiqsoftware/cdk-magiq-media`**.
   - Why: the default `GITHUB_TOKEN` cannot dispatch to another repo. Until this exists the
     `dispatch-deploy` / `dispatch-staging` steps are skipped — builds go green, nothing deploys.

2. **Land the workflow changes on `develop`.**
   - Merge branch `deploy/chase/initial-gitflow` → `develop` (via PR).
   - Until merged, `develop` still triggers on the old `[main, release/**]` and none of the
     new trigger remap or dispatch logic is live.

3. **Go-live toggles** — repo vars `STAGING_ENABLED` and `PROD_ENABLED` are `false`. Flip to
   `true` per env only after that account is signed off (see section E). dev/qa need no flag.

## B. GitHub — `cdk-magiq-media` repo

4. **Add required-reviewer protection** on the `staging` and `prod` **environments**
   (Settings → Environments) so those deploys pause for human approval. dev/qa stay ungated.
5. **Verify env config** (already populated — confirm correct):
   - `CDK_DEFAULT_ACCOUNT` vars: dev=989143135668, qa=835494934465, staging=727517389921,
     prod=614323302920.
   - `AWS_DEPLOY_ROLE_ARN` secret per env → correct deploy-role ARN in each account.
   - `NUGET_PAT`, `ORGANIZATION_ID` secrets present.

## C. AWS — DevOps account (shared ECR, 738608577325)

6. **OIDC push role** — confirm `GitHubOidcMagiqMediaRole` trusts `magiq-media` (OIDC) and can
   push to the `magiq-media` ECR repo. Already working for current builds; verify it covers the
   new triggers (`develop`, `release/**`, `v*` tags).
7. **ECR cross-account pull policy** — the ECR repository policy must allow all four env
   accounts to pull: `ecr:GetAuthorizationToken`, `BatchGetImage`, `GetDownloadUrlForLayer`,
   `BatchCheckLayerAvailability`. The DevOps CDK stack has the policy construct — confirm it
   lists Development, QA, Demo, Prod.

## D. AWS — each environment account (Development, QA, Demo, Prod)

For **each** of the four accounts, in ap-southeast-2:

8. **Deploy role** (the one in cdk `AWS_DEPLOY_ROLE_ARN`) — trusts `cdk-magiq-media` via OIDC,
   with permissions: CloudFormation, Lambda, IAM (update function roles), ECR describe/pull,
   and read access to the data-stack outputs.
9. **CDK bootstrap** — run `cdk bootstrap` (CDKToolkit stack) in the account/region, trusting
   the deploy role. Demo (staging) and Prod are new → almost certainly not bootstrapped yet.
10. **Account readiness** — confirm the account can accept deploys (service quotas, any
    prerequisite data stacks).

## E. After each account is ready (per env)

11. Env verified + Tom-approved → set the matching flag (`STAGING_ENABLED` / `PROD_ENABLED`)
    to `true` in magiq-media.
12. **Smoke test dev first:** push to `develop` → build + ECR push → dispatch → cdk deploys to
    Development. Confirm end-to-end before enabling qa/staging/prod.

## F. Known gap (not blocking)

13. `saga-document-signing` (9th host) is built by magiq-media but **not wired** in cdk
    `magiq-media-stack.ts` — only 8 hosts deploy. Add its `ecrCode(...)` when the signing host
    is ready.

---

**Critical path to first deploy:** #1 (token) → #2 (merge to develop) → #6/#8/#9 for the
Development account → #12 smoke test.
