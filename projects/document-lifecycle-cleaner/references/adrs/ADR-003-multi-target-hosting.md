# ADR-003 — Multi-Target Hosting: IIS Default, Docker Supported

**Date:** 2026-07-13  
**Status:** Accepted

---

## Context

The application is on-premises / customer-hosted inside NATA's environment. The team's usual AWS-native stack is not available. Two hosting targets were considered: IIS and Docker (containerised).

The initial architecture fixed IIS. It was subsequently determined that the client may later prefer a containerised deployment, and supporting both has negligible cost if the application stays hosting-agnostic.

The MAGIQ Documents integration was confirmed to have no Windows-specific dependencies (SOAP via `HttpClient` + Dapper on `Microsoft.Data.SqlClient` — both cross-platform), making a Linux container viable.

---

## Decision

Support **two deployment targets — IIS and Docker** — without code changes between them:

1. **IIS is the default.** The assumed target for initial delivery.
2. **Docker is a supported alternative.** Client can switch without re-architecting.
3. **Kestrel is the web server in both cases.** Under IIS, Kestrel sits behind the IIS reverse proxy (in-process hosting model). Under Docker, Kestrel listens directly.
4. **All environment-specific settings come from configuration.** Connection strings, MAGIQ Documents endpoints, ports — no hard-coded host assumptions.
5. **Dockerfile** compiles the React SPA and publishes it into the API image's `wwwroot`, producing the same single self-contained artifact used under IIS.
6. **Linux base image** is viable (no Windows-only dependencies). Final base image choice is at the client's discretion.

---

## Consequences

- No host-specific code paths — `appsettings.json` + environment variables cover all differences.
- Single deployable artifact in both cases (React in `wwwroot`).
- Hangfire runs in-process in both targets — no change to job processing.
- Docker adds a `Dockerfile` and potentially a `docker-compose.yml` to the repo; minimal overhead.
- In-process IIS hosting model (default) is expected; out-of-process remains an option but is not the assumed default.
