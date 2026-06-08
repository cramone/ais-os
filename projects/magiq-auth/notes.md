# Notes — MAGIQ Auth

_Open questions, session notes, and resolutions._

---

## Validate redirect URI on host name, not just port
_Captured: 2026-06-02T04:52:00Z_

The redirect URI validation needs to check the host name, not just the port. Port-only matching is insufficient.

---
