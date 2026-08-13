# Implementation Plan: ISign — New Feature Implementation

**Solution:** `D:\source\azure\Documents\MagiqCMS-Old\Foundation.sln`  
**Plugin path:** `Foundation\InfoXpert.Web\Plugins\Foundation.SecuredSigning\`  
**All paths below are relative to the plugin root unless stated otherwise.**

> Companion plan: the WeSign multi-document verification/fixes are covered separately in `secured-signing-wesign-multiple-plan.md`.

---

## Background

The `Foundation.SecuredSigning` plugin integrates InfoRouter documents with the Secured Signing API (`https://www.securedsigning.com`, v1.4). It uses the `securedsigning.client` NuGet SDK (v1.5.0) via the `ExposedServiceClient` wrapper.

**ISign** — sole signatory: the *current user* signs a document themselves, inline in an embedded iFrame. No external signers, no notify callback from the SS server.

---

## Overview

ISign is a sole-signatory embedded signing flow. The current user uploads a document to Secured Signing, then signs it themselves via an embedded iFrame.

Infrastructure already in place:
- `AuthorizationScope.ISign` — `Client/Authorization/AuthorizationScope.cs:58`
- `EmbeddedUiResourceType.ISign = 14` — `Client/EmbeddedUiResourceType.cs:11`
- `GetEmbeddedUiResource(user, request)` — `Client/SecuredSigningSession.cs:143`

---

## Phase 1: ISign iFrame Request Class

**Create:** `Client/ISign/ISignIFrameRequest.cs`

```csharp
using Foundation.SecuredSigning.Client.Authorization;

namespace Foundation.SecuredSigning.Client.ISign
{
    public class ISignIFrameRequest : EmbeddedResourceRequest
    {
        public override EmbeddedUiResourceType ResourceType
        {
            get { return EmbeddedUiResourceType.ISign; }
        }

        public override AuthorizationScope Scope
        {
            get { return AuthorizationScope.ISign.And(AuthorizationScope.Basic); }
        }
    }
}
```

**Add to .csproj** — add a `<Compile Include="Client\ISign\ISignIFrameRequest.cs" />` entry in `Foundation.SecuredSigning.csproj` in the same `<ItemGroup>` as other `Client\WeSign\` entries.

---

## Phase 2: View Models

**Create:** `ViewModels/ISign/ISignViewModel.cs`

```csharp
using System;

namespace Foundation.SecuredSigning.ViewModels.ISign
{
    public class ISignViewModel : AuthorizedViewModel
    {
        public string IFrameUrl { get; set; }
        public string IFrameTitle { get; set; }
        public string DocumentReference { get; set; }
        public string DocumentName { get; set; }
        public string ReturnUrl { get; set; }
        public Exception UnhandledException { get; set; }
    }
}
```

**Create:** `ViewModels/ISign/SendISignViewModel.cs`

```csharp
using System;
using InfoXpert.Localization;

namespace Foundation.SecuredSigning.ViewModels.ISign
{
    public class SendISignViewModel : AuthorizedViewModel
    {
        public string DocumentName { get; set; }
        public int DocumentId { get; set; }
        public string ReturnUrl { get; set; }
        public LocalizedString SelectionError { get; set; }
        public Exception UnhandledException { get; set; }

        public bool HasError()
        {
            return UnhandledException != null || SelectionError != null;
        }
    }
}
```

**Add both to .csproj** in the `<ItemGroup>` containing other `ViewModels\WeSign\` entries.

---

## Phase 3: Service Layer

### 3a. Add ISign methods to `ISecuredSigningService`

**File:** `Services/ISecuredSigningService.cs`

Add to the interface:

```csharp
/// <summary>
/// Provisions an ISign request — uploads the document to Secured Signing.
/// </summary>
/// <param name="recordId">The document record identifier.</param>
/// <returns>The <see cref="ProvisionISignResponse" />.</returns>
ProvisionISignResponse ProvisionISign(RecordId recordId);

/// <summary>
/// Creates the ISign view model for the signing iFrame.
/// </summary>
/// <param name="documentReference">The document reference from ProvisionISign.</param>
/// <param name="documentName">The document name.</param>
/// <param name="returnUrl">The return URL after signing.</param>
/// <returns>The <see cref="ISignViewModel" />.</returns>
ISignViewModel CreateISignViewModel(string documentReference, string documentName, string returnUrl = null);
```

### 3b. Create response message

**Create:** `Services/ResponseMessages/ProvisionISignResponse.cs`

```csharp
using InfoXpert.Localization;

