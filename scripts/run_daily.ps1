# 转发脚本（2026-11-17 框架调整）：v1 项目已整体移入 v1\ 目录。
# Windows 计划任务 SmartDaily-2200 仍指向本文件，路径不变；实际逻辑在 v1\scripts\run_daily.ps1。
& 'D:\pro\smart-daily\v1\scripts\run_daily.ps1'
exit $LASTEXITCODE
