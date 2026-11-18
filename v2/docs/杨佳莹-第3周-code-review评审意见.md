# 第 3 周 Code Review 评审意见

**评审人**：杨佳莹（架构师）
**评审日期**：2026-11-18
**评审范围**：dev 分支他人真实提交 2 条；只评提交内容与 `specs/` 契约的一致性，不代签、不改他人文件

---

## 评审 1

**提交号**：`fcd1569`
**作者**：方赫
**提交时间**：2026-11-17 21:54:37
**提交内容**：`feat: [TK-V2-103] 实现采集协议与异常契约（红绿循环）`
**对应任务**：`v2/specs/tasks.md` TK-V2-103（`sources/base.py` + `tests/test_worksource.py`）

### 评审方式（可复跑）

1. `git show fcd1569 --stat` → 4 文件：`docs/dev/方赫-第3周.md`、`v1/docs/ai-usage-log.md`、`sources/base.py`、`tests/test_worksource.py`；代码改动只在 `v2/`，符合目录隔离。
2. `git show fcd1569 -- v2/src/smart_daily_v2/sources/base.py` → 逐行核对 Protocol 签名、异常类继承、错误串拼装。
3. 对照 `v2/specs/tasks.md` TK-V2-103 验收①②③④ 与 issue #14 的 K5 / K8 修订文本。
4. 对照 `v1/specs/design.md` 3.5 采集层契约「异常驱动降级」与 `v2/README.md` §2「全部源抛异常 → 抛 `AllSourcesUnavailableError`」。

### 发现

**建议（P2）——协议符合性测试没有校验返回类型契约**

- `tests/test_worksource.py::test_three_sources_satisfy_protocol` 用 `isinstance(source, WorkSource)` 判定，三个假源的 `collect()` 返回标注都是 `list[object]`。
- `@runtime_checkable` Protocol 的 `isinstance` 只检查成员存在性与可调用性，不检查返回注解；TK-V2-103 契约写明 `collect(...) -> list[WorkItem]`，但本条验收①无法拦住返回 `list[dict]` 或 `list[object]` 的实现。
- 风险落点：`TK-V2-104` 的 `fallback.py` 要在合并后统一调用一次 `normalize()`；若上游返回的不是 `WorkItem` 而是未归一化对象，单点归一化的边界会被绕过（G7）。
- 建议：补一条用例断言 `collect` 的返回标注为 `list[WorkItem]`（例如 `typing.get_type_hints`），或让假源返回真实 `WorkItem` 并断言元素类型，别只靠 `isinstance`。

**提示（P3）——K8 继承关系要求降级链显式区分捕获顺序**

- `AllSourcesUnavailableError(SourceUnavailableError)` 符合 K8 方案甲，`except SourceUnavailableError` 能兜住全失败异常（验收④已用测试锁定，正确）。
- 但同一继承关系带来一个下游约束：`TK-V2-104` 的降级循环若写成 `except SourceUnavailableError: continue`，会把「全源失败」误当「单源失败」继续遍历，最终不抛 `AllSourcesUnavailableError`，重演 v1 坑 1。
- 建议：在 104 的实现约束里写死捕获顺序——先 `except AllSourcesUnavailableError: raise`，再 `except SourceUnavailableError: 记原因、切下一源`；并在 `test_fallback.py` 加一条"全失败不被吞"的用例。此项属后续任务约束，不构成本提交缺陷。

### 结论

**通过**。4 条验收全部有对应用例，K5 keyword-only、K8 继承、无平台专有字段三点属实；留 1 条 P2 建议 + 1 条 P3 提示，不阻断 104 开工（P3 需在 104 实现前落进任务约束）。

---

## 评审 2

**提交号**：`c850d86`
**作者**：赵蕊
**提交时间**：2026-11-17 17:37:21
**提交内容**：`feat: [TK-V2-102] 实现 WorkItem 与单次归一化入口`
**对应任务**：`v2/specs/tasks.md` TK-V2-102（`models.py`）

### 评审方式（可复跑）

1. `git show c850d86 --stat` → 只改 `v1/docs/ai-usage-log.md` 与 `v2/src/smart_daily_v2/models.py`，精确 `add`、未碰 v1 代码。
2. `git show c850d86 -- v2/src/smart_daily_v2/models.py` → 逐行核对 `WorkItem` 字段、三种源记录、`local_date()`、`normalize()`。
3. 对照 `v2/specs/tasks.md` TK-V2-102 验收①–④、归一化单点（K4 方案甲）与 G7 幂等约定。
4. 对照 `v1/specs/design.md` 2.2 归属日语义、2.3 数据模型与 `v2/README.md` §3。

### 发现

**建议（P2）——类型校验用 `isinstance`、类型映射用精确 `type`，两者不一致**

- `normalize()` 先做 `isinstance(entry, (WorkItem, CommitEntry, TaskEntry, MessageEntry))` 校验，随后用 `_SOURCE_BY_TYPE[type(entry)]` 取映射。
- 传入 `CommitEntry` 的子类实例时：校验通过（子类也是实例），映射却以子类对象作精确键查表 → `KeyError`，不是契约里约定的 `TypeError`。
- 建议：校验改精确类型（`if type(entry) not in _ALLOWED_TYPES: raise TypeError(...)`），或映射改按 `isinstance` 逐类匹配；两处用同一套判定口径。

**建议（P2）——G7 幂等只在「全 `WorkItem`」输入下成立，混合输入边界未写明**

- 全 `WorkItem` 输入原样放行、不重排（符合验收②）；但只要混入一条 `CommitEntry`，整表就会按 `occurred_at` 倒序重排，先前已归一化的 `WorkItem` 相对顺序也会变。
- 这不违反 K4（104 仍是一次归一化），但「下游禁止二次归一化」的边界应在接口上写清：哪些调用算合法。
- 建议：在 `normalize()` docstring 与 tasks 102 补一句——混合输入的排序覆盖全部条目；下游若已持有 `WorkItem`，不得再调用本函数。或补一条混合输入的顺序断言用例，把行为固化。

### 结论

**通过**。8 个字段与 tasks 逐字一致，三种源记录齐全，未知类型抛 `TypeError`、`WorkItem` 原样放行、R4 东八区归属三条硬约束都有测试覆盖；留 2 条 P2 建议，不阻断 103 开工。

---

## 评审人声明

我评审的是提交内容与规范契约的一致性，不代签、不改他人文件、不替代作者本人的确认状态。所有意见基于仓库内实际提交 diff 与 `specs/` 原文，命令可复跑、行号可核对；不虚构问题，也不把「待实现任务」写成缺陷。

---

**统计**：评审 2 条他人提交（方赫 1 条 / 赵蕊 1 条）；结论 2 条通过；共 3 条建议（P2）、1 条提示（P3），0 条阻断。
