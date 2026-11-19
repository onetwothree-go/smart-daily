# 第 3 周 code-review 意见回应 · 方赫（开发工程师）

**回应人**：方赫（开发工程师 / 被评审人）
**回应日期**：2026-11-19
**评审来源**：`v2/docs/于悦-第3周-code-review互评记录.md`（提交 `fcc87c0`，2026-11-19），评审对象为本人 `4fdfdf0`（TK-V2-404）与 `29da6dc`（TK-V2-601），共 5 条意见（R1-01 / R1-02 / R2-01 / R2-02 / R2-03）
**起草说明**：逐条依据仓库真实 diff、`v2/specs/tasks.md` 与全 git 历史核实后回应，命令可复跑、行号可核对。**回应为草稿，结论、对方复检结果、是否闭环、本人签字与日期全部留空**，待本人逐条核对后填。按组纪律**不修改评审人文件**（其互评总表「对方回应」列由评审人本人核对后回填，本文件只提供回应内容）、不代勾 checkbox、不代签、不倒填、不自行改 `v2/specs/tasks.md`。
**依据**：指导书第七部分第 3 周角色产出表（全员 code-review 互评、合并前逐条回应）、`v2/specs/tasks.md` L47（G4「合并前执行 code-review 并逐条回应」）、L57（code-review 后由需求分析师逐条核对验收标准再勾销）、L494（补记注明时间、不倒填、不代签 G9）

---

## 一、逐条回应总表

| 编号 | 级别 | 意见摘要 | 回应结论 | 是否需改已推送代码 |
|---|---|---|---|---|
| R1-01 | 建议 P2 | 「应送达集合」不应由 `results` 反推；建议 605 补「`results` 缺一个 scope → 判 False」用例 | 部分接受 + 澄清（见 §二.1） | 否，登记为后续约束 |
| R1-02 | 提示 P3 | 异常原因被静默吞、`push_status` 五态缺判定依据 | 知悉，接受为后续约束（见 §二.2） | 否 |
| R2-01 | 建议 P2 | 601 验收②是测试内手写桩链自证，待 602 端到端复验 | 完全接受，双方口径一致（见 §二.3） | 否 |
| R2-02 | 建议 P2 | 称 `tasks.md` L379 变量名为 `REPORT_TGAVRGPBGE`、与其他处不一致 | **如实反馈：该事实前提不成立**，提请评审人复核（见 §二.4） | 否，不代改他人文档 |
| R2-03 | 提示 P3 | golden 数据只锁 `record_id`，602–606 对账可能漂移 | 接受，登记为后续约束（见 §二.5） | 否 |

> 5 条意见均经评审人注明「不构成本提交缺陷 / 属后续任务约束」，且 0 条阻断。故本轮**不改动任何已推送代码**，需落实部分全部登记为后续任务约束，待组内裁定或主线（104/501/602）解除后处理。

---

## 二、逐条回应明细

### R1-01｜应送达集合的来源（建议 P2）— 部分接受 + 澄清

**核实事实**（`git show 4fdfdf0`、`git show b643beb` 可复跑）：

- 404 的 `v2/tests/test_dispatch.py` L145 已有 `test_all_delivered_missing_scope_is_false`：`expected = {"personal:member-1", "team"}` 为**独立固定集合**、`results` 只给 1 个 scope，断言 `all_delivered(...) is False` —— 即「`expected` 独立构造 + `results` 缺 scope → 判 False」在 404 单元测试层已覆盖。
- 605 的 `v2/tests/test_integration_delivery.py` L44 已有 `test_expected_set_is_exactly_six_scopes`：断言 `outcome.expected == set(SCOPES)`（固定 6 条）、无 realtime/push scope、`set(outcome.results) == outcome.expected`。
- 但本人如实承认：605 的 `v2/tests/conftest.py` L90 为 `expected = set(results)`，**确由回执反推**（该 harness 是集成胶水，模拟编排层注入的应送达集合，设计上就拿 `dispatch` 实际回执当 expected）；且 605 **没有**「`results` 缺一个 scope、而 `expected` 仍固定 6 条 → 判 False」的用例。R1-01 对 605 的建议成立。

