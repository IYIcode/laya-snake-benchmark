$s = Get-Counter '\GPU Engine(*engtypeCompute*)\Utilization Percentage' -ErrorAction SilentlyContinue
$top = $s.CounterSamples | Where-Object { $_.CookedValue -gt 0.2 } |
  ForEach-Object {
    $pid_ = ($_.InstanceName -split '_pid_')[1] -split '_luid_' | Select-Object -First 1
    [pscustomobject]@{ PID = [int]$pid_; Pct = [math]::Round($_.CookedValue, 2) }
  } | Group-Object PID | ForEach-Object {
    [pscustomobject]@{ PID = $_.Name; GPUPct = [math]::Round(($_.Group | Measure-Object Pct -Sum).Sum, 2) }
  } | Sort-Object GPUPct -Descending | Select-Object -First 8
foreach ($t in $top) {
  $name = (Get-Process -Id $t.PID -ErrorAction SilentlyContinue).ProcessName
  "{0,-8} {1,7}%  {2}" -f $t.PID, $t.GPUPct, $name
}
