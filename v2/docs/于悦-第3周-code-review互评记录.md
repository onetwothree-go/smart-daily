# 第 3 周 code-review 互评记录 · 于悦（需求分析师）

**评审人**：于悦（需求分析师）
**评审日期**：2026-11-19
**评审范围**：dev 分支他人真实提交 2 条（均为方赫本周代码提交）；只评「提交内容与 `v2/specs/tasks.md` 验收标准 / 契约的一致性」，不改他人文件、不代签、不倒填
**起草说明**：本记录依据 GitHub 远端 dev 实际 diff、`v2/specs/tasks.md` 0.1.1 与组内已有评审记录起草，命令可复跑、行号可核对。**签认（2026-11-24）**：评审人签字、评审日期、结论与工作流执行情况由本人签认；对方回应据 `v2/docs/方赫-第3周-code-review意见回应.md` 如实登记，R2-02 异议待本人复检、不代判对错。
**依据**：指导书第七部分第 3 周角色产出表「全员：code-review 互评（每人每周至少评审他人 2 次提交并留意见）」、任务书第 5 条、自查清单第 6 条

---

## 一、本周互评总表

| 序号 | 日期 | PR / 提交号 | 被评审人 | 对应任务编号 | 用了哪个工作流 | 我提的意见（条数） | 对方回应 | 是否闭环 |
|---|---|---|---|---|---|---|---|---|
| 1 | 2026-11-19 | `4fdfdf0` | 方赫（fh0709） | TK-V2-404 | ☑ 是（人工逐行核对 git diff + 规范原文，见 §二评审方式）—— 本人签认 11-24 | 2（R1-01 / R1-02） | 方赫 11-19 逐条回应：R1-01 部分接受+澄清、R1-02 知悉接受为后续约束，均不构成本提交缺陷、不改已推送代码（见 `方赫-第3周-code-review意见回应.md`） | ☑ 已回应、复检一致（11-24） |
| 2 | 2026-11-19 | `29da6dc` | 方赫（fh0709） | TK-V2-601 | ☑ 是（人工逐行核对 git diff + 规范原文，见 §三评审方式）—— 本人签认 11-24 | 3（R2-01 / R2-02 / R2-03） | 方赫 11-19 逐条回应：R2-01 完全接受、R2-03 接受为后续约束；R2-02 提出异议称「事实前提不成立」提请本人复核（见回应文件 §二.4） | ☐ 已回应，R2-02 待本人复检（11-24） |

> 已满足「至少 2 次」。选这两条的原因：都是 11-18 至 11-19 新交的代码提交、都是他人提交、验收标准可逐条对照；杨佳莹已评 `fcd1569`（103）与 `c850d86`（102）、赵蕊已评 `075f692` 等，不重复评同一提交。模板里原写的「周一 000/002/… 六条」为 11-17 起草时的备选对象，本次未采用。

---

## 二、第 1 次评审明细

- **提交号**：`4fdfdf0`
- **作者 / 时间**：方赫 ｜ 2026-11-18 23:17（北京时间；API 原始 `2026-11-18T15:17:11Z`）
- **提交内容**：`feat: [TK-V2-404] 实现分发规则与送达判定`
- **对应任务**：`v2/specs/tasks.md` §6 TK-V2-404（L396–401），依赖 402 / 403 / 304
- **评审范围（改了哪些文件）**：新增 `v2/src/smart_daily_v2/notifiers/dispatch.py`（+64）、`v2/tests/test_dispatch.py`（+149）；另 `docs/ai-usage-log.md` +8、`v2/docs/方赫-红绿循环记录-第3周.md` +7。代码改动只在 `v2/`，符合目录隔离，未碰 v1 代码。

### 评审方式（可复跑）

1. `git show 4fdfdf0 --stat` → 4 文件，如上。
2. 对照远端 `v2/src/smart_daily_v2/notifiers/dispatch.py`（64 行）与 `v2/tests/test_dispatch.py`（149 行）逐行核。
3. 对照 `v2/specs/tasks.md` L399（Interfaces）、L400（验收①–⑤）、L50（G7）、L93（R3）、L409（501 验收③ / K2 五态）、L542（U6）。
4. 对照方赫 `v2/docs/方赫-红绿循环记录-第3周.md` 的 404 红绿段与 `docs/ai-usage-log.md` 当天补记。