namespace Foundation.SecuredSigning.Services.ResponseMessages
{
    public class ProvisionISignResponse
    {
        public bool Success { get; private set; }
        public string DocumentReference { get; private set; }
        public string DocumentName { get; private set; }
        public LocalizedString Error { get; private set; }

        public static ProvisionISignResponse Succeeded(string documentReference, string documentName)
        {
            return new ProvisionISignResponse { Success = true, DocumentReference = documentReference, DocumentName = documentName };
        }

        public static ProvisionISignResponse Failed(LocalizedString error)
        {
            return new ProvisionISignResponse { Success = false, Error = error };
        }
    }
}
```

**Add to .csproj** alongside other `Services\ResponseMessages\` entries.

### 3c. Implement in `SecuredSigningService`

**File:** `Services/SecuredSigningService.cs`

Add the following methods. The `using` statement for `Foundation.SecuredSigning.Client.ISign` and `Foundation.SecuredSigning.ViewModels.ISign` must be added at the top of the file.

```csharp
/// <inheritdoc />
public ProvisionISignResponse ProvisionISign(RecordId recordId)
{
    if (recordId == null)
    {
        throw new ArgumentNullException("recordId");
    }

    var workContext = _workContextAccessor.GetContext();
    if (workContext.CurrentUser == null)
    {
        return ProvisionISignResponse.Failed(T("You must be signed in to use ISign."));
    }

    var document = _infoRouter.DocumentService.GetDocument(recordId);
    if (document == null)
    {
        return ProvisionISignResponse.Failed(T("Document not found."));
    }

    using (var session = _client.OpenSession())
    {
        DocumentStore documentStore;
        try
        {
            documentStore = session.OpenDocumentStore(workContext.CurrentUser);
        }
        catch (Exception ex)
        {
            Logger.Error(ex, "Failed to open document store for ISign.");
            return ProvisionISignResponse.Failed(T("Failed to connect to Secured Signing. Ensure your account is authorized."));
        }

        var metadata = new DocumentMetadata(document.Name, recordId.Id, document.Version);
        var clientRef = new ClientReference(metadata);

        try
        {
            // Upload the document — same mechanism as WeSign
            var documentReference = documentStore.UploadDocument(metadata, () => _infoRouter.DocumentService.OpenRead(recordId), clientRef);
            return ProvisionISignResponse.Succeeded(documentReference.ToString(), document.Name);
        }
        catch (Exception ex)
        {
            Logger.Error(ex, "Failed to upload document id {0} for ISign.", recordId);
            return ProvisionISignResponse.Failed(T("Failed to upload document for signing."));
        }
    }
}

/// <inheritdoc />
public ISignViewModel CreateISignViewModel(string documentReference, string documentName, string returnUrl = null)
{
    var viewModel = CreateAuthorizedViewModel<ISignViewModel>(returnUrl);
    if (!viewModel.IsAuthorized)
    {
        return viewModel;
    }

    var workContext = _workContextAccessor.GetContext();
    using (var session = _client.OpenSession())
    {
        try
        {
            // Get the ISign embedded UI iFrame URL (resource type 14)
            var embeddedResource = session.GetEmbeddedUiResource(workContext.CurrentUser, new ISignIFrameRequest());
            viewModel.IFrameTitle = embeddedResource.Name;
            viewModel.IFrameUrl = embeddedResource.Url;
        }
        catch (Exception ex)
        {
            Logger.Error(ex, "Failed to load ISign embedded iFrame resource.");
            viewModel.UnhandledException = ex;
            return viewModel;
        }

        viewModel.DocumentReference = documentReference;
        viewModel.DocumentName = documentName;
        viewModel.ReturnUrl = returnUrl;
        viewModel.SecuredSigningBaseUrl = _client.GetSettings().ServiceBaseUrl;
    }

    return viewModel;
}
```

> **Note:** `ISignViewModel` needs a `SecuredSigningBaseUrl` property — add `public string SecuredSigningBaseUrl { get; set; }` to `ViewModels/ISign/ISignViewModel.cs`.  
> **Note:** `session.GetEmbeddedUiResource` is defined on `SecuredSigningSession` (implements `ISecuredSigningUiResources`) but NOT exposed on `ISecuredSigningSession`. Either:
> - Cast the session: `((ISecuredSigningUiResources)session).GetEmbeddedUiResource(...)`
> - OR add `GetEmbeddedUiResource` to `ISecuredSigningSession` interface (`Client/ISecuredSigningSession.cs`)
> The second option is cleaner. Add to `ISecuredSigningSession`:
> ```csharp
> EmbeddedUiResource GetEmbeddedUiResource(IUser user, EmbeddedResourceRequest request);
> ```

---

## Phase 4: Controller

**Create:** `Controllers/ISignController.cs`

```csharp
using System;
using System.Web.Mvc;
using Foundation.SecuredSigning.Services;
using Foundation.SecuredSigning.ViewModels.ISign;
using InfoXpert.ActiveInnovations.Models;
using InfoXpert.ActiveInnovations.Security;
using InfoXpert.Localization;
using InfoXpert.Logging;
using InfoXpert.Mvc;
using InfoXpert.Mvc.AntiForgery;
using InfoXpert.Runtime;
using InfoXpert.UI.Themes;

