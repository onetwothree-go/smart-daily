# C1–C10 逐条核对表

**编制人**：赵蕊（测试工程师 / 配置管理员）
**对应任务**：TK-V2-607 · C1–C10 逐条核对表与覆盖率 / 扫描归档
**编制日期**：2026-11-19
**版本**：v2.2（2026-11-23 C1/C2/C5/C8/C10 判定按实测回写；v2.1 = 同日 C10 回写，v2.0 = 2026-11-19 21:52 修订，历次修订内容见 §0）

**成功标准来源**：`v1/specs/proposal.md` 第 115–124 行（C1–C10 定义原文）。
本表仅引用标准**文本**，**不引用 v1 的实测证据**——v2 为独立重写，v1 的 ✅ 不能移花接木当作 v2 结论（零复制红线）。

## 0. 修订说明（v1.0 → v2.0，如实留痕）

| 项 | v1.0（本日 21:20 版） | v2.0（本版） | 修订原因 |
| --- | --- | --- | --- |
| 通过数 | 表内 10 行「实际输出」全写 `116 passed`，同文件摘要写 `126 passed` | 统一为**分组实测值**（见 §2） | 两处不一致，按组内「两处不一致即缺陷」判定为缺陷；116 是 `6081e82` 提覆盖率之前的旧数 |
| 判定分布 | ✅4 / ⚠️2 / ❌2 / ⏭1，标注「总计 9 条」 | ✅4 / ⚠️3 / ❌2 / ⏭1，**总计 10 条** | v1.0 漏算 C7，且 4+2+2+1=9 与 C1–C10 的 10 条自相矛盾 |
| 证据命令 | `pytest -k "C1 or C2 or C3 or C4 or C7 or C8 or C9"` → `1 passed, 115 deselected` | 按 C 分组逐条指定 nodeid（§4） | v2 用例名中不含 `C1` 字样，`-k` 只能偶然匹配到 1 条，**该命令证明力为零**，已删除 |
| C2 判定 | ✅ 通过 | ⚠️ 部分覆盖 | 降级机制与原因留痕有断言，但 v2 无 GitHub 源，「假 token 注入」场景无对应实现 |
| C4 用例 | 1 条 | 3 条 | 补 `test_team_report_entry_lines_match_personal`（逐字一致）、`test_both_reports_share_single_format_item_source`（格式同源） |

### v2.0 → v2.1（2026-11-23，C10 判定回写）

| 项 | v2.0（2026-11-19） | v2.1（本版） | 回写原因与证据 |
| --- | --- | --- | --- |
| C10 判定 | ❌ 未覆盖（v2 无 `notify.yml`、无被测对象） | ✅ 通过 | `TK-V2-803/804` 已落地：根 `notify.yml` 切 v2 单通道、v1 脚本停用，新增 `notify_push.py` 与两组用例；2026-11-23 本地实测 `test_notify_push.py` 9 passed、`test_notify_workflow.py` 7 passed、全量 265 passed；CI 4 run 全 success（`45033546323` 等）。任务编号与归属见 `v2/specs/tasks.md` §8.2 U2 闭环 |
| 判定分布 | ✅4 / ⚠️3 / ❌2 / ⏭1 | ✅5 / ⚠️3 / ❌1 / ⏭1 | 仅 C10 由 ❌ 转 ✅，其余 9 条判定未动（C5 仍 ❌，本版不处理） |

**回写口径**：① 原 C10 行（11-19 判定）保留在 §2 下方作历史留痕，本版新增 v2.1 行覆盖其结论，不倒填、不改写历史证据；② §3 的 `126 passed / 97%` 是 11-19 同批次实测，按 G5「不跨时点拼数据」原样保留，不混入 11-23 的 265 passed；③ **飞书群真实消息正文待本人目视确认**，本次仅按用例与 CI 结果回写判定，未代确认、未主动触发 push。

### v2.1 → v2.2（2026-11-23，C1/C2/C5/C8 缺口补齐回写，经本人确认）

