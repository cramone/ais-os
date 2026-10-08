# archive/

Local cold storage for legacy repos that are being **held, not migrated**, while we confirm whether anything depends on them.

## Layout

Two archive methods. Record which one was used in each repo's `ARCHIVE.md`.

**Full mirror** (default: history, multiple branches or LFS) — `scripts/archive-ado-repo.sh`
```
archive/<source-key>/<project>/<repo>/
  mirror.git/              bare mirror: all branches, tags and history
  <repo>.bundle            single-file portable copy (git bundle --all)
  <repo>.bundle.sha256     integrity checksum
  src/                     read-only checkout of the default branch
  archive-manifest.txt     generated: source URL, HEAD SHA, branches, tags, date
  ARCHIVE.md               notes: contents, dependency status, decision trail
```

**Zip snapshot** (single branch, history not needed) — ADO UI download
```
archive/<source-key>/<project>/<repo>/
  <repo>-<branch>.zip      snapshot of the branch tip
  ARCHIVE.md               must record the HEAD commit SHA and date, plus the zip's SHA-256
```

`<source-key>` matches the `source` value in `spec/repo-register.csv` (`infoxpert-ado`, `magiq-vs-ado`, `magiq-ado`, `github`).

**Creating the folder:** in the dashboard, open the repo (disposition `archive-in-place` or `decommission`) and click **Create archive folder**. It makes `archive/<source-key>/<project>/<repo>/` (the ADO project is the parent folder) with a starter `ARCHIVE.md` and refreshes the index below. Copy the zip in, click **Rescan files + SHA-256**, then set **2-location backup** once a second copy exists. Project and repo folder names have spaces turned into `-`. If one project has two repos with the same name, the repo folder gets `--<register id>`. **Delete folder…** removes an empty scaffold outright; a folder holding files is moved to `archive/.trash/<source>/<project>/` after you type its name, and an emptied project folder is removed.

`ARCHIVE.md` has a block between `<!-- rhk:status:start -->` and `<!-- rhk:status:end -->` that the dashboard keeps in sync with the register (disposition, status, 2-location backup, confirmation, file list, SHA-256). Write your notes outside that block.

## Rules

