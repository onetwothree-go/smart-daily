# smart-daily v2 每日自动日报入口（Windows 计划任务 SmartDaily-2200 调起）
# 设计口径（2026-11-20）：
#   - 跑的是 v2 CLI（第三周活跃、含日报美化格式的生成器），不碰已封版的 v1。
#   - 工作目录固定到本仓库 v2\，不依赖调用方 cwd，规避旧脚本 D:\pro\ 失效路径。
#   - v2 代码只读 os.environ、不自动加载 .env；用 uv 的 --env-file 把凭证注入新进程，
#     这是计划任务（无继承会话环境）能读到 GITHUB_TOKEN / FEISHU_APP_ID / FEISHU_APP_SECRET 的关键。
#   - REPORT_RECIPIENTS 显式置空：老师外部收件人路现码本就不触发，这里再做一次双保险。
#   - 无论 CLI 是否有 stdout，都追加一行运行摘要到日志（时间戳 + 退出码），
#     因为 dispatch 层零 print，Tee 遇到零输出不会建文件，无人值守时无据可查。
#   - SMART_DAILY_NO_NOTIFY=1 时为演练模式（加 --no-notify），只采集生成落库不推送；
#     计划任务正常运行不设此变量，仍真实推送。
# 无人值守前提：本机开机、未休眠（任务已设唤醒）、联网；不需要任何 AI 窗口常开。

Set-Location 'D:\projects\smart-daily\v2'

$uvPath = 'D:\tools\uv\uv.exe'
if (-not (Test-Path $uvPath)) {
    Write-Error "uv 不存在：$uvPath"
    exit 1
}

$day = Get-Date -Format 'yyyy-MM-dd'
$logDir = Join-Path (Get-Location) 'data\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir "daily-$day.log"

$env:REPORT_RECIPIENTS = ''

$cliArgs = @('run', '--env-file', '.env', 'python', '-m', 'smart_daily_v2.cli', '--day', $day)
$dryRun = $env:SMART_DAILY_NO_NOTIFY -eq '1'
if ($dryRun) { $cliArgs += '--no-notify' }

& $uvPath @cliArgs *>&1 | Tee-Object -FilePath $log
$rc = $LASTEXITCODE
$mode = if ($dryRun) { 'DRYRUN' } else { 'REAL' }
Add-Content -Path $log -Encoding UTF8 -Value ("[{0}] mode={1} exit_code={2}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $mode, $rc)
exit $rc
