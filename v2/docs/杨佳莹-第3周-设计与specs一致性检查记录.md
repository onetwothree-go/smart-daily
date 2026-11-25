<img width="1809" height="624" alt="image" src="https://github.com/user-attachments/assets/047b779e-e684-4519-b63b-9fd00b637395" /># 第 3 周 设计与 specs/ 一致性检查记录

**检查人**：杨佳莹（架构师）
**检查日期**：2026-11-18
**检查范围**：`v1/specs/design.md` 0.6、`v1/specs/proposal.md` 0.4.4、`v2/specs/tasks.md` 0.1.1、`v2/README.md`，以及 dev 分支当前 `v2/src/` 已落地代码
**检查口径**：设计结论是否已完整、无冲突地进入 specs 与实现；「尚未实现的任务」不算不一致，「已裁定并回填的冲突」按闭环登记

---

## 一、检查方法

全部结论可用以下命令复跑，不依赖口头记忆：

```bash
cd D:/pro/smart-daily
git log --oneline -30                                  # 改动与责任人对账
grep -n "REPORT_RECIPIENTS\|应送达\|len(groups)" v1/specs/design.md v2/specs/tasks.md v2/README.md
grep -n "push_status\|all(\|any(" v2/specs/tasks.md v2/README.md
grep -rn "casefold\|normalize_key" v2/src/smart_daily_v2/
grep -rn "v1/\|from smart_daily\." v2/src v2/tests v2/pyproject.toml
git status --short
```

---

## 二、一致项（核对通过）

| 编号 | 检查点 | 设计结论 | specs / 实现落点 | 结论 |
| --- | --- | --- | --- | --- |
| P-01 | 空列表语义（K1 / U1） | ADR-103：异常才降级，空列表 = 该源当天无数据、属合法结果 | `v2/README.md` §2 已由 `58d4fec` 改；`tasks.md` TK-V2-104 验收②与 §8.2 U1 行由 `075f692` / `3a730bf` / `14a919f` 同步 | 一致，已闭环 |
| P-02 | 团队日报双通道（K6） | design 3.3 / 3.4：群 `send(subject, body, [])` + `REPORT_RECIPIENTS` 外部邮件，各自 1 条回执，`scope` 为 `team` / `team:report_recipients` | `v2/README.md` §2、`tasks.md` TK-V2-404 验收①、TK-V2-605 验收①均为 4 邮件 + 1 群 + 1 外部邮件 | 一致 |
| P-03 | 未配置外部收件人时的应送达数（U6） | design 3.4 第 3 条：退回 `len(groups) + 1`（本期 5 条），不判失败 | `tasks.md` TK-V2-404 验收⑤、§8.2 U6 行逐字对齐；605 的「6 条」指已配置外部收件人的场景，两者不冲突 | 一致 |
| P-04 | 送达判定（K2 / R3） | design 3.4：`pushed == (push_status == "ok")`，禁用 `any()`；五态 `ok/partial/failed/no_channel/skipped` | `tasks.md` TK-V2-501 Interfaces 返回 9 键、验收⑤五态与不变量；TK-V2-404 验收③④ 禁用 `any()` | 一致 |
| P-05 | keyword-only 调用（K5） | `collect(*, since, until, author=None)` | `tasks.md` TK-V2-103 Interfaces、`base.py::WorkSource.collect` 签名逐字一致 | 一致 |
| P-06 | 全失败异常继承（K8） | `AllSourcesUnavailableError(SourceUnavailableError)`，子类自实现 `__init__` 调 `super()` | `tasks.md` TK-V2-103 验收④、`base.py` 实现及 `test_all_sources_error_is_catchable` | 一致 |
| P-07 | 归一化单点（K4 方案甲） | 采集器只产 `RawRecord`，`normalize()` 唯一调用点在 TK-V2-104 的 `fallback.py`，下游禁二次归一化（G7） | `tasks.md` TK-V2-102「归一化单点」段、TK-V2-104 验收④；当前 `models.py` 只提供定义、未在别处调用 | 一致；104 未实现属进度问题，不是契约冲突 |
| P-08 | v2 从零实现、目录隔离 | 指导书第 18 页任务 2：新建 v2 目录、禁止复制阶段一源代码，设计结论只以文字带入 | `grep -rn "v1/\|from smart_daily\." v2/src v2/tests v2/pyproject.toml` → 0 命中；`v2/README.md` 只列 ADR 结论 | 一致 |

---

## 三、不一致项与整改建议

### C-01 · 身份归并键的「唯一实现」在设计里是单点、代码里是双点

**等级**：建议（P2）