### 验收标准逐条核对

| 验收 | 核对结果 |
|---|---|
| ① 6 通道回执、团队两路各自独立 try 各 1 条 | 属实。`dispatch.py` L43–58 三路各自 try、scope 分别为 `personal:*` / `team` / `team:report_recipients`；`test_dispatch.py` L34–75 有对应用例 |
| ② `no_notify=True` → 6 通道调用全 0 | 属实。L39–40 直接返回 `{}`；test L78–87 断言 `results == {}` 且三桩调用数合计 0 |
| ③ R3 禁止 `any()`，6 中 3 真判 False | 属实。L63–64 为 `bool(expected) and all(results.get(scope, False) ...)`，全文无 `any(`；test L106–124 部分送达判 False、L127–138 全真判 True |
| ④ `grep -n "any(" ... notifiers/` 0 命中 | 本提交新增的 `dispatch.py` 内 0 命中（同上）；其余通道文件的全目录自查见方赫红绿记录 |
| ⑤ `REPORT_RECIPIENTS` 未配置 → 退回 5 条、不判失败 | 属实。L54 `if team_recipients:` 才产生外部回执；test L90–103 断言 `len(results) == 5` 且 `all_delivered(set(results), results) is True` |

### 发现

**R1-01｜建议（P2）——「应送达集合」的来源不能取自 `results` 本身**

- `test_dispatch.py` L103 用 `all_delivered(set(results), results)` 断言未配置外部收件人时判成功。此时 `expected` 直接由 `results` 的键生成，`all()` 实际只检查「已产生的回执是否都为 True」，**不构成 R3 要求的独立应送达集合校验**。
- 依据：L93 R3 原文「应送达集合 + `all()`」；L542 U6 裁定未配置时退回 `len(groups)+1`（5 条），是**由编排层按成员数算出的固定集合**，不是从回执反推；L409 501 验收③ 规定 `pushed` 由 `all_delivered()` 得出。
- 风险落点：若 501 沿用 `set(results)` 构造 `expected`，任何「少发一路但没写回执」的情形都会被 `all()` 放过，v1 坑 2 会从编排层复发。
- 建议：501 显式按 `set(personal)` 映射 + `team` [+ `team:report_recipients`] 构造 `expected`；605 补一条「expected 固定 5/6 条、`results` 缺一个 scope → 判 False」的用例。此项属后续任务约束，**不构成本提交缺陷**。

**R1-02｜提示（P3）——异常原因被静默吞掉，`skipped` / `no_channel` 两态缺判定依据**

- `dispatch.py` L14–15 / L21–22 / L28–29 / L46–47 / L51–52 / L57–58 全为 `except Exception: return False`，只留 `bool` 不留原因；L39–40 `no_notify=True` 返回 `{}`，而 `all_delivered(set(), {})` 按 test L141–142 明确断言返回 `False`。
- 依据：L409 K2 要求 `push_status` 五态 `ok / partial / failed / no_channel / skipped`；402 验收②（L386）R5 要求「返回 False、**记录原因**、不抛异常」。若缺凭证被吞成普通 False、或 `no_notify` 的空回执被当成全失败，501 无法区分 `no_channel` 与 `failed`、`skipped` 与 `partial`。
- 建议：501 在调用 `dispatch` 前显式分流 `no_notify` 与通道配置探测；`dispatch` 至少 `logger.warning` 记录失败原因。此项属后续任务约束，**不构成本提交缺陷**。
- 另按模板「红→绿可复跑」自查：本提交与 103/105 同为「一次提交同时新增 src 与 tests」，红态输出只写在方赫红绿记录与 AI 会话留痕，**无独立的失败测试在先的提交号**。方赫已在记录中如实注明，不据此否定本提交，但本人复核红态可复现性时需留意（已在进度维护记录 §四第 9 条登记）。