namespace Foundation.SecuredSigning.Controllers
{
    [Themed(Layout = "SecuredSigning", Enabled = true)]
    [AntiForgeryIgnore]
    public class ISignController : Controller
    {
        private readonly ISecuredSigningService _securedSigningService;
        private readonly Work<IInfoRouterServices> _infoRouter;

        public ISignController(ISecuredSigningService securedSigningService, Work<IInfoRouterServices> infoRouter)
        {
            _securedSigningService = securedSigningService;
            _infoRouter = infoRouter;
            Logger = NullLogger.Instance;
            T = NullLocalizer.Instance;
        }

        public ILogger Logger { get; set; }
        public Localizer T { get; set; }

        /// <summary>
        /// Entry point: provisions document, then shows the signing iFrame.
        /// Accepts a single document (ISign is sole signatory — one doc per session).
        /// </summary>
        [InfoRouterAuthorize("items")]
        [AntiForgeryIgnore]
        [ValidateInput(false)]
        public ActionResult Sign(SelectedRecords items, string returnUrl)
        {
            if (string.IsNullOrEmpty(returnUrl))
            {
                returnUrl = _infoRouter.Value.GenerateReturnUrl(Request);
            }

            var workContext = HttpContext.GetWorkContext();
            if (workContext.CurrentUser == null)
            {
                return new HttpUnauthorizedResult();
            }

            // ISign supports a single document — take first selected
            if (items == null || !items.HasAtLeastOneRecord())
            {
                return View(new ISignViewModel
                {
                    IsAuthorized = true,
                    UnhandledException = new InvalidOperationException("No document selected.")
                });
            }

            var recordId = items.RecordIds[0];

            // Step 1: upload document to SS
            var provisionResult = _securedSigningService.ProvisionISign(recordId);
            if (!provisionResult.Success)
            {
                return View(new ISignViewModel
                {
                    IsAuthorized = true,
                    UnhandledException = new Exception(provisionResult.Error.ToString())
                });
            }

            // Step 2: get signing iFrame view model
            ISignViewModel viewModel;
            try
            {
                viewModel = _securedSigningService.CreateISignViewModel(
                    provisionResult.DocumentReference,
                    provisionResult.DocumentName,
                    returnUrl);
            }
            catch (Exception ex)
            {
                viewModel = new ISignViewModel
                {
                    IsAuthorized = true,
                    UnhandledException = ex,
                    ReturnUrl = returnUrl
                };
            }

            return View(viewModel);
        }
    }
}
```

**Add to .csproj** alongside other `Controllers\` entries.

---

## Phase 5: Routes

**File:** `Routes.cs`

Add an ISign route to `GetDefaultRoutes()` **before** the generic `SecuredSigning/{action}` catch-all:

```csharp
new RouteDescriptor
{
    Priority = 5,
    Route = new Route("SecuredSigning/ISign/{action}",
        new RouteValueDictionary
        {
            {"area", "Foundation.SecuredSigning"},
            {"controller", "ISign"}
        },
        new RouteValueDictionary(),
        new RouteValueDictionary
        {
            {"area", "Foundation.SecuredSigning"}
        },
        new MvcRouteHandler())
},
```

---

## Phase 6: Views

**Create directory:** `Views/ISign/`

**Create:** `Views/ISign/Sign.cshtml`

```cshtml
@using InfoXpert.Utility.Extensions
@model Foundation.SecuredSigning.ViewModels.ISign.ISignViewModel
@{
    Script.Require("jquery");
    Script.Require("jqueryPostMessage");
    Style.Require("securedSigning");
    Script.Require("securedSigning");
    Style.Include("securedSigning-auth.css");
    Layout.Title = T("Document Signing - I Sign");
    if (string.IsNullOrEmpty(Model.ReturnUrl) && Request["ReturnUrl"] != null)
    {
        Model.ReturnUrl = Request["ReturnUrl"];
    }
}

