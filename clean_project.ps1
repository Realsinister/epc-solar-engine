# clean_project.ps1
# One-click cleanup for pv-epd-pipeline:
# - Create _backup_unused/
# - Move unused/experimental scripts into backup
# - Add _backup_unused/ to .gitignore
# - Commit + push changes to GitHub (if git is available and repo configured)

param(
    [switch]$NoGit  # run as .\clean_project.ps1 -NoGit to skip git steps
)

$ErrorActionPreference = "Stop"

# Go to project root (folder where this script lives)
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot
Write-Host "Project root: $projectRoot"

# 1) Ensure backup folder exists
$backupDir = "_backup_unused"
if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir | Out-Null
    Write-Host "Created backup folder: $backupDir"
} else {
    Write-Host "Backup folder already exists: $backupDir"
}

# 2) List of candidate files to move to backup
#    (Safe: each is only moved if it actually exists)
$obsoleteFiles = @(
    "gwp_from_archives.py",
    "gwp_from_archives_v2.py",
    "rehydrate_archives.py",
    "rehydrate_archives_force.py",
    "eco_ui_harvest.py",
    "eco_login_capture.py",
    "epd_pull_eco_portal_bulk.py",
    "epd_pull_oekobaudat.py",
    "scan_oekobaudat_for_pv.py",
    "audit_archives.py"
)

foreach ($f in $obsoleteFiles) {
    $src = Join-Path $projectRoot $f
    if (Test-Path $src) {
        $dst = Join-Path $projectRoot $backupDir
        Move-Item -Path $src -Destination $dst -Force
        Write-Host "Moved $f -> $backupDir"
    } else {
        Write-Host "Skip (not found): $f"
    }
}

# 3) Ensure _backup_unused/ is ignored by git
$gitignorePath = Join-Path $projectRoot ".gitignore"
$ignoreLine = "_backup_unused/"

if (Test-Path $gitignorePath) {
    $content = Get-Content $gitignorePath
    if ($content -notcontains $ignoreLine) {
        Add-Content $gitignorePath "`n$ignoreLine"
        Write-Host "Added '$ignoreLine' to .gitignore"
    } else {
        Write-Host "'$ignoreLine' already present in .gitignore"
    }
} else {
    Set-Content $gitignorePath "$ignoreLine`n"
    Write-Host "Created .gitignore with '$ignoreLine'"
}

# 4) Git commit + push (optional)
if (-not $NoGit) {
    $gitCmd = Get-Command git -ErrorAction SilentlyContinue
    if (-not $gitCmd) {
        Write-Host "git is not installed or not in PATH; skipping git steps."
    } else {
        $insideRepo = git rev-parse --is-inside-work-tree 2>$null
        if ($LASTEXITCODE -eq 0 -and $insideRepo.Trim() -eq "true") {
            Write-Host "Git repository detected. Staging changes..."
            git add -A

            # Try to commit; if nothing to commit, git returns non-zero
            git commit -m "Housekeeping: move unused scripts to _backup_unused" 2>$null
            if ($LASTEXITCODE -ne 0) {
                Write-Host "No changes to commit (or commit failed)."
            } else {
                Write-Host "Commit created. Attempting git push..."
                git push 2>$null
                if ($LASTEXITCODE -ne 0) {
                    Write-Host "git push failed (no remote/credentials/branch mismatch). Check git config manually."
                } else {
                    Write-Host "git push succeeded."
                }
            }
        } else {
            Write-Host "Not inside a git repository; skipping git commit/push."
        }
    }
} else {
    Write-Host "Git steps disabled by -NoGit."
}

Write-Host "Cleanup completed."