| 项 | v2.1（11-19 原判） | v2.2（本版） | 回写原因与证据（2026-11-23 实测） |
| --- | --- | --- | --- |
| C1 | ⚠️ 部分覆盖（缺飞书群消息第三源，仅两源） | ✅ 通过 | `test_group_by_member_splits_and_sorts` 构造 github/feishu_task/feishu_chat 三源同报；实测三源逐条 1:1 呈现（3 条原文各占一行） |
| C2 | ⚠️ 部分覆盖（v2 无 GitHub 源，假 token 场景无实现） | ✅ 通过 | `sources/github.py` 已实现；`test_source_github.py::test_invalid_token_401_raises_source_unavailable`（20 passed）覆盖假 token 抛 `SourceUnavailableError` 交降级链 |
| C5 | ❌ 未覆盖（无 storage.py） | ✅ 通过 | `test_storage.py`（20 passed），`test_upsert_same_day_member_keeps_one_row` 覆盖 UNIQUE(日期,成员) + 覆盖更新 |
| C8 | ⚠️ 部分覆盖（CLI 返回码 1 无被测对象） | ✅ 通过 | `test_cli.py`（10 passed），`test_collect_failure_returns_one_and_argparse_error_returns_two` 覆盖返回码 1/2 |
| 判定分布 | ✅5 / ⚠️3 / ❌1 / ⏭1 | ✅9 / ⚠️0 / ❌0 / ⏭1 | 四条缺口均经实测补证，其余 6 条判定未动 |

**确认与边界**：本版缺口回写经杨佳莹本人确认后执行（见 `docs/ai-usage-log.md` 11-23 对应条目）；四条原判定（11-19 时点）为当时事实，按"不倒填、不改写历史"原则保留在 §2 的旧值说明与本节表格中，仅以新行/新判定覆盖结论；§3 的 `126 passed / 97%` 仍为 11-19 同批次原始输出，不混入 11-23 数据。

## 1. 判定口径

| 标记 | 含义 |
| --- | --- |
| ✅ 通过 | 该 C 的**全部核心断言**在 v2 有直接用例，且本次实测通过 |
| ⚠️ 部分覆盖 | 核心断言中**有子句未覆盖**，缺口在「覆盖说明」列逐条写明，不代之以"基本通过" |
| ❌ 未覆盖 | v2 无对应实现（非"没写用例"，而是**被测对象不存在**） |
| ⏭ 观察项 | 按 TK-V2-607 验收③，性能项不进硬验收，不建计时用例 |

**其它口径**：
① 判定基于 2026-11-19 本机实跑，Python **3.14.2**（`.venv`），CI 为 **3.13**，版本差异可能造成个别分支覆盖不同，判定以同批次输出为准，不跨版本拼数据；
② 覆盖率为 TOTAL **97%**（Stmts 287 / Miss 9），未达任何教师阈值时如实标注，不四舍五入抬高（G5 不补造）；
③ C6 为观察项，**不计入** C1–C10 的可测判定范围。

## 2. C1–C10 验收矩阵

