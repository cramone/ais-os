# Customer Deletion — Implementation Plan

Branch suggestion: `feat/customer-deletion`

## Goal

Support soft delete (restorable) and hard delete (irreversible) of a `Customer`,
without orphaning ApiClients, Settings, sessions, or the MySQL physical user
created for Enterprise/apache-hash auth.

## Background / current state

- No delete capability exists today (no `DeleteCustomer*` in `ICustomerService`/`CustomerService`,
  no API endpoint, no UI action).
- `Customer` table (`migrations/mysql/001_CreateSchema.sql:85-96`) has no soft-delete column.
  `Name` uniqueness is enforced only in app code via `CustomerService.GetCustomerByNameAsync`
  (case-insensitive collation `utf8mb4_0900_ai_ci`), not a DB unique constraint — the existing
  `UNIQUE KEY NameId (Name(128), Id)` is composite with Id and doesn't block name reuse.
- `CustomerService.CreateAsync` (src/MagiqAuth.Services/Customers/CustomerService.cs:121-137)
  creates a physical MySQL user on customer creation when `DbProviderName == MySql`:
  ```
  CREATE USER '{customer.Name.ToLower()}'@'%' IDENTIFIED BY '{customerSettings.ApacheHash}';
  GRANT EXECUTE ON FUNCTION apacheHashForLogin TO '{customer.Name.ToLower()}'@'%';
  ```
  Errors here are caught and only logged — never surfaced. No `DROP USER` exists anywhere
  in the codebase today.
- FK dependencies on `Customer.Id`:
  - `UserCustomer.CustomerId` → `ON DELETE CASCADE` (001_CreateSchema.sql:359). Fine as-is.
  - `ApiClientCustomer.CustomerId` → `ON DELETE CASCADE` (005_AddApiClientTable.sql:74). Fine as-is.
  - `ApiClient.CustomerId` → no cascade rule, defaults to `RESTRICT`/`NO ACTION`
    (005_AddApiClientTable.sql:31). **Hard delete blocker** — must explicitly remove or
    reassign ApiClient rows first.
  - `Setting.CustomerId` → no FK constraint at all (001_CreateSchema.sql:280-287). Orphans
    silently on hard delete unless cleaned up explicitly.
- Cache: `GetAllCustomersAsync` result is cached via `CacheHelper.KeyForCustomerList()`
  (CustomerService.cs:143-163). `CacheHelper.FlushCustomer()` exists
  (MagiqAuth.Services/Caching/CacheHelper.cs:24-37) and must be called on any delete/restore.

## Design summary

Two-stage delete:
1. **Soft delete** — reversible, default UX for "delete customer". Keeps all child rows
   (Settings, UserCustomer, ApiClient, ApiClientCustomer) intact for restore. Revokes live
   tokens/sessions and disables ApiClients so a soft-deleted tenant can't authenticate.
2. **Hard delete** — only permitted on an already soft-deleted customer (recommend after a
   retention window, e.g. 30 days), or via explicit admin override. Irreversibly removes
   Customer + dependent rows + drops the MySQL physical user.

## Step 1 — Schema migration

New file: `migrations/mysql/006_AddCustomerSoftDelete.sql`

```sql
ALTER TABLE `Customer`
  ADD COLUMN `IsDeleted` bit(1) NOT NULL DEFAULT 0,
  ADD COLUMN `DeletedOnUtc` datetime(6) NULL;

ALTER TABLE `ApiClient`
  DROP FOREIGN KEY `FK_ApiClient_Customer_CustomerId`, -- confirm actual constraint name first
  ADD CONSTRAINT `FK_ApiClient_Customer_CustomerId`
    FOREIGN KEY (`CustomerId`) REFERENCES `Customer` (`Id`)
    ON DELETE RESTRICT ON UPDATE RESTRICT; -- explicit RESTRICT, no behavior change, just documents intent

ALTER TABLE `Setting`
  ADD CONSTRAINT `FK_Setting_Customer_CustomerId`
    FOREIGN KEY (`CustomerId`) REFERENCES `Customer` (`Id`)
    ON DELETE CASCADE ON UPDATE RESTRICT;
```

Notes:
- Confirm real FK constraint name for `ApiClient` before writing the `DROP FOREIGN KEY` line
  (`SHOW CREATE TABLE ApiClient;`).
- Adding the `Setting` FK retroactively may fail if orphaned `CustomerId` values already exist
  in production — run a `SELECT s.* FROM Setting s LEFT JOIN Customer c ON s.CustomerId = c.Id
  WHERE c.Id IS NULL` audit first and clean up before applying.
- Don't reuse `Customer.StatusId` for soft-delete — keep deletion state orthogonal to existing
  business status enum.

## Step 2 — Domain / EF mapping

