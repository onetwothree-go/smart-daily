# 方赫 · 第 3 周 AI 使用日志签认清单

> 数据源：`docs/ai-usage-log.md` 第 3 周区段（2026-11-16 起）中方赫本人的待确认条目。
> 生成方式：脚本按标题与「人工核验方式」行摘录原文，未改日志正文。
> **签认（2026-11-23）**：本人 30 条「人工核验方式」经本人逐行核对属实，已签认（☑）。
> 本清单不代替正式日志 `docs/ai-usage-log.md`；正式日志中的对应条目状态由本人另行签认。
> 不含队友（于悦 / 赵蕊 / 杨佳莹）产出行——那些由各自本人确认，本人不代核。

| # | 日志行号 | 条目 | 人工核验方式（原文摘录） | 本人核对 |
|---|---|---|---|---|
| 1 | L323 | 补记（2026-11-17，方赫第 3 周 TK-V2-105 配置与凭证 | 人工核验方式：本人逐行 review config.py（frozen dataclass / load_config 可注入 env / require_credential 缺凭证抛 ValueError 且不发 HTTP），确认无硬编码凭证（G6 扫描 0 命中）、git diff -- v1/src v1/tests 为空（未碰 v1 代码）；红阶段真实失败输出已核对为… | ☑ 属实 |
| 2 | L331 | 补记（2026-11-17，方赫按 issue #14 修订接口契约 K2/K8/K5 | 人工核验方式：逐字对照审核记录 §四 K2/K8 与 §五 K5 的修订文本；改后 grep 复核 8 处关键词全部命中，且 K1/K3/K4/K6（于悦、杨佳莹负责）的既有改动痕迹保留、未覆盖；git diff --stat 仅 v2/specs/tasks.md 一个文件，未碰任何代码（v1/src v1/tests 为空）。 | ☑ 属实 |
| 3 | L339 | 补记（2026-11-17，方赫第 3 周 TK-V2-103 采集协议与异常契约 | 人工核验方式：本人逐行 review base.py，确认 ① WorkSource 为 @runtime_checkable Protocol 且 collect(*, since, until, author=None) keyword-only（对应 issue #14 K5，本人修订）、② AllSourcesUnavailableError(SourceUnavail… | ☑ 属实 |
| 4 | L354 | 补记（2026-11-18，方赫第 3 周 TK-V2-301 按成员分组 | 人工核验方式：本人逐行 review generator.py（dict 插入序保留成员首现顺序、组内按 occurred_at 倒序），确认与 v2/specs/tasks.md 中 301 的验收口径一致；git diff -- v1/src v1/tests 为空（未碰 v1 代码）。 | ☑ 属实 |
| 5 | L362 | 补记（2026-11-18，方赫第 3 周 TK-V2-302 单条渲染 | 人工核验方式：本人逐行 review format_item（东八区 %H:%M 换算、kind 中文标签映射、空 detail 省略  ——  段、纯函数无 IO），确认与 v2/specs/tasks.md 中 302 验收口径一致；git diff -- v1/src v1/tests 为空。 | ☑ 属实 |
| 6 | L370 | 补记（2026-11-18，方赫第 3 周 TK-V2-303 个人日报 | 人工核验方式：本人逐行 review build_personal_report（首行格式、条目行复用 format_item 且不重排、空列表 "今日无工作记录" 分支、纯函数无 IO），确认与 v2/specs/tasks.md 中 303 验收口径一致；git diff -- v1/src v1/tests 为空。 | ☑ 属实 |
| 7 | L378 | 补记（2026-11-18，方赫第 3 周 TK-V2-304 团队日报 | 人工核验方式：本人逐行 review build_team_report（统计头计数口径、成员按条数降序、条目行复用 format_item 与个人日报逐字一致、0 条成员与全组 0 条分支、纯函数无 IO），确认与 v2/specs/tasks.md 中 304 验收口径一致；git diff -- v1/src v1/tests 为空。 | ☑ 属实 |
| 8 | L386 | 补记（2026-11-18，方赫第 3 周 TK-V2-401 成员邮箱映射 | 人工核验方式：本人逐行 review members.py（env 注入、逗号/分号解析、缺配置返回空容器、两变量物理隔离），确认与 v2/specs/tasks.md 中 401 验收及 design 0.6 契约一致；G6 自查仓库内真实邮箱 0 处；git diff -- v1/src v1/tests 为空。 | ☑ 属实 |
| 9 | L418 | 补记（2026-11-18，方赫第 3 周 TK-V2-402 SMTP 邮件通道 | 人工核验方式：本人逐行 review email.py（缺凭证 ValueError、use_ssl 取自 SMTP_SSL、send 异常捕获返回 False 不抛、无重试循环、monkeypatch smtplib.SMTP 打桩绝不真发邮件），确认与 v2/specs/tasks.md 中 402 验收及 design R5/N8 契约一致；G6 自查仓库内真实邮箱 0 … | ☑ 属实 |
| 10 | L426 | 补记（2026-11-18，方赫第 3 周 TK-V2-403 群通道与签名 | 人工核验方式：本人逐行 review webhook.py（gen_sign 与飞书官方算法/v1 参考实现一致、import hmac as _h 满足验收①全仓 1 行命中、关键词闸门先于 httpx.post、secret 非空才签名、异常捕获返回 False 不重试），确认与 v2/specs/tasks.md 中 403 验收及 design 3.3/ADR-104 … | ☑ 属实 |
| 11 | L434 | 补记（2026-11-18，方赫第 3 周 TK-V2-404 分发规则与送达判定 | 人工核验方式：本人逐行 review dispatch.py（dispatch 函数体内不读环境变量、team_recipients 纯参数注入；个人/群/外部三路独立 try、异常记 False 不漏回执；all_delivered 仅用 all()、全文无 any()、空 expected 返 False、缺失 scope 判 False；未配外部收件人不产生 team:r… | ☑ 属实 |
| 12 | L442 | 补记（2026-11-19，方赫第 3 周 TK-V2-601 无凭证可复现夹具 | 人工核验方式：本人逐行 review mock.py（纯函数无 IO、不读环境变量、不发请求；_FIXTURE_ROWS 与 golden JSON 逐条对账一致——本地 Python 实跑比对 record_id/member/kind/title/detail/occurred_at 全等；MockSource 实现 WorkSource 协议、collect 时间窗含端点… | ☑ 属实 |
| 13 | L464 | 补记（2026-11-19，方赫第 3 周 TK-V2-605 送达判定用例 C7/R3 | 人工核验方式：本人逐行 review delivery_harness（三通道 _send_personal/_send_team_group/_send_team_external 全部 monkeypatch 打桩绝不真发；异常注入经 BaseException 抛出覆盖用例 7；with_external=False 触发 U6 退回 5 条路径；fixture 函数体惰… | ☑ 属实 |
| 14 | L472 | 补记（2026-11-19，方赫第 3 周 code-review 意见回应与互评记录 | （原文无独立核验行，见该段） | ☑ 属实 |
| 15 | L481 | 补记（2026-11-19，方赫第 3 周 TK-V2-604 格式一致性与计数用例 | 人工核验方式：本人逐行 review format_harness（惰性导入、纯本地构造无 IO、empty_members 补空组）与测试用例（C1 计数 5 条 1:1 零手工、Counter 逐字比对、三源 3 条独立不去重不合并、个人=团队逐字一致、inspect.getsource 断言 format_item 单一来源、20 条不截断、0 条成员仍列出、record… | ☑ 属实 |
| 16 | L512 | 补记（2026-11-19，方赫第 3 周 TK-V2-104 异常驱动降级链 | 人工核验方式：本人本地逐项复核——git status 仅 2 项新增（fallback.py / test_fallback.py）；git diff 既有正式模块 / conftest.py / v1/ / v2/specs/tasks.md / v2/README.md 全为空；docstring 含「待确认」「停止点」「降级原因」三词；except AllSources… | ☑ 属实 |
| 17 | L533 | 补记（2026-11-19，方赫第 3 周 TK-V2-201 GitHub 提交采集 | 人工核验方式：本人本地逐项复核——git status 仅 2 项新增（github.py / test_source_github.py）、HEAD = origin/dev = 6ac60fd、已跟踪文件 0 改动；测试文件仍 251 行 / 10 用例与红阶段一致、断言未改弱（含「仓库为空」「token」「401」「sha==main」「from smart_daily … | ☑ 属实 |
| 18 | L545 | 补记（2026-11-19，方赫第 3 周 TK-V2-202 飞书任务采集 | 人工核验方式：本人本地逐项复核——git status 仅 2 项新增（feishu_tasks.py / test_source_feishu_tasks.py）、HEAD = origin/dev = fdb8d21、0/0 无撞车、已跟踪文件 0 改动；测试文件仍 367 行 / 10 用例与红阶段一致、断言未改弱（含 record_id==task_id 逐条相等、lo… | ☑ 属实 |
| 19 | L557 | 补记（2026-11-20，方赫第 3 周 TK-V2-203 飞书群消息采集·单群限定 | 人工核验方式：本人（经 WorkBuddy）只读复核——git status 仅 2 项新增（feishu_chat.py / test_source_feishu_chat.py）、HEAD = origin/dev = 9b5109b、0/0 无撞车、已跟踪文件 0 改动；测试文件 312 行 / 10 用例与红阶段一致、断言未改弱（单群过滤只返回目标群且排除 p2p、正文… | ☑ 属实 |
| 20 | L582 | 补记（2026-11-20，方赫第 3 周 TK-V2-501 主编排流程 | 人工核验方式：本人（经 WorkBuddy）只读复核——git status 仅 2 项新增（orchestrator.py / test_orchestrator.py）、fetch 发现队友 c6970ac（于悦 703 周五维护记录，碰了本日志但未碰红绿记录），先 git rebase origin/dev 快进到 c6970ac（0/0、501 两未跟踪文件保留、零冲突… | ☑ 属实 |
| 21 | L594 | 补记（2026-11-20，方赫第 3 周 TK-V2-502 SQLite 幂等落库 | 人工核验方式：本人（经 WorkBuddy）只读复核——git status 仅 2 项新增（storage.py / test_storage.py）、HEAD = origin/dev = 057de19、0/0 无撞车、已跟踪文件 0 改动；测试文件 236 行 / 10 用例与红阶段一致、修正后用例清单逐一核对、0 skip/xfail、assert 27 处、确认未放… | ☑ 属实 |
| 22 | L605 | 补记（2026-11-20，方赫第 3 周 TK-V2-503 历史查询 list_report | 人工核验方式：本人（经 WorkBuddy）只读复核——git status 仅 2 项修改（storage.py / test_storage.py，非新增）、git diff --stat 257 insertions / 0 deletions（502 原 10 用例与 _create_schema/save_report 逐字未改，新增只在文件末尾）、HEAD = or… | ☑ 属实 |
| 23 | L616 | 补记（2026-11-20，方赫第 3 周 TK-V2-504 CLI 与退出码 | 收尾自查（如实，由 Claude Code 在 /task504c 会话内完成）：ruff check . → All checks passed、ruff format --check . → 68 files already formatted、全量 196 passed；四验收 + 五不变量（v1 design L415-419）逐条对上；P6/零复制扫描（锚定 ^fro… | ☑ 属实 |
| 24 | L685 | 2026-11-20（续）成员账号名→中文显示名映射（范围外新增，状态 ☐ 待确认 | （原文无独立核验行，见该段） | ☑ 属实 |
| 25 | L701 | 2026-11-20（续 2）团队日报格式美化（范围外新增，状态 ☐ 待确认 | （原文无独立核验行，见该段） | ☑ 属实 |
| 26 | L709 | 2026-11-20（续 3）每日 22:00 自动日报定时（范围外运维自动化，状态 ☐ 待确认 | 验证：fetch 0/0 无撞车；注册计划任务 NextRun=11-20 22:00、已设唤醒；改 branch 后真推退出码 0（4 成员+飞书群全送达）；最终脚本 dry-run 退出码 0、日志落文件干净。 | ☑ 属实 |
| 27 | L725 | 2026-11-20（续 4）GitHub 采集器 main+dev 双分支并采与 SHA 去重 | （原文无独立核验行，见该段） | ☑ 属实 |
| 28 | L734 | 2026-11-20（续 5）团队日报 / 个人日报二次美化（范围外展示层微调，状态 ☐ 待确认 | 验证：全量 249 passed（246 基线 + 3 新增）、ruff check All checks passed、ruff format --check 78 files already formatted；改动仅 1 源 + 4 测试 + 本记录；保护文件 diff 全空、无真实凭证、未真推送。 | ☑ 属实 |
| 29 | L744 | 2026-11-20（续 6）V1 入口 / U2 实时提醒口径核验（只读，状态 ☐ 待确认 | 只读核验：v2 下 *.py 的 import smart_daily 0 命中、v2/src 无 subprocess / Popen / os.system / notify_push 调用；本机 SmartDaily-2200 唯一 Action 指向 v2/scripts/run_daily.ps1（22:00 Result=0、NextRun 11-21 22:00）… | ☑ 属实 |
| 30 | L776 | 2026-11-22（补记）TK-V2-803 根 notify.yml 切换到 v2 实时提醒 | 核验与提交（WorkBuddy，只读 + 提交）：本地独立复跑 uv run pytest tests/ -q → 265 passed in 2.70s、ruff check . All checks passed、ruff format --check . 83 files already formatted，与截图一致；git fetch origin dev 0/0 无… | ☑ 属实 |
