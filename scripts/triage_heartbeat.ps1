<#
.SYNOPSIS
    Kirov Dynamics — CI Heartbeat Triage (PowerShell)
.DESCRIPTION
    Scans all Raphasha27 repositories for failing CI runs, open Dependabot PRs,
    and repos with no CI configured. Outputs a colour-coded report to the console
    and saves a log file. Sends a Windows toast notification if failures are found.
.NOTES
    Schedule with Task Scheduler:
      - Program:   powershell.exe
      - Arguments: -ExecutionPolicy Bypass -File "C:\...\triage_heartbeat.ps1"
      - Trigger:   Daily at 08:00
    Requires GITHUB_TOKEN as a system environment variable or in the script below.
#>

#region ── Config ─────────────────────────────────────────────────────────────
$USERNAME   = "Raphasha27"
$API        = "https://api.github.com"
$TOKEN      = $env:GITHUB_TOKEN     # Set via: $env:GITHUB_TOKEN = "ghp_xxx"
$SKIP_REPOS = @("mochi-motion","Fire4s-End-End-AI-Solutions")
$LOG_DIR    = "$PSScriptRoot\..\logs"
$TIMESTAMP  = (Get-Date -Format "yyyy-MM-dd_HH-mm")
$LOG_FILE   = "$LOG_DIR\heartbeat_$TIMESTAMP.log"
#endregion