- `MagiqAuth.Core/Domain/Customers/Customer.cs`: add `IsDeleted` (bool), `DeletedOnUtc` (DateTime?).
- `MagiqAuth.Data/Mapping/Customers/CustomerMap.cs` (or equivalent): map new columns.

## Step 3 — Service layer (`MagiqAuth.Services/Customers/CustomerService.cs`)

### 3a. Global read-path filtering

Add `IsDeleted == false` filter to:
- `GetAllCustomersAsync` (CustomerService.cs:143-163)
- `GetCustomerByNameAsync` (CustomerService.cs:206-220)
- Any other `_customerRepository.Table` query in this file and any other service/controller
  that resolves a customer by id/name for auth/token-issuance purposes (grep
  `_customerRepository.Table` and `GetCustomerByIdAsync` across `MagiqAuth.Services`,
  `MagiqAuth.IDP`, `MagiqAuth.Api`, `MagiqAuth.Web` before finishing this step).
- Add an explicit `includeDeleted` opt-in parameter for admin-only restore/list views.

### 3b. `SoftDeleteCustomerAsync(int customerId)`

```
1. Load customer (must allow deleted=false only — can't double soft-delete).
2. Set IsDeleted = true, DeletedOnUtc = UtcNow. Save.
3. Disable/revoke all ApiClient rows linked via ApiClientCustomer for this customer
   (set an existing "disabled"/"revoked" flag on ApiClient — confirm field name in
   MagiqAuth.Core/Domain/ApiClients/ApiClient.cs; add one via migration if absent).
4. Revoke IdentityServer4 PersistedGrants for:
   - All ApiClients scoped to this customer (client-credentials tokens).
   - All users whose ONLY customer link is this customer (sessions/refresh tokens).
   Use IdentityServer4's IPersistedGrantService / token revocation store — do NOT
   raw-delete PersistedGrant rows if a documented revocation API exists.
5. CacheHelper.FlushCustomer() + flush customer list cache key.
6. Log via ActivityLog (existing pattern in CustomerService) — "Customer soft-deleted".
```

Do **not** touch `UserCustomer`, `ApiClient`, `ApiClientCustomer`, `Setting`, or
`CustomerSettings` rows — they must survive for restore.

### 3c. `RestoreCustomerAsync(int customerId, string? newName = null)`

```
1. Load customer, require IsDeleted == true.
2. Determine target name: newName ?? customer.Name.
3. GetCustomerByNameAsync(targetName) (already filtered to IsDeleted=false per 3a) —
   if a live customer holds that name:
     - if caller didn't supply newName, throw a specific exception
       (e.g. CustomerNameConflictException) so the API/UI can prompt for a new name.
     - if newName supplied, re-validate it's not already taken either.
4. Update customer.Name = targetName if changed, IsDeleted = false, DeletedOnUtc = null.
5. Re-enable previously disabled ApiClient rows for this customer (mirror of 3b step 3).
6. CacheHelper.FlushCustomer().
7. Log "Customer restored" (+ name change if applicable).
```

Note: PersistedGrants revoked during soft delete stay revoked — restored customer's users/
clients re-authenticate normally; this is intended, not a bug.

### 3d. SQL username collision on name reuse (important — flagged design risk)