- Never overwrite an existing archive.
- Don't edit code in `src/` or in extracted zips. Anything that gets revived is copied into a new `mgq-` repo in the enterprise, never developed here.
- The register row stays `disposition=pending` until we've checked for consumers. Deleting at source needs Chase's written confirmation (triage rule 5).
- To restore a mirror: `git clone <repo>.bundle <dir>` or `git clone mirror.git <dir>`. To restore a zip: extract it and `git init` a new `mgq-` repo (there's no history to bring over).

## Archived repos (managed by the dashboard)

Regenerated automatically when an archive folder is created, deleted or rescanned. Don't edit between the markers.

<!-- rhk:index:start -->
| Source | Project | Repo | Reg. id | Disposition | 2-loc backup | Folder | Files |
|---|---|---|---|---|---|---|---|
| magiq-vs-ado | Extensions | Extensions | 1 | decommission | yes | `archive/magiq-vs-ado/Extensions/Extensions` | `Extensions.zip` |
| magiq-ado | Cloud Storage Gateway | Cloud Storage Gateway | 2 | archive-in-place | yes | `archive/magiq-ado/Cloud-Storage-Gateway/Cloud-Storage-Gateway` | `Cloud Storage Gateway.zip` |
| magiq-ado | Conversion | Conversion | 3 | decommission | yes | `archive/magiq-ado/Conversion/Conversion` | `Conversion.zip` |
| magiq-ado | Documents | DigitalSigning | 13 | decommission | yes | `archive/magiq-ado/Documents/DigitalSigning` | `DigitalSigning.zip` |
| magiq-ado | Documents | documents-client-models | 15 | decommission | — | `archive/magiq-ado/Documents/documents-client-models` | `documents-client-models.zip` |
| magiq-ado | Documents | DocumentsClient-obsolete | 17 | decommission | not-required | `archive/magiq-ado/Documents/DocumentsClient-obsolete` | `DocumentsClient-obsolete.zip` |
| magiq-ado | Documents | DocumentsExport | 18 | decommission | not-required | `archive/magiq-ado/Documents/DocumentsExport` | `Magiq.DocumentsExport.zip` |
| magiq-ado | Documents | Foundation | 21 | decommission | yes | `archive/magiq-ado/Documents/Foundation` | `Foundation.zip` |
| magiq-ado | Documents | OfficeAddins | 28 | decommission | yes | `archive/magiq-ado/Documents/OfficeAddins` | `OfficeAddins.zip` |
| magiq-ado | Extensions | Commands | 34 | decommission | yes | `archive/magiq-ado/Extensions/Commands` | `Commands.zip` |
| magiq-ado | Extensions | DomainModeling | 35 | decommission | yes | `archive/magiq-ado/Extensions/DomainModeling` | `DomainModeling.zip` |
| magiq-ado | Extensions | Extensibility | 36 | decommission | — | `archive/magiq-ado/Extensions/Extensibility` | `Extensibility.zip` |
| magiq-ado | Extensions | Messaging | 39 | decommission | — | `archive/magiq-ado/Extensions/Messaging` | `Messaging.zip` |
| magiq-ado | Extensions | Middleware | 40 | decommission | yes | `archive/magiq-ado/Extensions/Middleware` | `Middleware.zip` |
| magiq-ado | Extensions | Pagination | 41 | decommission | yes | `archive/magiq-ado/Extensions/Pagination` | `Pagination.zip` |
| magiq-ado | Extensions | Specifications | 42 | decommission | yes | `archive/magiq-ado/Extensions/Specifications` | `Specifications.zip` |
| magiq-ado | MAGIQ PowerShell | Deployment | 44 | decommission | yes | `archive/magiq-ado/MAGIQ-PowerShell/Deployment` | `Deployment.zip` |
| magiq-ado | MAGIQ PowerShell | Documents | 45 | decommission | yes | `archive/magiq-ado/MAGIQ-PowerShell/Documents` | `Documents.zip` |
| magiq-ado | MagiqSDK | MagiqSDK | 52 | decommission | not-required | `archive/magiq-ado/MagiqSDK/MagiqSDK` | `MagiqSDK.zip` |
| magiq-ado | UIComponents | WPF | 56 | decommission | yes | `archive/magiq-ado/UIComponents/WPF` | `WPF.zip` |
| infoxpert-ado | Applications | $/Applications | 59 | decommission | yes | `archive/infoxpert-ado/Applications/Applications` | `Applications.zip` |
| infoxpert-ado | Conversion Tools | $/Conversion Tools | 60 | decommission | yes | `archive/infoxpert-ado/Conversion-Tools/Conversion-Tools` | `Conversion Tools.zip` |
| infoxpert-ado | Document Navigator | $/Document Navigator | 61 | decommission | yes | `archive/infoxpert-ado/Document-Navigator/Document-Navigator` | `Document Navigator.zip` |
| infoxpert-ado | Documents Client API | $/Documents Client API | 62 | decommission | yes | `archive/infoxpert-ado/Documents-Client-API/Documents-Client-API` | `Documents Client API.zip` |
| infoxpert-ado | Enterprise Connector | $/Enterprise Connector | 63 | decommission | yes | `archive/infoxpert-ado/Enterprise-Connector/Enterprise-Connector` | `Enterprise Connector.zip` |
| infoxpert-ado | InfoXpert | $/InfoXpert | 65 | decommission | not-required | `archive/infoxpert-ado/InfoXpert/InfoXpert` | `InfoXpert.zip` |
| infoxpert-ado | InfoXpert Legacy | $/InfoXpert Legacy | 66 | decommission | yes | `archive/infoxpert-ado/InfoXpert-Legacy/InfoXpert-Legacy` | `InfoXpert Legacy.zip` |
| infoxpert-ado | Licensing | $/Licensing | 67 | decommission | yes | `archive/infoxpert-ado/Licensing/Licensing` | `Licensing.zip` |
| infoxpert-ado | MAGIQ Client Api | $/MAGIQ Client Api | 68 | decommission | not-required | `archive/infoxpert-ado/MAGIQ-Client-Api/MAGIQ-Client-Api` | `MAGIQ Client Api.zip` |
| infoxpert-ado | MAGIQ Conversion | MAGIQ Conversion | 69 | decommission | yes | `archive/infoxpert-ado/MAGIQ-Conversion/MAGIQ-Conversion` | `MAGIQ Conversion.zip` |
| infoxpert-ado | MAGIQ Documents | $/MAGIQ Documents | 70 | decommission | yes | `archive/infoxpert-ado/MAGIQ-Documents/MAGIQ-Documents` | `MAGIQ Documents.zip` |
| infoxpert-ado | MAGIQ Extensions | $/MAGIQ Extensions | 71 | decommission | yes | `archive/infoxpert-ado/MAGIQ-Extensions/MAGIQ-Extensions` | `MAGIQ Extensions.zip` |
| infoxpert-ado | MAGIQ Infrastructure | $/MAGIQ Infrastructure | 72 | decommission | yes | `archive/infoxpert-ado/MAGIQ-Infrastructure/MAGIQ-Infrastructure` | `MAGIQ Infrastructure.zip` |
| infoxpert-ado | MAGIQ Licensing | $/MAGIQ Licensing | 73 | decommission | — | `archive/infoxpert-ado/MAGIQ-Licensing/MAGIQ-Licensing` | `MAGIQ Licensing.zip` |
| infoxpert-ado | MAGIQ Software | $/MAGIQ Software | 74 | decommission | yes | `archive/infoxpert-ado/MAGIQ-Software/MAGIQ-Software` | `MAGIQ Software.zip` |
| infoxpert-ado | Support Tools | $/Support Tools | 75 | decommission | yes | `archive/infoxpert-ado/Support-Tools/Support-Tools` | `Support Tools.zip` |
<!-- rhk:index:end -->