#region ── Helpers ─────────────────────────────────────────────────────────────
function Get-GH {
    param([string]$Path, [hashtable]$Query = @{})
    $headers = @{
        Authorization       = "Bearer $TOKEN"
        Accept              = "application/vnd.github+json"
        "X-GitHub-Api-Version" = "2022-11-28"
    }
    $results = [System.Collections.Generic.List[object]]::new()
    $url = "$API$Path"
    if ($Query.Count) {
        $qs = ($Query.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join "&"
        $url = "$url`?$qs"
    }
    do {
        try {
            $resp = Invoke-WebRequest -Uri $url -Headers $headers -UseBasicParsing -EA Stop
        } catch {
            if ($_.Exception.Response.StatusCode -in 403,404) { return $null }
            throw
        }
        $data = $resp.Content | ConvertFrom-Json
        # PS5: ConvertFrom-Json returns PSCustomObject even for arrays; check for array wrapper
        if ($data -is [System.Array]) {
            $results.AddRange([object[]]$data)
        } elseif ($data.PSObject.Properties.Name -contains 'workflow_runs' -or
                  $data.PSObject.Properties.Name -contains 'total_count') {
            # It's a wrapped object, return as-is
            return $data
        } elseif ($null -ne $data -and $data -isnot [string]) {
            # Could be a single object or array — try treating as array
            try { $results.AddRange([object[]]$data) } catch { return $data }
        } else {
            return $data
        }
        # Follow Link header for pagination
        $link = $resp.Headers["Link"]
        $url  = if ($link -match '<([^>]+)>;\s*rel="next"') { $Matches[1] } else { $null }
    } while ($url)
    return $results.ToArray()
}

function Write-Log {
    param([string]$Msg, [string]$Color = "White")
    Write-Host $Msg -ForegroundColor $Color
    Add-Content -Path $LOG_FILE -Value $Msg -Encoding UTF8
}

function Show-Toast {
    param([string]$Title, [string]$Body)
    try {
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(
            [Windows.UI.Notifications.ToastTemplateType]::ToastText02)
        $template.GetElementsByTagName("text")[0].AppendChild(
            $template.CreateTextNode($Title)) | Out-Null
        $template.GetElementsByTagName("text")[1].AppendChild(
            $template.CreateTextNode($Body)) | Out-Null
        $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier(
            "Kirov Heartbeat").Show($toast)
    } catch { <# silently ignore if toast not supported #> }
}

function Get-StatusIcon {
    param([string]$Conclusion, [string]$Status)
    if ($Status -in "in_progress","queued","waiting") { return "[RUN]" }
    switch ($Conclusion) {
        "success"   { return "[ OK]" }
        "neutral"   { return "[ OK]" }
        "skipped"   { return "[SKP]" }
        "failure"   { return "[ERR]" }
        "timed_out" { return "[ERR]" }
        "cancelled" { return "[WRN]" }
        default     { return "[???]" }
    }
}
#endregion

#region ── Main ───────────────────────────────────────────────────────────────
# Ensure log directory exists
New-Item -ItemType Directory -Force -Path $LOG_DIR | Out-Null

$divider = "=" * 60

Write-Log ""
Write-Log $divider Cyan
Write-Log "  KIROV DYNAMICS -- CI HEARTBEAT TRIAGE" Cyan
Write-Log "  $(Get-Date -Format 'yyyy-MM-dd HH:mm') SAST" Cyan
Write-Log $divider Cyan

if (-not $TOKEN) {
    Write-Log ""
    Write-Log "  [!] GITHUB_TOKEN is not set." Red
    Write-Log "  Set it with:  `$env:GITHUB_TOKEN = 'ghp_xxx'" Yellow
    Write-Log ""
    exit 1
}

Write-Log ""
Write-Log "  Fetching repositories..." DarkGray

$allRepos = Get-GH "/users/$USERNAME/repos" @{type="owner";per_page=100}
if (-not $allRepos) {
    Write-Log "  [!] Could not fetch repos. Check token." Red
    exit 1
}

$repos = $allRepos | Where-Object { -not $_.archived -and $_.name -notin $SKIP_REPOS }
Write-Log "  Scanning $($repos.Count) repositories..." DarkGray
Write-Log ""

$failingCI  = [System.Collections.Generic.List[hashtable]]::new()
$pendingCI  = [System.Collections.Generic.List[hashtable]]::new()
$noCi       = [System.Collections.Generic.List[string]]::new()
$allGreen   = [System.Collections.Generic.List[string]]::new()
$depPRs     = [System.Collections.Generic.List[hashtable]]::new()

foreach ($repo in $repos) {
    $name = $repo.name
    Write-Host "  Checking $name..." -ForegroundColor DarkGray -NoNewline
    Write-Host "`r" -NoNewline

    # Latest CI run
    $runData = Get-GH "/repos/$USERNAME/$name/actions/runs" @{per_page=1}
    $run     = if ($runData -and $runData.workflow_runs) { $runData.workflow_runs[0] } else { $null }

    # Dependabot PRs
    $prs = Get-GH "/repos/$USERNAME/$name/pulls" @{state="open";per_page=100}
    if ($prs) {
        $botPRs = $prs | Where-Object { $_.user.login -eq "dependabot[bot]" }
        foreach ($pr in $botPRs) {
            $depPRs.Add(@{Repo=$name; Number=$pr.number; Title=$pr.title; Url=$pr.html_url})
        }
    }

    if (-not $run) {
        # Check if workflow files exist
        $wf = Get-GH "/repos/$USERNAME/$name/actions/workflows"
        if (-not $wf -or $wf.total_count -eq 0) {
            $noCi.Add($name)
        } else {
            $noCi.Add("$name  (no runs yet)")
        }
        continue
    }

    $conclusion = if ($run.conclusion) { $run.conclusion } else { "" }
    $status     = if ($run.status)     { $run.status     } else { "" }
    $icon       = Get-StatusIcon $conclusion $status
    $branch     = if ($run.head_branch) { $run.head_branch } else { "?" }
    $url        = if ($run.html_url)    { $run.html_url    } else { "" }

    if ($status -in "in_progress","queued","waiting") {
        $pendingCI.Add(@{Name=$name; Icon=$icon; State=$status; Branch=$branch; Url=$url})
    } elseif ($conclusion -in "failure","timed_out","action_required") {
        $failingCI.Add(@{Name=$name; Icon=$icon; State=$conclusion; Branch=$branch; Url=$url})
    } elseif ($conclusion -in "success","neutral","skipped") {
        $allGreen.Add($name)
    } else {
        $failingCI.Add(@{Name=$name; Icon=$icon; State="$conclusion/$status"; Branch=$branch; Url=$url})
    }
}

# Clear spinner
Write-Host (" " * 50) + "`r" -NoNewline

#region ── Print sections ────────────────────────────────────────────────────
Write-Log "  [OK] GREEN ($($allGreen.Count)):" Green
if ($allGreen.Count) {
    foreach ($n in $allGreen) { Write-Log "       * $n" Green }
} else {
    Write-Log "       (none)" DarkGray
}

if ($pendingCI.Count) {
    Write-Log ""
    Write-Log "  [RUN] IN PROGRESS ($($pendingCI.Count)):" Yellow
    foreach ($r in $pendingCI) {
        Write-Log ("       $($r.Icon)  {0,-40}  [{1}]" -f $r.Name, $r.Branch) Yellow
        Write-Log "            $($r.Url)" DarkGray
    }
}

if ($failingCI.Count) {
    Write-Log ""
    Write-Log "  [ERR] FAILING ($($failingCI.Count)):" Red
    foreach ($r in $failingCI) {
        Write-Log ("       $($r.Icon)  {0,-40}  [{1}] -> {2}" -f $r.Name, $r.Branch, $r.State) Red
        Write-Log "            $($r.Url)" DarkGray
    }
}

if ($noCi.Count) {
    Write-Log ""
    Write-Log "  [???] NO CI CONFIGURED ($($noCi.Count)):" DarkYellow
    foreach ($n in $noCi) { Write-Log "       * $n" DarkYellow }
}

if ($depPRs.Count) {
    Write-Log ""
    Write-Log "  [KEY] OPEN DEPENDABOT PRs ($($depPRs.Count)):" Magenta
    foreach ($pr in $depPRs) {
        Write-Log ("       * [{0}] PR #{1} -- {2}" -f $pr.Repo, $pr.Number, $pr.Title.Substring(0,[Math]::Min(60,$pr.Title.Length))) Magenta
        Write-Log "            $($pr.Url)" DarkGray
    }
}
#endregion

#region ── Summary ───────────────────────────────────────────────────────────
$total     = $repos.Count
$pctGreen  = if ($total -gt 0) { [Math]::Round($allGreen.Count / $total * 100) } else { 0 }
$health    = if ($pctGreen -ge 90) { "HEALTHY" } elseif ($pctGreen -ge 70) { "DEGRADED" } else { "CRITICAL" }
$hColor    = if ($pctGreen -ge 90) { "Green"  } elseif ($pctGreen -ge 70) { "Yellow"  } else { "Red"     }

Write-Log ""
Write-Log $divider Cyan
Write-Log ("  {0} {1}%  |  {2} OK  {3} FAIL  {4} RUNNING  {5} NO-CI" -f `
    $health, $pctGreen, $allGreen.Count, $failingCI.Count, $pendingCI.Count, $noCi.Count) $hColor
Write-Log "  Dependabot PRs pending: $($depPRs.Count)" Cyan
Write-Log "  Log saved: $LOG_FILE" DarkGray
Write-Log $divider Cyan
Write-Log ""
#endregion

# ── Toast notification on failure ─────────────────────────────────────────────
if ($failingCI.Count -gt 0) {
    $failNames = ($failingCI | Select-Object -First 3 | ForEach-Object { $_.Name }) -join ", "
    Show-Toast "Kirov Heartbeat — $($failingCI.Count) Failure(s)" "Failing: $failNames"
    exit 1
} elseif ($pctGreen -lt 70) {
    Show-Toast "Kirov Heartbeat — Health $pctGreen%" "$($allGreen.Count)/$total repos green"
}

exit 0
#endregion
