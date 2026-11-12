Set-Location 'D:\pro\smart-daily'
$day = Get-Date -Format 'yyyy-MM-dd'
$logDir = Join-Path (Get-Location) 'data\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir "daily-$day.log"
& 'C:\Users\asus\.local\bin\uv.exe' run --env-file .env python -m smart_daily.cli --day $day *>&1 | Tee-Object -FilePath $log
exit $LASTEXITCODE