- 这次合并前是否执行了 code-review 工作流：☑ 是（人工逐行核对 git diff + 规范原文，见上文「评审方式」）　☐ 否 —— 本人签认 2026-11-24
- 结论：☑ 可合并　☐ 改完再合　评审人：于悦　日期：2026-11-24

---

## 三、第 2 次评审明细

- **提交号**：`29da6dc`
- **作者 / 时间**：方赫 ｜ 2026-11-19 00:11（北京时间；API 原始 `2026-11-18T16:11:33Z`）
- **提交内容**：`test: [TK-V2-601] 建立无凭证可复现夹具`
- **对应任务**：`v2/specs/tasks.md` §6 TK-V2-601（L435–439），依赖 102 / 103，并行组 P6-a
- **评审范围（改了哪些文件）**：新增 `v2/src/smart_daily_v2/sources/mock.py`（+139）、`v2/tests/conftest.py`（+27）、`v2/tests/fixtures/README.md`（+5）、`v2/tests/fixtures/mock_work_items.json`（+92）、`v2/tests/test_mock.py`（+163）；另 `docs/ai-usage-log.md` +8、`v2/docs/方赫-红绿循环记录-第3周.md` +7。代码改动只在 `v2/`，`test:` 前缀符合 L439。

### 评审方式（可复跑）

1. `git show 29da6dc --stat` → 7 文件，如上。
2. 对照远端 `sources/mock.py`、`tests/test_mock.py`（163 行）、`tests/conftest.py`、`tests/fixtures/mock_work_items.json`（10 条 × 7 字段）逐行核。
3. 对照 `v2/specs/tasks.md` L438（601 验收①–④）、L441–445（602 验收）、L379（401 验收④）、L400（404 验收①）、L542（U6）。
4. `29da6dc` 的 CI 三项（Ruff / 测试+覆盖率 / 飞书提醒）经 GitHub API 复核均 success。

### 验收标准逐条核对

| 验收 | 核对结果 |
|---|---|
| ① 清空所有凭证仍能构造 4 人样例并产出完整日报 | 属实。`conftest.py` 的 `cleared_env` 清 `GITHUB_/FEISHU_/SMTP_/DAILY_/DB_` 前缀 + 三个具名变量；test L16–31 断言 4 人、首行「成员 4 人 / 条目 10 条」、无「今日无工作记录」 |
| ② mock 不出现在默认降级链 | **条件达成，待端到端复验**，见 R2-01 |
| ③ 稳定 `record_id` 供 602–606 对账复用 | 属实。10 条 `mock-001…010`，test L34–43 断言两次加载一致、唯一、`mock-` 前缀、与 golden_rows 顺序一致 |
| ④ 不是第四路正式数据源、不进 C1（文档 + 断言双保险） | 属实。`mock.py` 首部 docstring 明写；test L146–163 用源码字符串黑名单 + fixtures/README 锚点双断言 |

### 发现

**R2-01｜建议（P2）——验收② 是用「测试内手写桩链」自证，未连接生产默认降级链**

- `test_mock.py` L78–99 的 `default_chain` 是测试里**自己 new 的三个 `FakeFormalSource`**，断言「这个手写列表里没有 mock」恒为真；L102–143 的 `run_chain` 也是测试内重写的降级循环，**没有调用生产代码 `collect_with_fallback()`**（104 尚未实现，状态 ⏸）。
- 依据：L438 验收② 原文「mock 不出现在默认降级链（无凭证跑默认链 → 结果不含演示数据，I1 / I11）」；P6-a 约束「禁改正式模块」使本任务无法改 104，方赫在红绿记录与 AI 日志补记里已**如实注明**「以测试内桩链隔离验证、未把降级链写进 src，待 602 端到端复验」，不算隐瞒。
- 风险落点：日后若有人把 `MockSource` 挂进真实默认链，这两条用例仍会全绿，验收② 的约束实际没落到生产代码上。
- 建议：602（`tests/test_integration_fallback.py`，现 ⏸）解除后补一条**直接调用 `collect_with_fallback()`** 的用例，断言无凭证且未显式 `--mock` 时结果不含 `mock-` 前缀 `record_id`；在此之前把 601 验收② 记为「条件达成 / 待端到端复验」，**不判不合格、不勾销**。此条与进度维护记录 §四第 10 条一致。

