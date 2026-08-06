# ADR-008 — React SPA Served from API wwwroot

**Date:** 2026-07-13  
**Status:** Accepted

---

## Context

The application has a React frontend for the review/confirmation UI (Steps 6–7), the jobs dashboard, and the job details view. It needs to be hosted somewhere.

Options:

- **Separate web server / CDN** — React served independently of the API. Requires CORS configuration, separate deployment artifact, separate IIS site or container.
- **API wwwroot** — React is built and published into the ASP.NET Core app's `wwwroot`. Both the SPA and the API are served from the same process, same origin, same IIS site.

On-premises hosting makes a CDN irrelevant. A second IIS site or container adds deployment complexity for a single-server, operator-only tool.

FastEndpoints runs on the standard ASP.NET Core minimal-API pipeline, which supports `UseDefaultFiles()` + `UseStaticFiles()` + `MapFallbackToFile("index.html")` alongside `UseFastEndpoints()` without conflict.

---

## Decision

Build the React SPA and publish it into the API's **`wwwroot`**. Serve static files from the same ASP.NET Core app.

- **No separate web server.** No CORS surface.
- **Single deployable artifact.** One IIS site, one Docker image.
- **Route prefix.** FastEndpoints is configured with a route prefix (e.g. `api`) so the SPA deep-link fallback (`MapFallbackToFile("index.html")`) only intercepts non-API paths.
- **Dockerfile** builds the React SPA (via Node) and copies the output into the published API image's `wwwroot`.

---

## Consequences

- Deployment is a single artifact — simplifies IIS setup and Docker image management.
- No CORS configuration required — SPA and API share the same origin.
- The `api` route prefix must be consistently applied to all FastEndpoints routes — a missing prefix on any endpoint would cause the SPA fallback to intercept it.
- React build is part of the CI/CD pipeline — the `Dockerfile` and any publish scripts must include the Node build step.
- If a separate frontend deployment is ever needed (e.g. different team owns the SPA), extracting it is straightforward — add CORS config and adjust the build pipeline.
