# Reviews — magiq-auth

_Established 2026-08-28 with `MA-001`, the project's first review under the `review-cycle` skill._

**A review is where work starts.** Findings get argued here; sequencing, PR shaping and execution
tracking happen in the matching `plans/` folder. The folder name is shared between the two trees, so a
review and the plan that consumes it stay traceable — including after both are archived. See
`CLAUDE.md § Review → Plan` for the convention and § Review → Plan cycle for the adoption marker.

**Document ids** are `MA-nnn`, minted monotonically across `reviews/` and `plans/` including every
`Archive/`, never reused, never renumbered. All cross-references use ids, never paths.

**Status vocabulary** — _Draft_ · _Active_ (findings agreed, being worked) · _Parked_ · _Superseded_ ·
_Done_.

**Outcome** — every review needs one eventually: _plan_ · _parked_ · _decision-only_ · _folded-into_ ·
_withdrawn_. _pending_ is a state to leave, not to rest in.

| Id | Workstream | Review | Status | Outcome | Its plan |
|---|---|---|---|---|---|
| MA-001 | `validateuser-lockout/` | `validateuser-lockout-review-2026-08-28.md` | **Draft** | pending | *(none yet — 7 open questions; plan gate shut until findings agreed)* |

---

## `validateuser-lockout/` — account lockout on `ValidateUser`

Adapted 2026-08-28 from `D:\source\github\magiq-auth\reports\ValidateUser-Lockout-Review.md`. That
report remains the source artefact in the code repo; its §§3–5, 7, 8 are the proposed design, test plan
and rollout notes, which were deliberately **not** carried into the review — they are the raw material
for the plan.

Ten findings, `VUL-1` … `VUL-10`. Headline: account lockout sets `user.Active = false` permanently and
is reachable by any unauthenticated caller who knows an email address (VUL-1), while
`PasswordResetSend` refuses to issue a reset token to an inactive user (VUL-4) — so lockout removes the
account's own recovery path and every unlock needs an administrator.

Paired prompt: `validateuser-lockout-review-2026-08-28-prompt.md`. Paste-ready, stands alone.

---

## Legacy documents

The five files in `plans/` (`claims-normalization.done`, `client-credentials-plan.done`,
`customer-deletion-plan.md`, `external-providers-plan.md`, `tenant-switching-plan.md`) predate this
cycle. They carry no ids and no front-matter, so their status is **UNKNOWN** — not met, not unmet, not
done. Several analysis documents in the code repo (`PRODUCTION_CODE_AUDIT_REPORT.md`,
`AuditLogging-Separation-Plan.md`, `sync-to-async-review-plan.md`) are in the same position.

Backfill one workstream at a time, when that workstream is next picked up, deriving status from
`plans/README.md` rather than from guesswork about the body. **Do not bulk-rewrite.**