- **依据**：`v1/specs/design.md` 2.2「映射解析收敛到唯一实现：`identity.py`」「同一逻辑只写一遍」（RT-06）；`tasks.md` TK-V2-101 交付物与 Interfaces 只认 `identity.py` 的公开函数。
- **现状**：`v2/src/smart_daily_v2/identity.py` 中 `normalize_key()` 写 `raw.strip().casefold()`，`normalize_members()` 又写一遍 `key = raw.strip().casefold()`，没有调用前者。
- **影响**：当前行为一致；但归属规则一旦调整（例如加 Unicode 归一化、改空串处理），两处必须同步改，漏一处就会出现「单键归一」与「批量归并」两套口径，正是 RT-06 要消除的问题。
- **建议**：`normalize_members()` 内部改为调用 `normalize_key(raw)`，保留一个实现点；补一条用例验证两函数对同一输入产出同一键。

### C-02 · naive `datetime` 的归属日语义只在实现里有，设计与 specs 未写明

**等级**：建议（P2）

- **依据**：`v1/specs/design.md` 2.2 只规定归属日按东八区计算（R4）；`tasks.md` TK-V2-102 验收④只给带 `+08:00` 与 `Z` 的用例。两处均未写「无时区信息的时间戳按什么处理」。
- **现状**：`models.py::local_date()` 对 `ts.tzinfo is None` 直接返回 `ts.date()`，即视作已是东八区本地时间。
- **影响**：若 201–203 某个采集器从上游拿到 naive UTC 时间戳（不带 `Z`），会直接取到 UTC 日期，跨日条目归错一天；而现有 R4 用例全部带 tzinfo，测不到这条分支。
- **建议**：在 design 2.2 与 tasks 102 各补一句契约——「naive 输入视为已按东八区归一化的本地时间，采集器负责把上游 UTC 时间补上 tzinfo」；并在 `test_models.py` 加一条 naive 输入的边界用例。

### C-03 · 采集层缺凭证的异常类型在 README 与实现之间缺一个落点

**等级**：建议（P2）

- **依据**：`v2/README.md` §2 与 `tasks.md` TK-V2-105 验收①要求「采集层缺凭证 → `SourceUnavailableError` 语义、不发 HTTP」；验收②要求「通知侧 `from_env()` 抛 `ValueError`」。
- **现状**：`config.py::require_credential()` 只抛 `ValueError`，没有把它包装成 `SourceUnavailableError` 的函数；`sources/base.py` 也只定义异常类型，不提供包装入口。
- **影响**：TK-V2-201/202/203 三个采集模块各自实现时会自行决定怎么转换，出现三种写法；与 README「缺凭证抛 `SourceUnavailableError`」的单一契约不符。
- **建议**：在 TK-V2-105 或 README §2 明确一句——「包装责任在采集器入口：`try: require_credential(...)` → `except ValueError as e: raise SourceUnavailableError(name, str(e))`；通知侧不包装」。不改现有 105 已落地的函数签名。

### C-04 · TK-V2-605 依赖未列主编排任务

**等级**：提示（P3）

- `tasks.md` TK-V2-605 依赖写「601、404」，但其验收②要求断言 `pushed=False`；`pushed` 由 TK-V2-501 `run()` 产出。
- 建议依赖补 501，或在验收②注明使用 501 的桩。不影响当前已完成任务，属依赖图维护精度问题。

### C-05 · TK-V2-404 验收②的通道数未区分是否配置外部收件人

**等级**：提示（P3）

- `tasks.md` TK-V2-404 验收②写「`no_notify=True` → 6 个通道调用次数全 0」，而验收⑤规定 `REPORT_RECIPIENTS` 未配置时应送达集合退回 5 条。
- 两处在同一任务内口径不完全一致：6 个只在外部收件人配置时成立。
- 建议②改为「配置外部收件人时 6 个、未配置时 5 个通道调用次数全 0」，与 ⑤ 和 U6 裁定对齐。

---

## 四、不在本次整改范围（仅登记）

- **U1 / U6** 已闭环，见 P-01 / P-03，不再计入未决项。
- **U2**（实时提醒是否纳入 v2）、**U3**（提交前缀口径）、**U4**（轮换表第 3 周仍「待定」）、**U5**（教师覆盖率阈值）与 **K7**（同口径待组内会）由组内会或对应责任人处理，不写成本次缺陷。
- **任务状态栏**（如 TK-V2-102/103 仍标 ⬜）由需求分析师按进度维护记录统一回填，架构师只提契约问题，不代改。
- **签字栏**待组内评审，本人不代签。

---

## 五、检查结论

设计结论进入 specs 的主链（K1、K2、K4、K5、K6、K8、U1、U6、目录隔离）**全部一致**；发现 3 条建议（P2）、2 条提示（P3），均为「文档未覆盖实现分支」或「同一规则多处实现」的精度问题，**无阻断项**。建议 C-01 / C-02 / C-03 在对应任务（101 / 102 / 105 的后续迭代或 104 开工前）由责任人逐条回应或修复，C-04 / C-05 由需求分析师随 tasks.md 下次维护一并改。

---

**签字**：

- 检查人：杨佳莹　日期：2026-11-18 
- 组内评审：于悦 ☑（2026-11-24）　方赫 ☐　赵蕊 ☑（2026-11-25）
