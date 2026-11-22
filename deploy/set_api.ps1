# Update the tunnel API url inside index.html and push.
# Usage: powershell -ExecutionPolicy Bypass -File deploy\set_api.ps1
#        powershell -ExecutionPolicy Bypass -File deploy\set_api.ps1 -Api https://xxx.trycloudflare.com
param([string]$Api)

if (-not $Api) {
    $log = "Y:\hks\.cache\tunnel.log"
    if (-not (Test-Path $log)) { Write-Host "no tunnel log found, pass -Api manually"; exit 1 }
    $m = Select-String -Path $log -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" -AllMatches | Select-Object -Last 1
    $Api = $m.Matches[-1].Value
}

Write-Host "API = $Api"
$probe = ""
try { $probe = (Invoke-WebRequest "$Api/health" -UseBasicParsing -TimeoutSec 10).Content } catch { }
if ($probe -match "skus") { Write-Host "health OK: $probe" } else { Write-Host "WARN: $Api/health did not answer as expected" }

$file = "Y:\hks\index.html"
$text = Get-Content $file -Raw
$new = [regex]::Replace($text, "https://[a-z0-9-]+\.trycloudflare\.com", $Api)
if ($new -eq $text) {
    Write-Host "index.html already points to this url, nothing to do"
    exit 0
}
Set-Content -Path $file -Value $new -Encoding utf8NoBOM

git -C Y:\hks add index.html
$msg = "[P2] home page api -> " + ($Api -replace "https://", "")
git -C Y:\hks -c user.name="P2" -c user.email="p2@hks.local" commit -q -m $msg
git -C Y:\hks push 2>&1 | Select-Object -Last 2 | Out-String | Write-Host
Write-Host "pushed; wait about 1 minute for Pages"
