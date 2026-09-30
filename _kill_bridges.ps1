# utf-8-sig
$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'laya_bridge\.py --port 889[01]' }
if (-not $procs) { Write-Output 'no bridge processes found'; exit 0 }
foreach ($p in $procs) {
  Write-Output ('killing {0} :: {1}' -f $p.ProcessId, $p.CommandLine.Substring(0, [Math]::Min(90, $p.CommandLine.Length)))
  Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep 2
$left = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'laya_bridge\.py' }
Write-Output ('remaining bridges: ' + ($left | Measure-Object).Count)