| C | 成功标准（原文摘要） | 承接任务 | 用例 ID（pytest nodeid） | 实际输出 | 判定 | 覆盖说明 / 缺口 | 执行人 | 日期 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | 当日 3 次提交 + 2 个任务 → 个人日报条目数 = 5、手工 0；条目与原始记录 1:1，同一动作跨三源按 3 条独立条目呈现 | TK-V2-604 | `test_generator.py::test_personal_report_counts_all_items`<br>`::test_group_by_member_splits_and_sorts` | `1 passed in 0.10s`；三源同报实测 3 条 1:1 | ✅ 通过 | 3 提交（github）+ 2 任务（feishu_task）共 5 条、条目数 = 5、逐条 1:1、手工 0 ✅；**第三源缺口已补**：`test_group_by_member_splits_and_sorts` 构造 github/feishu_task/feishu_chat 三源同报，2026-11-23 实测三源逐条呈现（条目原文全在、各占一行）✅。原 11-19 判定「⚠️ 仅两源」为当时事实，按 §0 v2.2 回写，不倒填 | 杨佳莹（表维护人回写） | 2026-11-23 |
| C2 | 假 `GITHUB_TOKEN` 注入 → 降级到 local-git、主流程不中断、日志记录降级原因 | TK-V2-602 / 201 | `test_fallback.py::test_exception_source_falls_back_to_next`<br>`::test_multiple_fallbacks_accumulate_reasons_in_order`<br>`::test_all_sources_error_not_swallowed_as_single_failure`<br>`test_source_github.py::test_invalid_token_401_raises_source_unavailable` | `3 passed in 0.14s`；github 源 20 passed | ✅ 通过 | 源抛 `SourceUnavailableError` → 切下一源、主流程不中断 ✅；降级原因进 `reasons[]` 按序累积 ✅；**GitHub 源缺口已补**：`sources/github.py` 已实现，`test_invalid_token_401_raises_source_unavailable` 覆盖假 token 注入后抛 `SourceUnavailableError`（供降级链接管）✅。原 11-19 判定「⚠️ 仅 mock」为当时事实，按 §0 v2.2 回写 | 杨佳莹（表维护人回写） | 2026-11-23 |
| C3 | 同一成员多个 GitHub 登录名归并为一份日报、不串人 | TK-V2-606 / 101 | `test_integration_identity.py::test_case_whitespace_variants_merge_to_one_group`<br>`::test_different_people_not_merged`<br>`test_generator.py::test_same_member_from_multiple_accounts_merges` | `3 passed in 0.10s` | ✅ 通过 | 大小写 / 首尾空格变体归一组 ✅；不同人**不**合并 ✅；`record_id` 互不相交、无归并丢失 ✅；未映射身份告警且不丢（`test_unmapped_identity_warns_and_not_dropped`）✅ | 赵蕊 | 2026-11-19 |
| C4 | 团队日报含全部 4 位成员条目，与个人日报**条目行格式逐字一致**；20 条与 0 条成员均全量列出 | TK-V2-604 | `test_generator.py::test_team_report_lists_all_members_without_truncation`<br>`::test_team_report_entry_lines_match_personal`<br>`test_integration_format.py::test_both_reports_share_single_format_item_source` | `3 passed in 0.16s` | ✅ 通过 | 20 / 2 / 1 / 0 条四成员全列、统计头「成员 4 人 · 条目 23 条」✅；条目行与个人日报逐字比对 ✅；两报表经 `inspect.getsource` 证实共用同一 `format_item()` ✅ | 赵蕊 | 2026-11-19 |
| C5 | 同日重跑两次，SQLite 中 (日期,成员) 记录数不变、内容覆盖更新 | TK-V2-502/503 | `test_storage.py::test_upsert_same_day_member_keeps_one_row`<br>`::test_schema_has_unique_and_work_items_reserved` | `20 passed in 1.48s` | ✅ 通过 | **storage.py 缺口已补**：UNIQUE(日期,成员) 约束 + `ON CONFLICT DO UPDATE`，同日同成员重跑仅保留一行、内容覆盖更新（`test_upsert_same_day_member_keeps_one_row`）✅；`list_reports` 按日倒序、参数化查询、只读 ✅。原 11-19 判定「❌ 无 SQLite 落盘」为当时事实，按 §0 v2.2 回写，不倒填 | 杨佳莹（表维护人回写） | 2026-11-23 |
| C6 | 单成员 100 条提交采集耗时 < 30s（观察项） | —（原 TK-V2-607） | 不建计时用例 | 未执行 | ⏭ 观察项 | 按 607 验收③：性能为观察项、不进硬验收、不建计时用例。恢复为验收项的前置条件：fixture 注入 100 条 + 剥离真实网络 + 固定计时起止口径 + 组内评审 | 赵蕊 | 2026-11-19 |
| C7 | 4 封个人邮件 + 1 条飞书群 + 1 封团队外部邮件**全部 ok** 才算送达；一成一败不算送达 | TK-V2-404/605/601 | `test_integration_delivery.py::test_six_channels_all_true_is_delivered`<br>`::test_three_of_six_true_is_not_delivered` | `2 passed in 0.33s` | ✅ 通过 | 6 通道全 true → `pushed=True`，调用次数 4 personal / 1 team / 1 external ✅；3/6 true → **不判送达** ✅ | 赵蕊 | 2026-11-19 |
| C8 | 区分两种空：① 当天无数据 → 显式「今日无工作记录」、全组零记录时团队日照发；② 三源全不可用 → 必须抛明确异常，禁止静默返回空日报 | TK-V2-603/504 | `test_fallback.py::test_all_sources_fail_raises`<br>`test_generator.py::test_personal_report_empty_day`<br>`::test_team_report_all_empty_day`<br>`test_cli.py::test_collect_failure_returns_one_and_argparse_error_returns_two` | `3 passed in 0.13s`；cli 10 passed | ✅ 通过 | 全失效抛 `AllSourcesUnavailableError`、errors 聚合完整 ✅；合法空产出「今日无工作记录」、团队日照发 ✅；**CLI 缺口已补**：`cli.py` 已实现，`test_collect_failure_returns_one_and_argparse_error_returns_two` 覆盖采集失败返回码 1、参数错误返回码 2 ✅。原 11-19 判定「⚠️ 无 cli.py」为当时事实，按 §0 v2.2 回写 | 杨佳莹（表维护人回写） | 2026-11-23 |
| C9 | 跨时区下按本地日历日正确归属（东八区 23:30 的提交计入当日） | TK-V2-603 | `test_models.py::test_local_date_utc8_boundary` | `1 passed in 0.09s` | ✅ 通过 | UTC+8 23:30 → 当日、次日 00:00 → 次日 ✅；UTC 16:00 的 `.date()` 得前一日而 `local_date()` 得次日，差异被专打 ✅ | 赵蕊 | 2026-11-19 |
| C10 | `main`/`dev` push 带 3 commit → 飞书群恰 1 条、含「日报」二字、列全 commit 原文、显示中文名、`code=0`；feature 分支 0 次；失败亮红灯 | TK-V2-803/804（U2 闭环） | `test_notify_push.py` 9 用例（含 `test_main_push_sends_exactly_one_message_with_all_commits`）<br>`test_notify_workflow.py` 7 契约用例 | `9 passed in 2.83s` + `7 passed in 0.13s`（2026-11-23 实测） | ✅ 通过 | 根 `notify.yml` 切 v2、v1 脚本停用；main/dev push 恰 1 条含「日报」+ 全 commit 原文 + 中文名 + `code=0` ✅；feature 分支 0 次 ✅；飞书 `code!=0` / 缺凭证 → exit 1 亮红灯 ✅；未映射身份回落、不写 SQLite ✅；CI 4 run 全 success（`45033546323` 两步均 success）。原 11-19 判定「❌ 无被测对象」为当时事实，按 §0 v2.1 回写，不倒填。**飞书群真实消息正文待本人目视确认** | 杨佳莹（表维护人回写） | 2026-11-23 |
| C10（历史判定，留痕） | 同上 | TK-V2-U2 | 无 | 未执行 | ❌ 未覆盖 | 2026-11-19 原判：v2 无 `notify.yml` / 无 push 实时提醒实现，无被测对象；已作 U2 上报。**本行仅作历史留痕，结论已被上方 v2.1 行取代** | 赵蕊 | 2026-11-19 |