Today `CREATE USER` is keyed off `customer.Name.ToLower()` (CustomerService.cs:124). Soft
delete does NOT drop the MySQL user (can't — must survive for restore). If a new customer
is created reusing the same name while the old one is soft-deleted, `CreateAsync`'s
`CREATE USER` call will collide with the still-existing physical user for the old customer
and fail (currently fails silently — caught and only logged, per CustomerService.cs:129-136).

**Recommended fix: change the MySQL username scheme from `customer.Name` to a stable,
unique identifier — `customer.Id` or `customer.CustomerGuid`** (e.g. `cust_{customerGuid}`).
This decouples the physical DB user from the mutable/reusable `Name` field entirely and
eliminates the collision class permanently. This requires:
- Updating `CustomerService.CreateAsync` (line 124) to build username from `customer.Id`/Guid.
- Confirming nothing downstream (Enterprise apacheHashForLogin callers, any client config)
  assumes the MySQL username equals the customer name — grep `apacheHashForLogin` usage and
  any docs/config referencing `'{CustomerName}'@'%'` pattern before changing this.

If renaming the username scheme is out of scope for this change, the fallback is to make the
`CREATE USER` failure in `CreateAsync` non-silent (throw, don't just log) so a real naming
conflict blocks customer creation visibly instead of leaving a customer row with no working
SQL user.

### 3e. `HardDeleteCustomerAsync(int customerId)`

```
1. Load customer. Require IsDeleted == true (block hard-delete of a live customer;
   require explicit soft-delete-then-hard-delete flow). Optionally enforce minimum
   retention window since DeletedOnUtc (e.g. 30 days) unless an admin override flag passed.
2. Delete Setting rows where CustomerId == customerId (explicit delete; cascade from
   step 1's migration also covers this once Setting FK exists, but keep explicit code
   for auditability / pre-migration safety).
3. Delete ApiClient rows for this customer (ApiClientCustomer cascades automatically
   once ApiClient rows are gone, but ApiClientCustomer junction rows that point to OTHER
   customers via IsUnrestricted/shared clients must NOT be deleted blindly — only remove
   the rows scoped to this customer, not the ApiClient itself if it's shared/unrestricted
   across customers per the IsUnrestricted flag added in the client-credentials work).
   Concretely:
     - For ApiClients with IsUnrestricted = true or with other ApiClientCustomer rows
       pointing elsewhere: just delete the ApiClientCustomer junction row for this customer.
     - For ApiClients scoped ONLY to this customer: delete the ApiClient row outright
       (junction cascades).
4. Delete UserCustomer rows for this customer (cascades automatically per existing FK,
   but check for users left with zero UserCustomer rows afterward — flag, don't auto-delete
   the User; that's a separate cleanup concern).
5. DROP USER '{the same identifier scheme used in CreateAsync}'@'%'; — wrap in try/catch
   like CreateAsync does, but this failure should be louder (surfaced to caller / logged
   at Error with explicit "manual cleanup needed" note), since silently leaving a stale
   MySQL user is a security residue (unused login with valid password hash sitting in MySQL).
6. Delete CustomerSettings row(s) for this customer.
7. Delete the Customer row itself.
8. CacheHelper.FlushCustomer().
9. Log "Customer hard-deleted" with full audit detail (who, when, customer id/name) —
   this is irreversible, log generously.
```

Wrap steps 2-7 in a single DB transaction (`_dbContext` transaction scope) so a partial
failure doesn't leave the Customer row deleted with orphaned children, or vice versa.

## Step 4 — API / controller surface

- `MagiqAuth.Api/Controllers/CustomersV2Controller.cs` (or V1, confirm which is current):
  - `DELETE /api/v2/customers/{id}` → soft delete (default action).
  - `POST /api/v2/customers/{id}/restore` → restore, body accepts optional `newName`.
  - `DELETE /api/v2/customers/{id}/hard` → hard delete, admin-only authorization policy,
    requires customer already soft-deleted (service enforces, but gate at controller too
    with a clear 409/400 if not).
- Return `CustomerNameConflictException` as 409 Conflict with the conflicting name in the
  response body so UI can prompt for a new name on restore.

## Step 5 — UI (MagiqAuth.Web, Razor)

- Customer list/detail page: add "Delete" action (soft), confirmation dialog explaining
  it's restorable.
- Add a "Deleted Customers" admin view (uses `includeDeleted: true` query) with Restore action
  — restore flow should show a text input for new name only when the API returns the name
  conflict, not unconditionally.
- Hard delete: separate, more heavily gated admin-only screen, with typed-confirmation
  (type customer name to confirm) given irreversibility.

## Step 6 — Tests (`MagiqAuth.Services.Tests`)

- Soft delete: customer hidden from `GetAllCustomersAsync`/`GetCustomerByNameAsync` after
  delete; child rows (Settings, UserCustomer, ApiClient) still present in DB.
- Restore: same name available → restores cleanly; name taken by another live customer →
  throws conflict requiring newName; restore with newName succeeds and updates Name.
- Name reuse: create new customer with name matching a soft-deleted one succeeds at the
  app layer; explicitly test the MySQL `CREATE USER` path doesn't collide (this depends on
  resolving 3d — test should target whichever username scheme is chosen).
- ApiClient revocation on soft delete: token issuance fails for an ApiClient belonging to a
  soft-deleted customer; succeeds again after restore.
- Hard delete: blocked when customer is not already soft-deleted; cascades correctly for
  Settings/ApiClient/UserCustomer; shared/unrestricted ApiClients survive when one of several
  linked customers is hard-deleted, only the junction row is removed.

## Open decisions to confirm with user before implementing

1. MySQL username scheme change (3d) — confirm no external/Enterprise dependency assumes
   username == customer name before changing it.
2. Hard-delete retention window length (default 30 days) and whether an admin override
   bypassing it is wanted.
3. Exact authorization policy for hard-delete endpoint (likely a new "SuperAdmin"-tier claim
   — check existing claims model per `ed026f3 standardized claims AB#33710`).
4. Whether PersistedGrant revocation should go through an existing IdentityServer4
   revocation service already wired in this codebase, or needs new wiring — check
   `MagiqAuth.IDP` for existing `IPersistedGrantService` usage before step 3b.4.