@if (!Model.IsAuthorized)
{
    @Html.Partial("~/Plugins/Foundation.SecuredSigning/Views/WeSign/AuthorizePartial.cshtml", Model)
}
else if (Model.UnhandledException != null)
{
    using (Capture(Layout.Header))
    {
        if (!string.IsNullOrEmpty(Model.ReturnUrl))
        {
            <a class="back-button" id="back-button" href="@Model.ReturnUrl">@T("Back")</a>
        }
        <h1 id="page-title">@T("I Sign")</h1>
    }
    <div class="ss-page">
        <div class="alert alert-danger">
            @T("An error occurred while preparing your document for signing.")
        </div>
        <div>
            <strong>@T("Error Details:")</strong>
            <p>@Model.UnhandledException.Message</p>
        </div>
        @T("There may be more information in the logs.")
    </div>
}
else
{
    if (!string.IsNullOrEmpty(Model.ReturnUrl))
    {
        <a href="@Model.ReturnUrl" class="back-button over-iframe" id="back-button">@T("Back")</a>
    }

    @Display(New.PreLoader(Title: T("Preparing document for signing...")))
    <div id="ss-content" style="height: 100%; position: absolute; width: 100%;">
        <iframe id="ssl-frame"
                documentName="@Model.IFrameTitle"
                style="border: none; height: 100%; position: relative; width: 100%;">
        </iframe>
    </div>

    using (Script.Foot())
    {
        <script data-main="https://api.securedsigning.com/web/v1.4/client/scripts/main"
                src="https://api.securedsigning.com/web/v1.4/client/scripts/require.js"></script>
        <script type="text/javascript">
        (function ($) {
            var iframeManager = new SecuredSigningIFrameManager({
                iframeEl: "#ssl-frame"
            });

            // Show the ISign embedded UI.
            // iframeManager.showISign loads the ISign embedded control (resource type 14).
            // The DocumentReference identifies the document the user is signing.
            // See SS SDK docs for showISign / getISignResource signature.
            iframeManager.showISign(
                '@Model.IFrameUrl',
                '@Model.DocumentReference',
                '@Model.ReturnUrl',
                function () {
                    // iFrame loaded — hide preloader
                    $('.preloader').fadeTo(250, 0, function () { $(this).hide(); });
                }
            );
        })(jQuery);
        </script>
    }
}
```

> **IMPORTANT — SDK method verification required:**  
> The `iframeManager.showISign(...)` call above mirrors the WeSign `showWeSign(...)` pattern. Before coding this, verify what method the `SecuredSigningIFrameManager` exposes for ISign by:
> 1. Checking `Scripts/jquery.securedSigning.js` for `showISign`, `getISignResource`, or `iSign` method signatures.
> 2. Reviewing the SS API docs for the v1.4 ISign embedded control flow.  
> 
> From `jquery.securedSigning.js:802-806`:
> ```javascript
> SecuredSigning.prototype.getISignResource = function (requestData, containerId, onError) {
>     window.requestInfo = requestData;
>     window.containerId = containerId;
>     this.getUIResource(14, onError);
> }
> ```
> `requestData` has a `DocumentReference` property (string). The `containerId` is the CSS selector for the iFrame container.  
> Adapt the view's JS to use this API if `SecuredSigningIFrameManager.showISign` doesn't exist:
> ```javascript
> var ss = new SecuredSigning({ /* config */ });
> ss.getISignResource({ DocumentReference: '@Model.DocumentReference' }, '#ssl-frame', function(err) {
>     alert('Error loading ISign: ' + err);
> });
> ```

---

## Phase 7: Register ISign in Navigation / EventHooks

To expose ISign as an action in the InfoRouter document list (right-click menu), check:

**File:** `Navigation/` — find the file that registers WeSign menu items. It likely uses `INavigationProvider` or similar InfoRouter navigation API. Add an ISign entry pointing to `ISignController.Sign` with single-document selection constraint.

**File:** `Handlers/` — if WeSign has a content part handler, check if ISign needs one (unlikely — ISign has no persistent state unless you add audit tables).

---

## Optional: ISign Audit Trail (DB Persistence)

If you want history of ISign operations (similar to WeSign's `WeSignPackageRequests` table):

### Migration

**File:** `Migrations.cs` — add `UpdateFrom2()`:

```csharp
public int UpdateFrom2()
{
    SchemaBuilder.CreateTable("ISignRequests", table => table
        .Column<int>("Id", column => column.Identity().PrimaryKey())
        .Column<DateTime>("CreatedDateUtc")
        .Column<string>("DocumentId")
        .Column<string>("DocumentName", column => column.WithLength(128))
        .Column<string>("DocumentReference")
        .Column<string>("DocumentVersion")
        .Column<bool>("IsComplete")
        .Column<DateTime>("SignedDateUtc", column => column.Nullable())
        .Column<string>("SignedDocumentId")
        .Column<string>("Status")
        .Column<int>("UserPartRecord_Id")
    );
    return 3;
}
```

> **Only add this if you need audit history.** ISign can function statelessly — upload doc, get iFrame URL, user signs, done. For the first implementation, defer the DB table.

---

## ISign Completion Callback (Post-Signing)

### Determine callback mechanism

ISign (sole signatory) may use one of:

**Option 1 — postMessage (client-side):** After signing, SS iFrame sends a `window.postMessage` to the parent frame. Handle in the view's JS:
```javascript
jQuery.receiveMessage(function (msg) {
    var data = msg.data;
    // data.status === 'completed' or similar
    window.location.href = '@Model.ReturnUrl';
}, 'https://www.securedsigning.com');
```
This is the `getISignResource2` pattern from `jquery.securedSigning.js:807`.

**Option 2 — Server notify callback:** SS calls a server endpoint (like `WeSign/NotifyCallback`). If SS ISign sends server-side callbacks, add a `NotifyCallback` action to `ISignController` following the same pattern as `WeSignController.NotifyCallback`. This would require the notify URL to be passed into the iFrame call.

Check the SS API docs to determine which mechanism ISign uses. `getISignResource2` uses postMessage (`receiveMessage`) so **Option 1 is more likely**.

---

## Summary of Files to Create / Modify

| Action | File |
|--------|------|
| Create | `Client/ISign/ISignIFrameRequest.cs` |
| Create | `ViewModels/ISign/ISignViewModel.cs` |
| Create | `ViewModels/ISign/SendISignViewModel.cs` |
| Create | `Services/ResponseMessages/ProvisionISignResponse.cs` |
| Create | `Controllers/ISignController.cs` |
| Create | `Views/ISign/Sign.cshtml` |
| Modify | `Services/ISecuredSigningService.cs` — add `ProvisionISign`, `CreateISignViewModel` |
| Modify | `Services/SecuredSigningService.cs` — implement those methods |
| Modify | `Client/ISecuredSigningSession.cs` — expose `GetEmbeddedUiResource` on interface |
| Modify | `Routes.cs` — add ISign route |
| Modify | `Foundation.SecuredSigning.csproj` — add new files |
| Modify | `Navigation/` — add ISign menu entry |
| Optional | `Migrations.cs` — add `UpdateFrom2()` for ISign audit table |

---

## Key References

| Symbol | File | Line |
|--------|------|------|
| `AuthorizationScope.ISign` | `Client/Authorization/AuthorizationScope.cs` | 58 |
| `EmbeddedUiResourceType.ISign` | `Client/EmbeddedUiResourceType.cs` | 11 |
| `GetEmbeddedUiResource` (impl) | `Client/SecuredSigningSession.cs` | 143 |
| `WeSignIFrameRequest` (pattern to copy) | `Client/WeSign/WeSignIFrameRequest.cs` | — |
| `ProvisionPackage` (pattern to copy) | `Services/SecuredSigningService.cs` | 551 |
| `AddDocumentToPackage` (upload pattern) | `Services/SecuredSigningService.cs` | 86 |
| `ISign JS endpoints` | `Scripts/jquery.securedSigning.js` | 775–810 |
| `WeSign Send view` (pattern for ISign view) | `Views/WeSign/Send.cshtml` | — |
| `WeSign Sign view` (pattern for ISign sign view) | `Views/WeSign/Sign.cshtml` | — |
| DB migrations | `Migrations.cs` | — |
| Routes | `Routes.cs` | — |