## 3. 实际输出摘要（全量测试 + 覆盖率）

命令：`./.venv/Scripts/python.exe -m pytest -q --cov=smart_daily_v2 --cov-report=term-missing`
时间：2026-11-19 21:55 | Python 3.14.2（`.venv`）| HEAD `c917978` + ruff 修复已提交（工作区干净）

```
Name                                       Stmts   Miss  Cover   Missing
------------------------------------------------------------------------
src\smart_daily_v2\__init__.py                 0      0   100%
src\smart_daily_v2\config.py                  14      1    93%   43
src\smart_daily_v2\identity.py                12      0   100%
src\smart_daily_v2\models.py                  32      0   100%
src\smart_daily_v2\notifiers\dispatch.py      43      4    91%   46-47, 57-58
src\smart_daily_v2\notifiers\email.py         37      1    97%   54
src\smart_daily_v2\notifiers\members.py       20      1    95%   16
src\smart_daily_v2\notifiers\webhook.py       44      2    95%   57-60
src\smart_daily_v2\reports\generator.py       35      0   100%
src\smart_daily_v2\sources\base.py            15      0   100%
src\smart_daily_v2\sources\fallback.py        21      0   100%
src\smart_daily_v2\sources\mock.py            14      0   100%
------------------------------------------------------------------------
TOTAL                                        287      9    97%
126 passed in 1.40s
```

> 上述 module 级数字与 `Missing` 列取自同批次 `--cov-report=term-missing` 输出；
> 原始输出归档于 `v2/docs/testing/证据/pytest-cov-20261119.txt`（607 验收④）。

## 4. 分组执行记录（可逐条复现）

判定所用的全部命令与真实输出，2026-11-19 21:50 本机执行：