**回应**：接受「应送达集合须由编排层独立构造」这一原则，R1-01 指向的 v1 坑 2 风险属实。澄清两点：① 该原则的落点是被 104 阻塞的 501/502 编排层，404 分发层职责只产出 `dict[scope, bool]`，其单元测试已按独立 `expected` 验证 `all_delivered`；② 605 harness 的 `expected = set(results)` 是**测试夹具内部**构造，不代表生产编排层口径，但确未覆盖「缺 scope」场景。

**后续动作（登记，不本轮执行）**：501 显式按 `set(personal)` 映射 + `team` [+ `team:report_recipients`] 构造 `expected`；605 若需补「固定 expected 6 条、`results` 缺 1 个 scope → False」用例，因 605 已提交推送，须经本人确认后走独立提交，不擅自改已推送代码。

### R1-02｜异常原因与五态判定（提示 P3）— 知悉，接受为后续约束

**核实事实**：`dispatch.py` 三路 `except Exception: return False` 是按 402 验收②（R5「返回 False、不抛异常」）与 N8「不重试」契约**有意为之**；`no_notify=True` 返回 `{}`，`all_delivered(set(), {})` 按 404 `test_dispatch.py` L141 明确返回 `False`。

**回应**：`push_status` 五态（ok / partial / failed / no_channel / skipped）属 K2 规定的 501/502 编排层职责，404 分发层不判五态；评审人亦写明「不构成本提交缺陷」。接受建议：**501 落地时**在调用 `dispatch` 前显式分流 `no_notify` 与通道配置探测，`dispatch` 侧可加 `logger.warning` 记录失败原因；均登记为后续约束，本轮不改代码。

**关于「无独立失败测试在先的提交号」**：如实说明——本组 TDD 采用「一次提交同时新增 src 与 tests」，红态证据留在 Claude Code 会话 pytest 输出截图与 `v2/docs/方赫-红绿循环记录-第3周.md` 的红段，均已在记录中如实注明，不倒填提交号、不虚构独立红提交。评审人已在进度维护记录 §四第 9 条登记，本人知悉。

### R2-01｜601 验收② 桩链自证（建议 P2）— 完全接受，口径一致

**核实事实**：601 红绿记录与 `docs/ai-usage-log.md` 601 补记均明确写「以测试内桩链（FakeFormalSource + run_chain，ADR-103 语义）隔离验证、未把降级链写进 src、未改 `base.py`、待 602 端到端复验」。

**回应**：与评审人 R2-01「条件达成 / 待端到端复验 / 不判不合格、不勾销」**完全一致，无需澄清**。602 解除 ⏸ 后补一条直接调用 `collect_with_fallback()` 的用例，断言无凭证且未显式 `--mock` 时结果不含 `mock-` 前缀 `record_id`。当前 602 仍 ⏸（issue #14 K1 口径待组内裁定），本人**不擅自解除 ⏸、不擅自改 `tasks.md`**。

### R2-02｜变量名两处不一致（建议 P2）— 如实反馈：事实前提不成立，提请评审人复核

评审记录 §三 R2-02 称「`v2/specs/tasks.md` L379（401 验收④）写的是 `REPORT_TGAVRGPBGE`，而 L400 / L542 / design 均为 `REPORT_RECIPIENTS`」。本人按「不伪造证据、命令可复跑」原则核实如下：

