# --- 答辩口径 · 22:00 本机自动日报（见答辩稿 2.6.2 / 链路①）---
# 由 Windows 计划任务 SmartDaily-2200 每日 22:00 调起，与任何 AI 窗口无关。
# 项目当前为 v1.1：自动定时属 N8 计划列兑现，非范围变更（proposal 变更记录补记 8）。
# 必须带 --env-file .env：裸 python -m 不读 .env，凭证为空会静默降级成空日报。
# *>&1 合并六条输出流，Tee-Object 写当天日志；exit $LASTEXITCODE 把 CLI 四码透传给计划任务。
# v1 已整体移入 v1/ 目录（2026-11-17 框架调整），本脚本随项目自包含于 v1/ 内运行。
# 根目录 scripts\run_daily.ps1 是转发脚本，Windows 计划任务 SmartDaily-2200 指向它，路径不变。
Set-Location 'D:\pro\smart-daily\v1'
$day = Get-Date -Format 'yyyy-MM-dd'
$logDir = Join-Path (Get-Location) 'data\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir "daily-$day.log"
& 'C:\Users\asus\.local\bin\uv.exe' run --env-file .env python -m smart_daily.cli --day $day *>&1 | Tee-Object -FilePath $log
exit $LASTEXITCODE