| C | 命令 | 真实输出 |
| --- | --- | --- |
| C1 | `pytest test_generator.py::test_personal_report_counts_all_items -q --tb=no` | `1 passed in 0.10s` |
| C2 | `pytest test_fallback.py::test_exception_source_falls_back_to_next ::test_multiple_fallbacks_accumulate_reasons_in_order ::test_all_sources_error_not_swallowed_as_single_failure -q --tb=no` | `3 passed in 0.14s` |
| C3 | `pytest test_integration_identity.py::test_case_whitespace_variants_merge_to_one_group ::test_different_people_not_merged test_generator.py::test_same_member_from_multiple_accounts_merges -q --tb=no` | `3 passed in 0.10s` |
| C4 | `pytest test_generator.py::test_team_report_lists_all_members_without_truncation ::test_team_report_entry_lines_match_personal test_integration_format.py::test_both_reports_share_single_format_item_source -q --tb=no` | `3 passed in 0.16s` |
| C7 | `pytest test_integration_delivery.py::test_six_channels_all_true_is_delivered ::test_three_of_six_true_is_not_delivered -q --tb=no` | `2 passed in 0.33s` |
| C8 | `pytest test_fallback.py::test_all_sources_fail_raises test_generator.py::test_personal_report_empty_day ::test_team_report_all_empty_day -q --tb=no` | `3 passed in 0.13s` |
| C9 | `pytest test_models.py::test_local_date_utc8_boundary -q --tb=no` | `1 passed in 0.09s` |
| C10 | `pytest tests/test_notify_push.py tests/test_notify_workflow.py -q --tb=no`（2026-11-23） | `16 passed in 4.07s`（分项 9 + 7） |

**已废弃的旧命令**：`pytest -k "C1 or C2 or C3 or C4 or C7 or C8 or C9"`（v1.0 使用）。
该命令输出 `1 passed, 115 deselected`——因为 v2 用例名不含 C 编号字样，只有一条用例恰好命中关键字，**不能作为任何 C 的证据**，本版删除并改用上表的精确 nodeid。

## 5. 未覆盖项与承接任务

| C | 判定 | 缺口与承接 |
| --- | --- | --- |
| C1 | ✅ 已覆盖（2026-11-23 回写） | 第三源 feishu_chat 缺口已补，三源同报逐条 1:1；详见 §0 v2.2 与 §2 C1 行 |
| C2 | ✅ 已覆盖（2026-11-23 回写） | GitHub 源已实现，假 token 401 抛 `SourceUnavailableError`；详见 §0 v2.2 与 §2 C2 行 |
| C5 | ✅ 已覆盖（2026-11-23 回写） | `storage.py` 已实现，同日同成员 upsert 幂等；详见 §0 v2.2 与 §2 C5 行 |
| C8 | ✅ 已覆盖（2026-11-23 回写） | `cli.py` 已实现，返回码 1/2 有专测；详见 §0 v2.2 与 §2 C8 行 |
| C6 | ⏭ 观察项 | 按 607 验收③单列，不进硬验收；恢复条件见 §2 |
| C10 | ✅ 已覆盖（2026-11-23 回写） | `TK-V2-803/804` 落地，9+7 用例实测通过、CI 4 run 全绿；详见 §0 v2.1 与 §2 C10 行 |

> 本节现无 ❌/⚠️ 未覆盖项；四条原缺口（C1/C2/C5/C8）均于 2026-11-23 经实测补齐并回写，历史判定见 §0 v2.1/v2.2 修订说明。

## 6. 判定分布统计（10 条全计）

| 判定 | 条数 | C 编号 |
| --- | --- | --- |
| ✅ 通过 | 9 | C1、C2、C3、C4、C5、C7、C8、C9、C10（其中 C1/C2/C5/C8/C10 为 2026-11-23 回写） |
| ⚠️ 部分覆盖 | 0 | — |
| ❌ 未覆盖 | 0 | — |
| ⏭ 观察项 | 1 | C6 |
| **合计** | **10** | C1–C10 |

> 计入硬验收判定（排除观察项 C6）共 9 条：通过 9 / 部分 0 / 未覆盖 0。**该 9/9 为 2026-11-23 回写后结论**（C1/C2/C5/C8/C10 五条原缺口经实测补齐），非 11-19 时点的 4/9；历史判定见 §0 v2.1/v2.2，不倒填。
> **不虚报通过率**：按「✅ 通过 ÷ 9」为 100%，但仅指 C1–C10 十条成功标准的**可测判定**；C6 为性能观察项（不进硬验收），飞书群真实消息正文仍待本人目视确认，不据此宣称"全部真实场景已验证"。

## 7. 与其它交付物的对应

| 本表项 | 对应文件 |
| --- | --- |
| 607 验收④（`pytest --cov` 与 `ruff check` 原始输出归档） | `v2/docs/testing/证据/pytest-cov-20261119.txt`、`ruff-check-20261119.txt` |
| 覆盖率门槛与静态扫描门禁 | `v2/docs/赵蕊-CI门禁与静态扫描归档.md` §4、§5 |
| 未覆盖项上报 | `v2/specs/tasks.md` §8.2（U1–U8） |
