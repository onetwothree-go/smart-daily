# C1–C10 逐条核对表

**编制人**：赵蕊（测试工程师 / 配置管理员）
**对应任务**：TK-V2-607 · C1–C10 逐条核对表与覆盖率 / 扫描归档
**编制日期**：2026-11-19
**版本**：v2.0（2026-11-19 21:52 修订，修订内容见 §0）

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
| C1 | 当日 3 次提交 + 2 个任务 → 个人日报条目数 = 5、手工 0；条目与原始记录 1:1，同一动作跨三源按 3 条独立条目呈现 | TK-V2-604 | `test_generator.py::test_personal_report_counts_all_items` | `1 passed in 0.10s` | ⚠️ 部分覆盖 | 构造 3 提交（github）+ 2 任务（feishu_task）共 5 条，断言条目数 = 5 且逐条等于 `format_item(item)`（证明 1:1、零手工）✅；**缺飞书群消息第三源**，"三源独立呈现"仅两源 | 赵蕊 | 2026-11-19 |
| C2 | 假 `GITHUB_TOKEN` 注入 → 降级到 local-git、主流程不中断、日志记录降级原因 | TK-V2-602 | `test_fallback.py::test_exception_source_falls_back_to_next`<br>`::test_multiple_fallbacks_accumulate_reasons_in_order`<br>`::test_all_sources_error_not_swallowed_as_single_failure` | `3 passed in 0.14s` | ⚠️ 部分覆盖 | 源抛 `SourceUnavailableError` → 切下一源、主流程不中断 ✅；降级原因进 `reasons[]`（含源名与 reason 文本）且按序累积 ✅；**v2 无 GitHub 源（仅 mock）**，故"假 token 实际注入"场景无对应实现 | 赵蕊 | 2026-11-19 |
| C3 | 同一成员多个 GitHub 登录名归并为一份日报、不串人 | TK-V2-606 / 101 | `test_integration_identity.py::test_case_whitespace_variants_merge_to_one_group`<br>`::test_different_people_not_merged`<br>`test_generator.py::test_same_member_from_multiple_accounts_merges` | `3 passed in 0.10s` | ✅ 通过 | 大小写 / 首尾空格变体归一组 ✅；不同人**不**合并 ✅；`record_id` 互不相交、无归并丢失 ✅；未映射身份告警且不丢（`test_unmapped_identity_warns_and_not_dropped`）✅ | 赵蕊 | 2026-11-19 |
| C4 | 团队日报含全部 4 位成员条目，与个人日报**条目行格式逐字一致**；20 条与 0 条成员均全量列出 | TK-V2-604 | `test_generator.py::test_team_report_lists_all_members_without_truncation`<br>`::test_team_report_entry_lines_match_personal`<br>`test_integration_format.py::test_both_reports_share_single_format_item_source` | `3 passed in 0.16s` | ✅ 通过 | 20 / 2 / 1 / 0 条四成员全列、统计头「成员 4 人 · 条目 23 条」✅；条目行与个人日报逐字比对 ✅；两报表经 `inspect.getsource` 证实共用同一 `format_item()` ✅ | 赵蕊 | 2026-11-19 |
| C5 | 同日重跑两次，SQLite 中 (日期,成员) 记录数不变、内容覆盖更新 | TK-V2-502/503 | 无 | 未执行 | ❌ 未覆盖 | **v2 无 `storage.py`、无任何 SQLite 落盘代码**，幂等语义无被测对象；待 5xx 层落地后补 | 赵蕊 | 2026-11-19 |
| C6 | 单成员 100 条提交采集耗时 < 30s（观察项） | —（原 TK-V2-607） | 不建计时用例 | 未执行 | ⏭ 观察项 | 按 607 验收③：性能为观察项、不进硬验收、不建计时用例。恢复为验收项的前置条件：fixture 注入 100 条 + 剥离真实网络 + 固定计时起止口径 + 组内评审 | 赵蕊 | 2026-11-19 |
| C7 | 4 封个人邮件 + 1 条飞书群 + 1 封团队外部邮件**全部 ok** 才算送达；一成一败不算送达 | TK-V2-404/605/601 | `test_integration_delivery.py::test_six_channels_all_true_is_delivered`<br>`::test_three_of_six_true_is_not_delivered` | `2 passed in 0.33s` | ✅ 通过 | 6 通道全 true → `pushed=True`，调用次数 4 personal / 1 team / 1 external ✅；3/6 true → **不判送达** ✅ | 赵蕊 | 2026-11-19 |
| C8 | 区分两种空：① 当天无数据 → 显式「今日无工作记录」、全组零记录时团队日照发；② 三源全不可用 → 必须抛明确异常，禁止静默返回空日报 | TK-V2-603（CLI 部分待 504） | `test_fallback.py::test_all_sources_fail_raises`<br>`test_generator.py::test_personal_report_empty_day`<br>`::test_team_report_all_empty_day` | `3 passed in 0.13s` | ⚠️ 部分覆盖 | 全失效抛 `AllSourcesUnavailableError`、errors 聚合完整 ✅；合法空产出「今日无工作记录」、团队日照发 ✅；**「CLI 返回码 1」无 `cli.py`**，无被测对象 | 赵蕊 | 2026-11-19 |
| C9 | 跨时区下按本地日历日正确归属（东八区 23:30 的提交计入当日） | TK-V2-603 | `test_models.py::test_local_date_utc8_boundary` | `1 passed in 0.09s` | ✅ 通过 | UTC+8 23:30 → 当日、次日 00:00 → 次日 ✅；UTC 16:00 的 `.date()` 得前一日而 `local_date()` 得次日，差异被专打 ✅ | 赵蕊 | 2026-11-19 |
| C10 | `main`/`dev` push 带 3 commit → 飞书群恰 1 条、含「日报」二字、列全 commit 原文、显示中文名、`code=0`；feature 分支 0 次；失败亮红灯 | TK-V2-U2 | 无 | 未执行 | ❌ 未覆盖 | **v2 无 `notify.yml` / 无 push 实时提醒实现**，无被测对象；已作 U2 上报（`tasks.md` §8.2），不静默略过 | 赵蕊 | 2026-11-19 |

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

