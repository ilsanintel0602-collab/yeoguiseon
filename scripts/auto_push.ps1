# ============================================================================
# yeoguiseon v4 - GitHub auto push (PowerShell)
# Usage: scripts/auto_push.bat (double-click) or PowerShell direct
# ============================================================================

$ErrorActionPreference = "Stop"
# Force UTF-8 output (prevent Korean garble)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 > $null 2>&1

$REPO_OWNER = "ilsanintel0602-collab"
$REPO_NAME = "yeoguiseon"
$BRANCH = "main"

# Resolve repo root as STRING (avoid PathInfo object issues)
$REPO_ROOT = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $REPO_ROOT
Write-Host "[OK] Repo root: $REPO_ROOT" -ForegroundColor Cyan

# ==================== 1. Load PAT ====================
$PAT_PATH = Join-Path $REPO_ROOT ".git_pat.txt"
if (-not (Test-Path $PAT_PATH)) {
    Write-Host "[ERR] .git_pat.txt not found at: $PAT_PATH" -ForegroundColor Red
    exit 1
}
$PAT = (Get-Content $PAT_PATH -Raw).Trim()
if ($PAT -notmatch '^(ghp_|github_pat_)') {
    Write-Host "[ERR] PAT format invalid. Regenerate at github.com/settings/tokens" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] PAT loaded (format verified)" -ForegroundColor Green

$Headers = @{
    "Authorization" = "token $PAT"
    "Accept" = "application/vnd.github.v3+json"
    "User-Agent" = "yeoguiseon-auto-push/1.0"
}
$API = "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME"

# ==================== 1.5 (v5.44): quick_check + auto_snapshot ====================
Write-Host "`n[1.5] quick_check + DB benchmark..." -ForegroundColor Cyan
# v5.45: Windows cp949 인코딩 문제 회피 — Python stdout UTF-8 강제
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$qcResult = & python "$REPO_ROOT\scripts\quick_check.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERR] quick_check FAILED. Push aborted." -ForegroundColor Red
    Write-Host "      Run: python scripts\auto_snapshot.py restore  (truncation 시)" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "[OK] quick_check PASS" -ForegroundColor Green
& python "$REPO_ROOT\scripts\auto_snapshot.py" save | Out-Null
Write-Host "[OK] snapshot saved" -ForegroundColor Green

# ==================== 2. Commit message ====================
$CommitMsg = Read-Host "`nCommit message (Enter for auto)"
if ([string]::IsNullOrWhiteSpace($CommitMsg)) {
    $CommitMsg = "Auto push @ $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
}
Write-Host "  -> $CommitMsg" -ForegroundColor Gray

# ==================== 3. Build file list (v5.18: 패턴 기반 자동 스캔) ====================
$Tracked = @("app.html", "sw.js", "index.html", "manifest.json", ".gitignore")

# HANDOFF_*.md
$h = Get-ChildItem -Path $REPO_ROOT -Filter "HANDOFF_*.md" -File -ErrorAction SilentlyContinue
if ($h) { foreach ($f in $h) { $Tracked = $Tracked + $f.Name } }

# data/*.json (백업 제외)
$d = Get-ChildItem -Path "$REPO_ROOT\data" -Filter "*.json" -File -ErrorAction SilentlyContinue
if ($d) { foreach ($f in $d) { if ($f.Name -notlike "*.backup_*") { $Tracked = $Tracked + ("data/" + $f.Name) } } }

# scripts (확장자 여러개 — v1.9 D1 인프라용 sql/toml/template 포함)
foreach ($ext in @("*.py", "*.bat", "*.js", "*.ps1", "*.md", "*.ipynb", "*.sql", "*.toml", "*.template")) {
    $s = Get-ChildItem -Path "$REPO_ROOT\scripts" -Filter $ext -File -ErrorAction SilentlyContinue
    if ($s) { foreach ($f in $s) { $Tracked = $Tracked + ("scripts/" + $f.Name) } }
}

# icons/*
$ic = Get-ChildItem -Path "$REPO_ROOT\icons" -File -ErrorAction SilentlyContinue
if ($ic) { foreach ($f in $ic) { $Tracked = $Tracked + ("icons/" + $f.Name) } }

# docs/*.md
$dc = Get-ChildItem -Path "$REPO_ROOT\docs" -Filter "*.md" -File -ErrorAction SilentlyContinue
if ($dc) { foreach ($f in $dc) { $Tracked = $Tracked + ("docs/" + $f.Name) } }

# .github/workflows/*.yml — PAT에 'workflow' scope 있을 때만 push (없으면 GitHub가 404)
# 권한 추가: github.com/settings/tokens → 토큰 편집 → workflow 체크
# 일단 자동 push에서 제외. 필요 시 GitHub 웹 UI(Add file → Create new file)로 수동 업로드.
# $gh = Get-ChildItem -Path "$REPO_ROOT\.github\workflows" -Filter "*.yml" -File -ErrorAction SilentlyContinue
# if ($gh) { foreach ($f in $gh) { $Tracked = $Tracked + (".github/workflows/" + $f.Name) } }

# data/migrations/*.sql (D1 initial migration)
$mg = Get-ChildItem -Path "$REPO_ROOT\data\migrations" -Filter "*.sql" -File -ErrorAction SilentlyContinue
if ($mg) { foreach ($f in $mg) { $Tracked = $Tracked + ("data/migrations/" + $f.Name) } }

