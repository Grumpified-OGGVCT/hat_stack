<#
.SYNOPSIS
    Install or manage the Gremlin Overnight Daemon as a Windows Scheduled Task.

.DESCRIPTION
    Registers a Windows Scheduled Task named "GremlinOvernightDaemon" that starts
    at user logon and runs the gremlin_daemon.py in --daemon mode.

    The daemon self-schedules based on the cron expressions in hat_configs.yml,
    so the Windows task just needs to start it at logon.

.PARAMETER Uninstall
    Remove the scheduled task.

.PARAMETER Status
    Show current task status.

.PARAMETER ConfigPath
    Path to hat_configs.yml (default: scripts/hat_configs.yml relative to this script)

.PARAMETER PythonPath
    Path to python executable (default: auto-detect pythonw.exe then python.exe)

.EXAMPLE
    .\install-gremlin-daemon.ps1
    Install the daemon task.

.EXAMPLE
    .\install-gremlin-daemon.ps1 -Uninstall
    Remove the daemon task.

.EXAMPLE
    .\install-gremlin-daemon.ps1 -Status
    Show task status.
#>

param(
    [switch]$Uninstall,
    [switch]$Status,
    [string]$ConfigPath = "",
    [string]$PythonPath = ""
)

$TaskName = "GremlinOvernightDaemon"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Resolve config path
if (-not $ConfigPath) {
    $ConfigPath = Join-Path $ScriptDir "hat_configs.yml"
}

# Resolve Python path
if (-not $PythonPath) {
    $pythonw = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($pythonw) {
        $PythonPath = $pythonw.Source
    } elseif ($python) {
        $PythonPath = $python.Source
    } else {
        Write-Error "Python not found. Install Python or specify -PythonPath."
        exit 1
    }
}

$DaemonScript = Join-Path $ScriptDir "gremlin_daemon.py"

if ($Status) {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $task) {
        Write-Host "Task '$TaskName' is NOT installed."
        exit 0
    }
    $info = $task | Get-ScheduledTaskInfo
    Write-Host "Task: $TaskName"
    Write-Host "State: $($task.State)"
    Write-Host "Last run: $($info.LastRunTime)"
    Write-Host "Next run: $($info.NextRunTime)"
    Write-Host "Actions:"
    foreach ($action in $task.Actions) {
        Write-Host "  $($action.Execute) $($action.Arguments)"
    }
    exit 0
}

if ($Uninstall) {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Task '$TaskName' uninstalled."
    } else {
        Write-Host "Task '$TaskName' was not installed."
    }
    exit 0
}

# Install
$arguments = "`"$DaemonScript`" --daemon --config `"$ConfigPath`""

$action = New-ScheduledTaskAction -Execute $PythonPath -Argument $arguments
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 8)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Gremlin Overnight Daemon - multi-repo autonomous code review scanner" `
    -Force

Write-Host "Task '$TaskName' installed."
Write-Host "  Python:  $PythonPath"
Write-Host "  Script:  $DaemonScript"
Write-Host "  Config:  $ConfigPath"
Write-Host "  Trigger: At logon"
Write-Host ""
Write-Host "The daemon reads its cron schedule from hat_configs.yml and runs phases"
Write-Host "automatically at the configured times (default: 2-5 AM)."
Write-Host ""
Write-Host "Test with: python `"$DaemonScript`" --dry-run --config `"$ConfigPath`""