**已废弃的旧命令**：`pytest -k "C1 or C2 or C3 or C4 or C7 or C8 or C9"`（v1.0 使用）。
该命令输出 `1 passed, 115 deselected`——因为 v2 用例名不含 C 编号字样，只有一条用例恰好命中关键字，**不能作为任何 C 的证据**，本版删除并改用上表的精确 nodeid。

## 5. 未覆盖项与承接任务

| C | 判定 | 缺口与承接 |
| --- | --- | --- |
| C5 | ❌ 未覆盖 | v2 无 `storage.py` / 无 SQLite 落盘代码，(日期,成员) 幂等语义无被测对象 → 待 TK-V2-502/503 |
| C8 | ⚠️ 部分覆盖 | 合法空与三源全失效已覆盖；「CLI 返回码 1」无 `cli.py` → 待 TK-V2-504 |
| C10 | ❌ 未覆盖 | v2 无 push 实时提醒 workflow → 已作 U2 上报（`tasks.md` §8.2） |
| C6 | ⏭ 观察项 | 按 607 验收③单列，不进硬验收；恢复条件见 §2 |

## 6. 判定分布统计（10 条全计）

| 判定 | 条数 | C 编号 |
| --- | --- | --- |
| ✅ 通过 | 4 | C3、C4、C7、C9 |
| ⚠️ 部分覆盖 | 3 | C1、C2、C8 |
| ❌ 未覆盖 | 2 | C5、C10 |
| ⏭ 观察项 | 1 | C6 |
| **合计** | **10** | C1–C10 |

> 计入硬验收判定（排除观察项 C6）共 9 条：通过 4 / 部分 3 / 未覆盖 2。
> **不虚报通过率**：若只按「✅ 通过 ÷ 9」计算为 44.4%，缺口的 3 条（C1、C2、C8 的子句）与 2 条未覆盖面（C5、C10）均因 v2 尚未落地对应实现，而非用例漏写。

## 7. 与其它交付物的对应

| 本表项 | 对应文件 |
| --- | --- |
| 607 验收④（`pytest --cov` 与 `ruff check` 原始输出归档） | `v2/docs/testing/证据/pytest-cov-20261119.txt`、`ruff-check-20261119.txt` |
| 覆盖率门槛与静态扫描门禁 | `v2/docs/赵蕊-CI门禁与静态扫描归档.md` §4、§5 |
| 未覆盖项上报 | `v2/specs/tasks.md` §8.2（U1–U8） |
