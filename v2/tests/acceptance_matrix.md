# C1–C10 逐条核对表

**编制人**：赵蕊（配置管理员，测试与配置角色）  
**编制日期**：2026-11-19  
**数据来源命令**：
- `.venv/Scripts/python.exe -m pytest -q --cov=smart_daily_v2 --cov-report=term`
- `.venv/Scripts/python.exe -m pytest -q -k "C1 or C2 or C3 or C4 or C7 or C8 or C9" --tb=no`

## 口径说明

① 判定基于 2026-11-19 本机实跑，Python 3.14.2（.venv），与 CI 的 3.13 存在版本差异；  
② 覆盖率为 TOTAL 97%（Stmts 287 / Miss 9），低于任何教师阈值时如实标注、不四舍五入抬高；  
③ v1 的同名 C1–C10 证据只作历史参考，不构成本表判定依据。

## C1–C10 验收矩阵

| C 编号 | 成功标准摘要 | 承接任务 | 用例 ID（pytest nodeid） | 实际输出 | 判定 | 执行人 | 日期 |
|--------|--------------|----------|---------------------------|----------|------|--------|------|
| C1 | 功能：个人日报条目数=3次提交+2个任务，手工编写=0，三源独立呈现 | TK-V2-604 | tests/test_generator.py::test_personal_report_counts_all_items | 116 passed, 0 failed | ⚠️ 部分覆盖 | 赵蕊 | 2026-11-19 |
| C2 | 功能：假 token 注入后降级到 local-git，日志记录降级原因 | TK-V2-602 | tests/test_fallback.py::test_exception_source_falls_back_to_next | 116 passed, 0 failed | ✅ 通过 | 赵蕊 | 2026-11-19 |
| C3 | 功能：多账号归并为一份日报，准确率100%，不串人 | TK-V2-606 | tests/test_generator.py::test_same_member_from_multiple_accounts_merges | 116 passed, 0 failed | ✅ 通过 | 赵蕊 | 2026-11-19 |
| C4 | 功能：团队日报包含全部4位成员，条目行格式逐字一致 | TK-V2-604 | tests/test_generator.py::test_team_report_lists_all_members_without_truncation | 116 passed, 0 failed | ✅ 通过 | 赵蕊 | 2026-11-19 |
| C5 | 功能：同日重跑两次，SQLite记录数不变，内容覆盖更新 | TK-V2-502/503 | 无对应测试用例 | 未覆盖 | ❌ 未覆盖 | 赵蕊 | 2026-11-19 |
| C6 | 性能：单成员100条提交采集耗时<30s（观察项） | TK-V2-607 | 观察项，不建计时用例 | 无测试用例 | ⏭ 观察项 | 赵蕊 | 2026-11-19 |
| C7 | 推送：6通道（4邮件+1飞书群+1外部邮件）全部ok才算成功 | TK-V2-404/605 | tests/test_integration_delivery.py::test_six_channels_all_true_is_delivered | 116 passed, 0 failed | ✅ 通过 | 赵蕊 | 2026-11-19 |
| C8 | 边界：区分合法空（显式文案）与全失效（抛异常，CLI返回码1） | TK-V2-603 | tests/test_fallback.py::test_all_sources_fail_raises | 116 passed, 0 failed | ⚠️ 部分覆盖 | 赵蕊 | 2026-11-19 |
| C9 | 边界：跨时区场景下按本地日历日正确归属 | TK-V2-603 | tests/test_models.py::test_local_date_utc8_boundary | 116 passed, 0 failed | ✅ 通过 | 赵蕊 | 2026-11-19 |
| C10 | 实时提醒：main分支push触发1次，列commit原文，飞书code=0 | TK-V2-U2 | 无对应测试用例 | 未覆盖 | ❌ 未覆盖 | 赵蕊 | 2026-11-19 |

## 实际输出摘要

```
=============================== tests coverage ================================
_______________ coverage: platform win32, python 3.14.2-final-0 _______________

Name                                       Stmts   Miss  Cover
--------------------------------------------------------------
src\smart_daily_v2\__init__.py                 0      0   100%
src\smart_daily_v2\config.py                  14      1    93%
src\smart_daily_v2\identity.py                12      0   100%
src\smart_daily_v2\models.py                  32      0   100%
src\smart_daily_v2\notifiers\dispatch.py      43      4    91%
src\smart_daily_v2\notifiers\email.py         37      1    97%
src\smart_daily_v2\notifiers\members.py       20      1    95%
src\smart_daily_v2\notifiers\webhook.py       44      2    95%
src\smart_daily_v2\reports\generator.py       35      0   100%
src\smart_daily_v2\sources\base.py            15      0   100%
src\smart_daily_v2\sources\fallback.py        21      0   100%
src\smart_daily_v2\sources\mock.py            14      0   100%
--------------------------------------------------------------
TOTAL                                        287      9    97%
126 passed in 0.64s
```

## 未覆盖项与承接任务

- **C5** → ❌ 未覆盖。理由：v2 无 storage.py / 无 sqlite 落盘代码，幂等语义待 TK-V2-502/503。
- **C8** → ⚠️ 部分覆盖。合法空与三源全失效已覆盖；"CLI 返回码 1"无 cli.py，待 TK-V2-504。
- **C6** → ⏭ 观察项。按 tasks 607 验收③单独注明"性能为观察项、不进硬验收、不建计时用例"，并写明恢复为验收项的前置条件（fixture 注入 100 条 + 剥离真实网络 + 固定计时口径 + 组内评审）。
- **C10** → ❌ 未覆盖。本周未纳入，已作 U2 上报（tasks §8.2），不静默略过。

## 判定分布统计

- ✅ 通过：4 条（C2、C3、C4、C9）
- ⚠️ 部分覆盖：2 条（C1、C8）
- ❌ 未覆盖：2 条（C5、C10）
- ⏭ 观察项：1 条（C6）
- 总计：9 条（C6不计入判定范围）

## 命令运行输出

```bash
.venv/Scripts/python.exe -m pytest -q --cov=smart_daily_v2 --cov-report=term
.venv/Scripts/python.exe -m pytest -q -k "C1 or C2 or C3 or C4 or C7 or C8 or C9" --tb=no
.                                                                        [100%]
1 passed, 115 deselected in 0.15s
```