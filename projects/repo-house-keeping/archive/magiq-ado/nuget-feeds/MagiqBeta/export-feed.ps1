# ---- Configure these ----------------------------------------------------
$Org      = "MAGIQSoftware"
$Project  = ""                        # leave empty for org-scoped feeds
$Feed     = "MagiqBeta"
$Pat      = ""              # PAT with Packaging (Read). Set to $null to use az CLI (Entra) token
$OutDir   = ".\nupkgs"
$PageSize = 1000
# -------------------------------------------------------------------------

$ErrorActionPreference = "Stop"
$AdoResource = "499b84ac-1321-427f-aa17-267ca6975798"

$script:token     = $null
$script:tokenTime = [datetime]::MinValue

function Get-AuthHeader {
    if ($Pat) {
        $b64 = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(":$Pat"))
        return @{ Authorization = "Basic $b64" }
    }
    # Entra tokens last ~1h; refresh after 40 min
    if (-not $script:token -or ((Get-Date) - $script:tokenTime).TotalMinutes -gt 40) {
        $script:token = az account get-access-token --resource $AdoResource --query accessToken -o tsv
        if (-not $script:token) { throw "Failed to get token. Run 'az login' first." }
        $script:tokenTime = Get-Date
    }
    return @{ Authorization = "Bearer $($script:token)" }
}

$proj    = if ($Project) { "$Project/" } else { "" }
$feedApi = "https://feeds.dev.azure.com/$Org/${proj}_apis/packaging/feeds/$Feed"
$pkgApi  = "https://pkgs.dev.azure.com/$Org/${proj}_apis/packaging/feeds/$Feed/nuget/packages"

New-Item -ItemType Directory -Force $OutDir | Out-Null

# Enumerate all packages with all versions (paged)
Write-Host "Enumerating packages..."
$pkgs = @(); $skip = 0
do {
    $uri = "$feedApi/packages?includeAllVersions=true&`$top=$PageSize&`$skip=$skip&api-version=7.1"
    $r = Invoke-RestMethod $uri -Headers (Get-AuthHeader)
    $pkgs += $r.value
    $skip += $PageSize
} while ($r.count -ge $PageSize)

$versions = foreach ($p in $pkgs) {
    foreach ($v in $p.versions | Where-Object { -not $_.isDeleted }) {
        [pscustomobject]@{ Name = $p.name; Version = $v.version }
    }
}
Write-Host "Found $($pkgs.Count) packages, $(@($versions).Count) versions."

# Download (resumable: existing files are skipped)
$i = 0; $failed = @()
foreach ($v in $versions) {
    $i++
    $file = Join-Path $OutDir "$($v.Name).$($v.Version).nupkg"
    if (Test-Path $file) { continue }

    $url = "$pkgApi/$($v.Name)/versions/$($v.Version)/content?api-version=7.1-preview.1"
    try {
        Invoke-WebRequest $url -Headers (Get-AuthHeader) -OutFile $file
        Write-Host "[$i/$(@($versions).Count)] $($v.Name) $($v.Version)"
    } catch {
        if (Test-Path $file) { Remove-Item $file -Force }   # drop partial download
        $failed += "$($v.Name) $($v.Version): $($_.Exception.Message)"
        Write-Warning "Failed: $($v.Name) $($v.Version)"
    }
}

if ($failed) {
    Write-Host "`n$($failed.Count) failures:"
    $failed | ForEach-Object { Write-Host "  $_" }
    exit 1
}
Write-Host "Done. Output: $(Resolve-Path $OutDir)"
