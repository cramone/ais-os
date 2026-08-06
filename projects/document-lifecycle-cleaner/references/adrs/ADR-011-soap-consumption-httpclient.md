# ADR-011 — MAGIQ SOAP Consumption: typed HttpClient (not a WCF proxy)

**Date:** 2026-07-27
**Status:** Accepted

---

## Context

ADR-004 chose SOAP (`srv.asmx`) as one of the two MAGIQ Documents integration
paths but deliberately left the *consumption style* open: "a generated SOAP proxy
or typed `HttpClient` wrapper". Story 34132 (the SOAP primitive) is the point that
choice must be made — the delivery plan flags it as the one open sub-decision for
this branch, to be settled with an ADR when the branch is cut.

The two candidates:

1. **Typed WCF proxy** — `System.ServiceModel.*` (`dotnet-svcutil` / connected
   service) generating strongly-typed request/response classes and a channel.
2. **Hand-built typed `HttpClient`** — construct SOAP 1.1 envelopes and parse
   responses directly, no generated code, no WCF stack.

The published WSDL was reviewed to decide. Findings:

- The service is classic ASP.NET **ASMX** (infoRouter under MAGIQ Documents),
  offering SOAP 1.1, SOAP 1.2, HTTP GET and HTTP POST bindings.
- The WSDL is very large (~1.3 MB, hundreds of operations); DLC uses a small
  handful (`AuthenticateUser`, `CreateDomain`, `Move`, `DeleteFolder`,
  `DeleteDomain`, recycle-bin ops).
- Crucially, the result payloads are typed as **`<s:complexType mixed="true">`
  with `<s:any/>`** — i.e. the WSDL does *not* describe the real response shape.
  `AuthenticateUserResult` is an opaque XML fragment carrying the infoRouter
  `success` attribute and ticket. A generated WCF proxy would surface these as
  untyped `XmlElement`/`XmlNode` anyway, so the proxy buys no type safety for the
  responses — the part that actually matters.

## Decision

Consume the MAGIQ SOAP service through a **hand-built typed `HttpClient`**
(`IMagiqSoapClient` / `MagiqSoapClient`, registered with `AddHttpClient`), not a
WCF proxy.

- **SOAP 1.1**, document/literal. Requests are built with `System.Xml.Linq`
  (`SoapEnvelope.Build`), posted as `text/xml; charset=utf-8` with a quoted
  `SOAPAction` header (e.g. `"http://tempuri.org/AuthenticateUser"`).
- Operation namespace is the WSDL `targetNamespace`, `http://tempuri.org/`.
- Endpoint is **configurable** (`MagiqDocumentsOptions.Endpoint`) — no baked-in
  URL (Task 34158). Timeout and transient-fault retry (count + exponential
  backoff) are options too.
- The **cardinal rule** is enforced in `MagiqResponseReader`: the outcome is read
  from the payload's `success` attribute, never the HTTP status (the service
  answers HTTP 200 even on failure). A `success="false"` maps to an
  `Operation` error and is **never retried**; only transport faults (network,
  timeout, HTTP 5xx) are retried.
- Because the WSDL result types are `xsd:any`, the reader normalises both
  encodings a mixed/any result can arrive in — a nested element, or an
  escaped/CDATA XML string (with or without an inner XML declaration).

## Consequences

- **No `System.ServiceModel.*` dependency** and no generated-code checkin to keep
  in sync with a 1.3 MB WSDL — consistent with the project's vanilla-primitives
  grain (no `Magiq.Platform.*`, minimal packages).
- Full control over the wire format: exact envelope, `SOAPAction`, timeout, and a
  retry policy that understands the 200-with-`success="false"` contract — which a
  generic WCF channel would not distinguish from success.
- Uses only framework XML APIs (`System.Xml.Linq`) — **zero new packages** for
  this story.
- Cost: request/response mapping is hand-written per operation. Acceptable — only
  a handful of operations are used, and the `xsd:any` responses would be untyped
  under a proxy regardless.
- **Open detail for the integration pass (Story 34134):** the exact infoRouter
  child element names on the result payload (`Ticket`, `ErrorMsg`/`ErrorNo`) are
  inferred, since the WSDL does not describe them. `MagiqResponseReader` matches
  them case-insensitively with fallbacks; confirm against a live
  `training.magiqdocuments.com` response and tighten if needed.

## Alternatives considered

- **Typed WCF proxy (`System.ServiceModel`)** — familiar and strongly typed for
  *requests*, but adds the WCF client stack and a large generated surface, and
  still yields untyped `XmlElement` for the `xsd:any` *responses* that carry the
  real contract. Net type-safety gain is marginal for a real dependency cost.
- **`ServiceReference` / connected service checked into the repo** — couples the
  build to a regenerated 1.3 MB artefact and obscures the tiny slice of the API
  actually used.
- **HTTP GET/POST binding** (the ASMX non-SOAP bindings) — simpler wire format,
  but non-standard, less portable across MAGIQ versions, and still needs the same
  `success`-attribute parsing. No advantage over SOAP 1.1.

---

## Amendment — 2026-08-05: folder-rule read/write operations

Two operations are added to the hand-built client for the reactive folder delete-rule
guard (see ADR-004 amendment and `decisions/log.md` [2026-08-05]) — same pattern as the
rest, no new dependency:

- **`GetFolderRules`** — read path. The `<Rules>` element is captured verbatim into a
  `FolderRuleSet` (a detached `XElement` clone) so the original can be restored
  byte-for-byte after one rule is relaxed. A success response with no `<Rules>` is a
  `Protocol` error.
- **`SetFolderRules`** — write path. `xmlRules` is the raw `<Rules>…</Rules>` fragment set
  as element text, so the envelope builder XML-escapes it to the `&lt;Rules&gt;…` form the
  service expects; `ApplyToTree` is sent lower-case `false` so only the target folder is
  affected. Outcome read from `success` (ADR-004 cardinal rule), parsed by the shared
  `ParseAck`.

Both are built with `System.Xml.Linq` and posted with a quoted `SOAPAction`
(`"http://tempuri.org/GetFolderRules"` / `SetFolderRules`), exactly as the existing ops.

**Open detail (mirrors the Story 34134/34525 pattern):** the exact **path format** these two
ops expect is not yet confirmed against training. The client currently sends a domain-rooted,
no-leading-slash path (matching `GetFolders`/`FolderExists` and the `Path="Test"` request
sample); confirm against a live `training.magiqdocuments.com` response and adjust if the
rule ops want the leading-slash form that `Move`/`DeleteFolder` use.