| 核实命令 | 实际结果 |
|---|---|
| `sed -n '379p' v2/specs/tasks.md` | ④ 为 `给定 REPORT_RECIPIENTS="a@x.com, b@x.com" → load_report_recipients() 返回 2 个…`，**不是** `REPORT_TGAVRGPBGE` |
| `git log --all --oneline -S "REPORT_TGAVRGPBGE" -- v2/specs/tasks.md` | **0 命中**（该串从未进入 `tasks.md`） |
| `git grep -l "REPORT_TGAVRGPBGE" $(git rev-list --all)` | 仅命中 `fcc87c0` / `b643beb` 两版的《于悦-第3周-code-review互评记录.md》与《于悦-第3周-tasks进度维护记录.md》，即**只存在于评审人自己的两份文档中**；从未出现在 `tasks.md` / `README.md` / `design.md` / `src/` / `tests/` |
| 代码侧口径 | `members.py` L25 `load_report_recipients` 读 `REPORT_RECIPIENTS`；`conftest.py` L11 `cleared_env` 清 `REPORT_RECIPIENTS`；`test_notifiers.py` L24 同名 → **本就一致，`cleared_env` 不漏清** |

**回应**：当前 dev 上「变量名两处不一致」的事实前提不成立，验收①「清空所有凭证」无风险；疑为评审记录起草时的转述/誊写误差。按组纪律，本人**不代改评审人文档、不改 `v2/specs/tasks.md`**，仅把可复跑核实结果如实登记，提请评审人本人核对后决定是否修订记录文本（走组内 / issue）。此条不否定评审人其余意见，也不代填其结论。

### R2-03｜golden 只锁 `record_id`（提示 P3）— 接受，登记为后续约束

**核实事实**：601 `v2/tests/test_mock.py` L34–43 的 `test_fixture_record_ids_stable_and_unique` 确只比对 `[row["record_id"] for row in golden_rows]`；605 `v2/tests/test_integration_delivery.py` L93–101 也只比两次 `record_id` 稳定。其余 6 字段（member / kind / title / detail / occurred_at / source）**未与 golden 做结构化全字段对账**。

**补充（如实）**：601 绿阶段本人曾在本地终端用 Python 实跑全字段对账（record_id / member / kind / title / detail / occurred_at 全等），并写入红绿记录与 AI 日志补记，但**未落成仓库内测试用例** —— 评审人「仓库内测试缺全字段对账」的判断属实。

**后续动作（登记）**：602–606 对账用例补一条 `fixture_items` 与 `golden_rows` 的结构化全字段比对（`occurred_at` 统一成 ISO 串、`local_day` 单独算）。评审人已写明「不构成本提交缺陷」，本轮不改代码。

---

## 三、核实命令（可复跑）

```bash
cd D:/projects/smart-daily
sed -n '379p' v2/specs/tasks.md                                  # R2-02：L379 实为 REPORT_RECIPIENTS
git log --all --oneline -S "REPORT_TGAVRGPBGE" -- v2/specs/tasks.md  # R2-02：0 命中
grep -n "missing_scope\|expected" v2/tests/test_dispatch.py     # R1-01：404 已有缺 scope 用例
grep -n "expected" v2/tests/conftest.py                         # R1-01：605 harness L90 反推属实
grep -n "record_id" v2/tests/test_mock.py                       # R2-03：601 只锁 record_id 属实
```

---

## 四、回应人声明

我回应的是评审人 5 条意见与仓库真实 diff / `v2/specs/tasks.md` / 全 git 历史的一致性，依据可复跑命令与行号核对，不虚构、不掩盖（R1-01 的 605 harness 反推、R2-03 的仓库内未落测试用例均如实承认）、不把「待实现任务」写成缺陷、不改评审人文件、不代勾 checkbox、不代签、不倒填、不代填评审人的结论与签字。

## 五、待本人确认

- 上述 5 条回应逐条复核：☐ 待确认
- 是否需就 R2-02 走组内 / issue 提请评审人复核：☐ 待确认
- 是否就 R1-01 / R2-03 补独立提交（改已推送的 605 测试）：☐ 待确认
- 对方复检结果：__________（留空）
- 是否闭环：☐ 待确认
- 回应人签字：__________　日期：__________（**均留空，待本人确认**）
