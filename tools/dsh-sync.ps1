<#
.SYNOPSIS
  One-command sync for the 3-person hackathon repo. ASCII output on purpose
  (Windows PowerShell 5.1 mangles non-ASCII script text).

.DESCRIPTION
  start  : pull what the others pushed, then print the progress board and your handoff card.
  end    : stage everything, commit as your role, rebase on the others, push.
  status : read-only snapshot (board head, dirty files, recent commits).

  The script never edits anything for you: updating 进度看板.md and 交接\<role>.md
  is your job, the script only moves them between machines.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\dsh-sync.ps1 -Name P2 -Action start

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\dsh-sync.ps1 -Name P2 -Action end -Message "tick 12 rows done"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('P1', 'P2', 'P3')]
    [string]$Name,

    [Parameter(Mandatory = $true)]
    [ValidateSet('start', 'end', 'status')]
    [string]$Action,

    [string]$Message = ''
)

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false } catch { }

function Write-Step([string]$Text) {
    Write-Host ''
    Write-Host "== $Text" -ForegroundColor Cyan
}
function Write-Note([string]$Text) { Write-Host "   $Text" -ForegroundColor DarkGray }
function Write-Warn2([string]$Text) { Write-Host "   $Text" -ForegroundColor Yellow }

# --- locate repo -------------------------------------------------------------
$top = & git rev-parse --show-toplevel 2>$null
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($top)) {
    throw 'Not a git repository. Run this inside the shared repo (Y:\hks on P2, your clone elsewhere).'
}
Set-Location $top.Trim()
$root = (Get-Location).Path

$board = '进度看板.md'
$handoff = Join-Path '交接' "$Name.md"

function Test-HasRemote {
    $names = @(& git remote)
    return ($names -contains 'origin')
}
function Test-HasCommit {
    & git rev-parse --verify HEAD *> $null
    return ($LASTEXITCODE -eq 0)
}

function Show-Board([int]$Lines) {
    Write-Step "Progress board: $board"
    if (Test-Path $board) {
        Get-Content -Encoding UTF8 -Path $board | Select-Object -First $Lines | ForEach-Object { Write-Host $_ }
        if ($Lines -lt 1000) { Write-Note "(first $Lines lines; open the file for the rest)" }
    }
    else { Write-Warn2 "MISSING $board - the repo is incomplete." }
}

function Show-Handoff([int]$Lines) {
    Write-Step "Your handoff card: $handoff"
    if (Test-Path $handoff) {
        Get-Content -Encoding UTF8 -Path $handoff | Select-Object -First $Lines | ForEach-Object { Write-Host $_ }
    }
    else { Write-Warn2 "MISSING $handoff - create it before you start." }
}

function Show-Log([int]$Count) {
    Write-Step "Recent commits"
    if (Test-HasCommit) { & git --no-pager log --oneline -n $Count } else { Write-Note 'no commits yet' }
}

# --- start -------------------------------------------------------------------
if ($Action -eq 'start') {
    if (Test-HasRemote) {
        Write-Step 'Pulling what the others pushed'
        & git pull --rebase --autostash
        if ($LASTEXITCODE -ne 0) {
            Write-Warn2 'PULL FAILED - you may have conflicts. Do not type over them:'
            Write-Warn2 '  git status  ->  fix the file  ->  git add <file>  ->  git rebase --continue'
            Write-Warn2 '  still confusing? git rebase --abort  then ask P1 to merge with you.'
        }
    }
    else {
        Write-Note 'No "origin" remote yet - skipping pull (share the repo before you rely on it).'
    }

    Show-Board 40
    Show-Handoff 16
    Show-Log 8

    Write-Step 'Checkpoints'
    Write-Note '19:30 end-to-end link / 00:30 accuracy / 09:00 deliverables / 11-22 15:00 freeze / 21:00 submit'
    Write-Note ("Now: " + (Get-Date -Format 'yyyy-MM-dd HH:mm'))
    Write-Host ''
    Write-Host 'Next: do the work, then update the board + your card and run -Action end.' -ForegroundColor Green
}

# --- end ---------------------------------------------------------------------
elseif ($Action -eq 'end') {
    Write-Step 'Changes to be shared'
    & git status --short
    if (-not (Test-Path $board)) { Write-Warn2 "You have no $board - your progress stays invisible." }

    & git add -A
    $staged = @(& git diff --cached --name-only)
    if ($staged.Count -eq 0) {
        Write-Note 'Nothing to commit.'
        Write-Note 'Did you forget to update the progress board and your handoff card?'
    }
    else {
        $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm'
        if ([string]::IsNullOrWhiteSpace($Message)) { $msg = "[$Name] sync $stamp" }
        else { $msg = "[$Name] $Message ($stamp)" }

        & git -c "user.name=$Name" -c "user.email=$Name@hks.local" commit -m $msg
        if ($LASTEXITCODE -ne 0) { throw 'commit failed' }
        Write-Step "Committed"
        Write-Note $msg
        Write-Note ("files: " + ($staged -join ', '))
    }

    if (Test-HasRemote) {
        if (Test-HasCommit) {
            Write-Step 'Rebasing on top of the others'
            & git pull --rebase --autostash
            if ($LASTEXITCODE -ne 0) {
                Write-Warn2 'CONFLICT - nothing pushed. Resolve:'
                Write-Warn2 '  git status  ->  fix the file  ->  git add <file>  ->  git rebase --continue'
                Write-Warn2 '  or: git rebase --abort  and merge with P1.'
                return
            }
        }
        Write-Step 'Pushing'
        & git push
        if ($LASTEXITCODE -ne 0) {
            Write-Warn2 'PUSH FAILED - check the remote URL and your account/token.'
            Write-Warn2 '  git remote -v'
        }
        else {
            Write-Note 'Pushed. The others see it on their next -Action start.'
        }
    }
    else {
        Write-Step 'No "origin" remote yet'
        Write-Note 'Create one PRIVATE repo, then run:'
        Write-Note '  git remote add origin <repo-url>'
        Write-Note '  git push -u origin main'
    }
}

# --- status ------------------------------------------------------------------
elseif ($Action -eq 'status') {
    Write-Note ("Repo: " + $root)
    if (Test-HasRemote) { & git remote -v } else { Write-Note 'No "origin" remote yet.' }
    Show-Board 22
    Write-Step 'Dirty files'
    $dirty = @(& git status --short)
    if ($dirty.Count -eq 0) { Write-Note 'clean' } else { $dirty | ForEach-Object { Write-Host $_ } }
    Show-Log 8
}