**R2-02｜规范文本待确认（P2，不构成本提交缺陷）——`REPORT_RECIPIENTS` 变量名两处不一致**

- `conftest.py` 的 `cleared_env` 具名清理 `REPORT_RECIPIENTS`，`32c35ca`（401）新增的 `notifiers/members.py` 里 `load_report_recipients()` 读的也是 `REPORT_RECIPIENTS`，**代码侧口径一致**。
- 但 `v2/specs/tasks.md` **L379（401 验收④）写的是 `REPORT_TGAVRGPBGE`**，而 L400（404 验收①）、L542（U6）、design 0.6 3.4 均为 `REPORT_RECIPIENTS`。
- 依据：L438 验收① 要求「清空所有凭证的环境」；若日后按 L379 字面另实现/另配置一个变量，`cleared_env` 会漏清，无凭证前提不再成立。
- 建议：组内确认 L379 是否为规范文本笔误，统一为 `REPORT_RECIPIENTS`；**本人不自行改 `v2/specs/tasks.md`**，确认后走组内 / issue。此条已在进度维护记录 §四第 11 条登记，性质待本人核；**不构成本提交缺陷**。

**R2-03｜提示（P3）——golden 数据只锁了 `record_id`，602–606 对账若用其他字段会漂移**

- `tests/fixtures/mock_work_items.json` 共 10 条、每条 7 字段（`record_id / member / kind / title / detail / occurred_at / source`），但 `test_fixture_record_ids_stable_and_unique` L43 只比对 `[row["record_id"] for row in golden_rows]`，其余 6 字段未与 `load_fixture_items()` 的结果比对。
- 依据：L438 验收③ 写明夹具「供 602–606 对账复用」；对账通常按全字段，若 `_FIXTURE_ROWS` 改了 `title` / `occurred_at` 而 JSON 未同步，本测试仍全绿但对账会错。
- 建议：602–606 的对账用例补一条 `fixture_items` 与 `golden_rows` 的结构化全字段比对（比较时把 `occurred_at` 统一成 ISO 串、`local_day` 单独算）。属后续任务约束，**不构成本提交缺陷**。

- 这次合并前是否执行了 code-review 工作流：☑ 是（人工逐行核对 git diff + 规范原文，见上文「评审方式」）　☐ 否 —— 本人签认 2026-11-24
- 结论：☑ 可合并　☐ 改完再合　评审人：于悦　日期：2026-11-24

---

## 四、评审人声明

我评审的是提交内容与 `v2/specs/tasks.md` 验收标准 / 契约的一致性，依据仓库内真实 diff、远端源码行号与规范原文，命令可复跑、行号可核对；不虚构问题，不把「待实现任务」写成缺陷，不改他人文件、不代签、不倒填、不代勾 checkbox。两条提交均为方赫本周真实代码提交，与组内已有评审对象不重复。

## 五、统计与签认

- 评审 2 条他人提交（方赫 `4fdfdf0` / `29da6dc`），共 **5 条意见**：3 条建议（P2，其中 R2-02 属规范文本待确认）、2 条提示（P3）；**0 条阻断**。
- **签认（2026-11-24）**：工作流执行情况、结论、评审签字与日期已由本人填；第 1 次评审对方 5 条已逐条回应、复检一致，第 2 次评审 R2-02 异议**待本人复检**（对方称 `tasks.md` 无该变量名，本人核实当前 L381 仍有 `REPORT_TGAVRGPBGE`、与 L402/L544 的 `REPORT_RECIPIENTS` 不一致，行号较起草时漂移，性质待定后走组内 / issue，**不自行改 tasks.md、不替对方认错**）。
- 三条后续约束（R1-01 应送达集合独立构造、R1-02 五态判定、R2-01 602 端到端复验）建议由本人在组内会提出，**不自行改 tasks.md、不代改他人代码**。
- 本记录落点 `v2/docs/`（第 3 周及后续周次课程交付文档，按 2026-11-18 组内归位口径）；AI 使用日志另在根 `docs/ai-usage-log.md`，不随迁。
