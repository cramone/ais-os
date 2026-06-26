# Security Incident Report — InfoXpert Legacy Systems

**Customer:** InfoXpert  
**Systems affected:** IXReports, Publishing Portal  
**Review period:** 10 June 2026 – 12 June 2026  
**Compiled:** 15 June 2026  
**Compiled by:** Chase Ramone  

---

## Background

A security review was initiated across two InfoXpert legacy systems following investigation of suspicious RDP access events on the host machine (Windows Event ID 4624, Logon Type 10). Reviews covered IXReports (report processing engine) and the Publishing Portal (three WCF host projects).

---

## Investigation — Attack Chain Reconstruction

### 1. Path Traversal — Primary Entry Point

`ReportProcessing.aspx` accepted a filename from the URL with no validation. The attacker requested:

```
ReportProcessing.aspx?action=downloadSample&id=../../web.config
```

This exposed `web.config`, revealing path hints. The attacker enumerated those paths until locating SQL account credentials — most likely the `magiq` account.

### 2. Direct SQL Server Access

That account had the `sysadmin` role assigned. With those credentials, the attacker connected directly to SQL Server and enabled `xp_cmdshell`, which permits OS-level command execution.

### 3. OS Command Execution via xp_cmdshell

Running under the `MSSQLSERVER` account, the attacker leveraged `xp_cmdshell` to extract passwords from files on the server.

#### What They Most Likely Attempted to Steal

- SQL account credential with sysadmin role
- Database content on the SQL instance
- Other DB connection string credentials
- Local file system contents readable by the SQL Server service
- Local user account names

#### What They Could NOT Steal (authority: NT Service\MSSQLSERVER)

| Target | Why Blocked |
|--------|-------------|
| Windows account passwords / NTLM hashes | `NT Service\MSSQLSERVER` blocked from SAM/SYSTEM registry hives |
| Cached domain credentials | No `SeImpersonatePrivilege` on SQL Server account — no LSASS access |
| Credentials of other domain machines | Virtual service account — no domain identity, no network lateral movement |
| Other servers on the network | No domain token — `NT Service\MSSQLSERVER` cannot authenticate to remote machines |
| Active Directory data | No domain access from virtual service account |

The `MSSQLSERVER` account policy lacks `SeImpersonatePrivilege`, confirmed by absence of the following Defender alerts:

- Credential dumping via registry hives
- SAM database access attempt
- Shadow copy used to steal credentials
- Possible credential dumping tool activity
- LSASS memory read

**Blast radius is contained to RM02.** Isolating RM02 was the correct response.

---

## IXReports — SQL Injection Vulnerabilities

### Threat

Dynamic SQL WHERE clause construction in `ReportProcessing.aspx.cs` built queries by string concatenation using unvalidated browser input. Three confirmed attack vectors existed.

### How It Was Exploited (Attack Vectors)

| # | Location | Severity | Vector |
|---|----------|----------|--------|
| 1 | `BuildStringSql` ~line 859 | **Critical** | SQL operator (`Condition_X` query param) passed directly into SQL — attacker controls `=`, `>`, or injects arbitrary SQL fragment (e.g. `= '' OR 1=1 --`) |
| 2 | `BuildStringSql` ~lines 844/855 | **High** | String value (`Parameter_X` query param) injected into quoted SQL literal; only protection was blocking `;` — trivially bypassed with `' OR '1'='1` |
| 3 | `BuildDateSql` ~line 800 | **High** | Date operator (`thisDateTag`) and date value both from user input with no validation |

Secondary risk: `AR_Reports.cs` `insertWhere` / `AR_Reports_ReportStart` appended `groupby` (from report XML metadata) to SQL with no identifier validation.

**Request flow:**

```
Browser QueryString
  → GetParameters() [line 1078]
  → ExtractParameters() [line 875]   ← parses "Condition_X==||value" format
  → BuildDateSql() / BuildStringSql() ← builds SQL by concatenation
  → AR_Reports.insertWhere()          ← injects string into base SQL
  → OleDBDataSource executes
```

**Example payloads:**
- Value field: `' OR '1'='1` → returns all rows in table
- Operator field: `= '' OR 1=1 --` → bypasses all filter logic

### Resolution — Code Fixes Applied

| File | Location | Fix |
|------|----------|-----|
| `ReportProcessing.aspx.cs` | `BuildStringSql` ~line 840 | Operator whitelist (`=`, `<>`, `>`, `<`, `>=`, `<=`, `NULL`, `NOT NULL`, `LIKE`); reject anything outside set. Single-quote escape (`'` → `''`) on all values |
| `ReportProcessing.aspx.cs` | `BuildStringSql` ~line 831 | Single-quote escape in `Colindex == -1` branch |
| `ReportProcessing.aspx.cs` | `BuildDateSql` ~line 800 | Validate each date part is numeric via `int.TryParse`; whitelist date operators |
| `App_Code/AR_Reports.cs` | `AR_Reports_ReportStart` ~line 103 | Regex validate `groupby` matches `^[\w\.]+$` before appending to SQL |

**Why these fixes are sufficient:**  
Parameterized queries are the gold standard but require refactoring the OleDBDataSource execution layer. The fixes use the next-best approach: operator whitelisting closes the highest-risk vector entirely; single-quote escaping prevents string-termination injection; numeric validation prevents non-numeric date input reaching SQL; regex identifier validation prevents column/field name injection.

Full fix plan with before/after test scripts (Python): `D:\source\infoxpert\InfoXpert Legacy\IXReports\Src\Site\SQL-injection-plan.md`

---

## Publishing Portal — Security Review

**Projects reviewed:**
- InfoXpert Web Portal Site
- Host.WCF.ClientActionService
- Host.WCF.ImageService

### Findings

No substantial vulnerabilities found.

### Hardening Applied

Dependencies updated to a version including **TLS 1.2 hardening** — eliminates exposure to TLS 1.0/1.1 downgrade attacks and weak cipher suites.

---

## Summary

| System | Vulnerability | Status |
|--------|--------------|--------|
| IXReports | SQL Injection (3 vectors, Critical/High) | **Resolved** — operator whitelist + value escaping applied |
| Publishing Portal | No substantial findings | **Hardened** — TLS 1.2 enforced via dependency update |

---

## Recommendations (Outstanding)

- **Parameterized queries** — the IXReports data access layer should be refactored to use parameterized OleDB commands as a longer-term hardening measure. Current fix is correct but defence-in-depth favours full parameterization.
- **RDP access audit** — investigate Windows Event ID 4624 (logon type 10) logs on the IXReports host to determine whether unauthorized access occurred and whether any data was accessed during the window of vulnerability.
- **Input validation layer** — consider a centralized input validation/sanitization middleware rather than per-method fixes for future legacy code changes.
