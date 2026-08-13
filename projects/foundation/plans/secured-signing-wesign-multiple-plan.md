# Implementation Plan: WeSign — Multi-Document Verification and Fixes

**Solution:** `D:\source\azure\Documents\MagiqCMS-Old\Foundation.sln`  
**Plugin path:** `Foundation\InfoXpert.Web\Plugins\Foundation.SecuredSigning\`  
**All paths below are relative to the plugin root unless stated otherwise.**

> Companion plan: the ISign feature is covered separately in `secured-signing-isign-plan.md`.

---

## Background

The `Foundation.SecuredSigning` plugin integrates InfoRouter documents with the Secured Signing API (`https://www.securedsigning.com`, v1.4). It uses the `securedsigning.client` NuGet SDK (v1.5.0) via the `ExposedServiceClient` wrapper.

**WeSign** — send documents to external parties for signing. Multi-signer, async, notify callback.

This plan covers verifying and fixing the WeSign multi-document flow. The backend already supports multiple documents per package; the work here is confirming the end-to-end path works and cleaning up known gaps.

---

## Current State

The WeSign backend **already supports multiple documents per package**:

- `WeSignPackage` holds `ConcurrentDictionary<DocumentMetadata, WeSignSigningRequest>` (multiple signing requests per package).
- `ProvisionPackage` in `Services/SecuredSigningService.cs:551` iterates all `selectedRecords.RecordIds` in parallel, builds a list of `UploadRequestViewModel` objects, and creates an empty `WeSignPackage`.
- `Send.cshtml` already renders all `UploadRequests` via client-side `RequestUploader` JS, which loops and calls `POST /SecuredSigning/WeSign/UploadSigningRequest` for each document, then calls `POST /SecuredSigning/WeSign/CreateSigningRequest` to get the signing iFrame.
- `PackageReference` (passed to `showWeSign` in `Sign.cshtml:80`) contains all document references.

The flow: `Send` → upload loop (one AJAX per doc) → all uploaded → `CreateSigningRequest` → signing iFrame.

---

## Gaps to Fix

### 1. Remove `debugger;` statement from `Send.cshtml`

**File:** `Views/WeSign/Send.cshtml:119`  
```cshtml
// REMOVE this line:
debugger;
```
Production code with a `debugger;` statement will pause execution in any browser with DevTools open.

### 2. Verify `RequestUploader` JS component exists and handles multiple documents

The `Send.cshtml` instantiates `new RequestUploader({...})`. Verify this component:
- Lives in the plugin's Scripts folder or is loaded via RequireJS from the SS CDN
- Loops through all `UploadRequests` items
- Calls `POST /SecuredSigning/WeSign/UploadSigningRequest?packageId=X&documentId=Y` per document
- After all uploads succeed, calls `POST /SecuredSigning/WeSign/CreateSigningRequest?packageId=X&returnUrl=Y`
- Loads the returned iFrame URL into `#ssl-frame`

**If `RequestUploader` is missing or broken:**

In `Send.cshtml`, replace the `RequestUploader` block with explicit inline JS:

```javascript
(function () {
    var uploadRequests = @Html.Raw(Json.Encode(Model.UploadRequests));
    var packageId = '@Model.PackageId';
    var returnUrl = '@Model.ReturnUrl';
    var baseUrl = '@Url.Content("~")';
    var csrfToken = '@Html.AntiForgeryTokenValueInfoXpert()';
    var total = uploadRequests.length;
    var completed = 0;

    function uploadNext(index) {
        if (index >= total) {
            // All uploads done — get the signing iFrame
            $.post(baseUrl + 'SecuredSigning/WeSign/CreateSigningRequest', {
                packageId: packageId,
                returnUrl: returnUrl
            }, function (response) {
                if (response.Success) {
                    $('#ssl-frame').attr('src', response.IFrameUrl);
                    $('.preloader').fadeOut(function () { $('#ss-content').show(); });
                } else {
                    alert('Failed to create signing request: ' + response.Error);
                }
            });
            return;
        }
        var req = uploadRequests[index];
        $('.preloader .description').text('Uploading ' + req.DocumentName + ' (' + (index + 1) + ' of ' + total + ')');
        $.post(baseUrl + 'SecuredSigning/WeSign/UploadSigningRequest', {
            packageId: packageId,
            documentId: req.DocumentId.Id
        }, function (response) {
            if (response.Success) {
                completed++;
                uploadNext(index + 1);
            } else {
                alert('Failed to upload ' + req.DocumentName + ': ' + response.Error);
            }
        });
    }

    uploadNext(0);
})();
```

### 3. Verify `CreateEmbeddedWeSignViewModel` returns iFrame URL in JSON response

**File:** `Services/SecuredSigningService.cs:354`  
The `CreateSigningRequest` controller action returns `Json(viewModel)`. Ensure `EmbeddedWeSignViewResponse` includes `IFrameUrl`, `Success`, and `Error` properties accessible from JS.

Check `Services/ResponseMessages/EmbeddedWeSignViewResponse.cs` — if `IFrameUrl` is not a top-level serializable property, add it.

### 4. Confirm InfoRouter document list supports multi-select → WeSign

Check the InfoRouter action menu / EventHooks integration. The `Send` action accepts `SelectedRecords items` which comes from InfoRouter's multi-select document grid. Confirm the action menu entry for WeSign is registered with `AllowMultiple = true` (or equivalent InfoRouter attribute). This is likely in `Navigation/` or `Handlers/` — check those files and update the menu registration if needed.

---

## Verification — End-to-End Multi-Document Flow

Once the fixes above are in place, verify the complete path with more than one document selected:

1. Select 2+ documents in the InfoRouter document grid and invoke WeSign.
2. Confirm `ProvisionPackage` builds one `UploadRequestViewModel` per selected record and creates the empty `WeSignPackage`.
3. Confirm the upload loop issues one `UploadSigningRequest` AJAX call per document and each succeeds.
4. Confirm `CreateSigningRequest` fires only after all uploads complete and returns a valid `IFrameUrl`.
5. Confirm the signing iFrame loads and all documents appear in the package for the signer.

---

## Summary of Files to Modify / Verify

| Action | File |
|--------|------|
| Fix | `Views/WeSign/Send.cshtml:119` — remove `debugger;` |
| Verify | `RequestUploader` JS component loops all `UploadRequests` (replace with inline JS if broken) |
| Verify | `Services/ResponseMessages/EmbeddedWeSignViewResponse.cs` — exposes `IFrameUrl`, `Success`, `Error` |
| Verify | `Navigation/` or `Handlers/` — WeSign action menu supports multi-select |
| Verify | WeSign multi-doc end-to-end flow (see Verification section) |

---

## Key References

| Symbol | File | Line |
|--------|------|------|
| `ProvisionPackage` | `Services/SecuredSigningService.cs` | 551 |
| `AddDocumentToPackage` (upload pattern) | `Services/SecuredSigningService.cs` | 86 |
| `CreateEmbeddedWeSignViewModel` | `Services/SecuredSigningService.cs` | 354 |
| `WeSign Send view` | `Views/WeSign/Send.cshtml` | — |
| `WeSign Sign view` | `Views/WeSign/Sign.cshtml` | 80 |
| Routes | `Routes.cs` | — |