# skills/**/SKILL.md
$sk = Get-ChildItem -Path "$REPO_ROOT\skills" -Filter "SKILL.md" -File -Recurse -ErrorAction SilentlyContinue
if ($sk) {
    foreach ($f in $sk) {
        $rel = $f.FullName.Substring($REPO_ROOT.Length + 1) -replace '\\', '/'
        $Tracked = $Tracked + $rel
    }
}

$TrackedFiles = $Tracked
$ExcludePatterns = @("*.backup_*.json", ".git_pat*", "_바탕화면_복사용*")

# Use ArrayList to avoid PowerShell += array quirks
$FilesToPush = New-Object System.Collections.ArrayList

foreach ($f in $TrackedFiles) {
    # Manual path join to avoid Join-Path with array side-effect
    $fullPath = "$REPO_ROOT\$($f -replace '/', '\')"
    if (-not (Test-Path -LiteralPath $fullPath)) { continue }
    $skip = $false
    $leaf = Split-Path $f -Leaf
    foreach ($pat in $ExcludePatterns) {
        if ($leaf -like $pat) { $skip = $true; break }
    }
    if (-not $skip) { [void]$FilesToPush.Add($f) }
}

Write-Host "`n[INFO] Files to push ($($FilesToPush.Count) files):"
foreach ($f in $FilesToPush) {
    $fullPath = "$REPO_ROOT\$($f -replace '/', '\')"
    $size = (Get-Item -LiteralPath $fullPath).Length
    $sizeStr = if ($size -gt 1MB) { "{0:N1} MB" -f ($size/1MB) } else { "{0:N1} KB" -f ($size/1KB) }
    Write-Host "  - $f ($sizeStr)" -ForegroundColor Gray
}

$Confirm = Read-Host "`nContinue? (Y/n)"
if ($Confirm -eq "n" -or $Confirm -eq "N") {
    Write-Host "Cancelled." -ForegroundColor Yellow
    exit 0
}

# ==================== 4. Get base commit + tree SHA ====================
Write-Host "`n[1/4] Fetching main branch state..."
$RefResp = Invoke-RestMethod -Uri "$API/git/refs/heads/$BRANCH" -Headers $Headers
$BaseCommitSHA = $RefResp.object.sha
Write-Host "  base commit: $($BaseCommitSHA.Substring(0,7))"

$BaseCommitResp = Invoke-RestMethod -Uri "$API/git/commits/$BaseCommitSHA" -Headers $Headers
$BaseTreeSHA = $BaseCommitResp.tree.sha
Write-Host "  base tree: $($BaseTreeSHA.Substring(0,7))"

# ==================== 5. Upload blobs ====================
Write-Host "`n[2/4] Uploading file blobs..."
$TreeEntries = @()
foreach ($f in $FilesToPush) {
    $fullPath = "$REPO_ROOT\$($f -replace '/', '\')"
    $bytes = [System.IO.File]::ReadAllBytes($fullPath)
    $base64 = [Convert]::ToBase64String($bytes)
    $body = @{ content = $base64; encoding = "base64" } | ConvertTo-Json -Compress
    $blobResp = Invoke-RestMethod -Uri "$API/git/blobs" -Headers $Headers -Method POST -Body $body -ContentType "application/json"
    Write-Host "  + $f -> $($blobResp.sha.Substring(0,7))" -ForegroundColor Gray
    $TreeEntries += @{
        path = $f
        mode = "100644"
        type = "blob"
        sha = $blobResp.sha
    }
}

# ==================== 6. Create new tree ====================
Write-Host "`n[3/4] Creating new tree..."
$TreeBody = @{
    base_tree = $BaseTreeSHA
    tree = $TreeEntries
} | ConvertTo-Json -Depth 5
$NewTreeResp = Invoke-RestMethod -Uri "$API/git/trees" -Headers $Headers -Method POST -Body $TreeBody -ContentType "application/json"
Write-Host "  new tree: $($NewTreeResp.sha.Substring(0,7))"

# ==================== 7. Create commit + update branch ref ====================
Write-Host "`n[4/4] Creating commit + pushing..."
$CommitBody = @{
    message = $CommitMsg
    tree = $NewTreeResp.sha
    parents = @($BaseCommitSHA)
} | ConvertTo-Json
$NewCommitResp = Invoke-RestMethod -Uri "$API/git/commits" -Headers $Headers -Method POST -Body $CommitBody -ContentType "application/json"

$UpdateBody = @{ sha = $NewCommitResp.sha; force = $false } | ConvertTo-Json
$UpdateResp = Invoke-RestMethod -Uri "$API/git/refs/heads/$BRANCH" -Headers $Headers -Method PATCH -Body $UpdateBody -ContentType "application/json"

Write-Host "`n[DONE] Push complete!" -ForegroundColor Green
Write-Host "  commit: https://github.com/$REPO_OWNER/$REPO_NAME/commit/$($NewCommitResp.sha)" -ForegroundColor Cyan
Write-Host "  GitHub Pages: 1-2 min later -> https://$REPO_OWNER.github.io/$REPO_NAME/" -ForegroundColor Cyan
Write-Host ""
