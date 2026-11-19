# CI 门禁与静态扫描归档

**配置管理员**：赵蕊  
**撰写日期**：2026-11-17（第 1 轮）｜**2026-11-19 21:29 第 2 轮复跑归档**｜**2026-11-19 21:37 ruff 阻断项修复**  
**文档状态**：第 2 轮归档（补本机复跑证据 + 覆盖率门槛说明 + ruff 阻断项）＋ 阻断项已修复、已推送，CI run 44535812635 转绿（§5.3、§2.1）

## 1. 门禁规则摘要

### 1.1 触发条件
CI 门禁在以下情况触发（`.github/workflows/ci.yml`）：
- **触发事件**：
  - `push` 到 `dev` 分支，且路径满足以下任一条件：
    - `v2/**`（v2 工程文件变更）
    - `.github/workflows/ci.yml`（CI 配置变更）
  - `pull_request`（PR 触发）
- **工作目录**：`v2/`
- **路径过滤**：避免 v1 的文档/代码提交白白跑 CI

### 1.2 Job 配置

#### Ruff 静态扫描（lint job）
- **检查内容**：
  - `uv run ruff check .`：规则检查（E/F/I/B）
  - `uv run ruff format --check .`：格式检查
- **退出要求**：两项都必须通过（退出码 0）

#### 测试 + 覆盖率（test job）
- **检查内容**：
  - `uv run pytest -q`：运行所有测试
  - `--cov=smart_daily_v2`：覆盖率检查
  - `--cov-report=term-missing`：显示未覆盖行
  - `--cov-report=xml`：生成 XML 报告
  - `--cov-fail-under=80`：覆盖率门槛 80%
- **退出要求**：测试通过 + 覆盖率 ≥ 80%

### 1.3 门禁逻辑
- 双 job 均通过 → CI 成功（GREEN）
- 任一 job 失败 → CI 失败（RED）
- 覆盖率报告会归档为 artifact

## 2. 归档表

> **本机复跑结论列口径**：历史 6 条 run 未逐条 checkout 复跑（避免污染工作区），该列填 `-`；
> 当前 HEAD 的复跑结论见 §5。run 链接已于 2026-11-19 21:35 经 GitHub Actions API 按 sha 核对回填，核对过程与三处更正见 §2.1。

| run 链接 | 触发提交（短号+message） | Ruff job 结论 | 测试 job 结论 | 覆盖率 | 本机复跑结论 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| [run 43797123659](https://github.com/onetwothree-go/smart-daily/actions/runs/43797123659) | 2bb4650 ci: [TK-V2-001] 新增 CI 门禁 — RED 验证（故意留 ruff F401 告警） | ❌ RED（F401） | ❌ RED（依赖失败） | - | - | 2026-11-16 03:15；负向验证：故意留未使用导入 |
| [run 43843812521](https://github.com/onetwothree-go/smart-daily/actions/runs/43843812521) | a1af126 test: [TK-V2-101] 身份归并用例（红） | ❌ RED（剧本外） | ❌ RED（预期） | - | - | 2026-11-16 09:53；RED 剧本内，Ruff 红属剧本外、根因待确认 |
| **无 run** | 6c226b5 feat: [TK-V2-101] 实现身份归并模块 identity.py（绿） | — | — | - | - | **未查到以该 sha 为 head 的 CI run**，见 §2.1 |
| [run 44057265412](https://github.com/onetwothree-go/smart-daily/actions/runs/44057265412) | c850d86 feat: [TK-V2-102] 实现 WorkItem 与单次归一化入口 | ✅ GREEN | ✅ GREEN | - | - | 2026-11-17 09:37；双 job 稳定绿 |
| **未触发** | 5f20287 docs: [TK-V2-102] 新增第3周测试用例集（101 已执行映射 + 全任务用例设计） | — | — | - | - | **路径过滤未命中**：改动文件在根 `docs/`，不在 `v2/**`，见 §2.1 |
| **未触发** | 9e756bb docs: [TK-V2-102] 补 AI 使用日志记录 | — | — | - | - | **路径过滤未命中**：改 `docs/ai-usage-log.md`，见 §2.1 |

### 2.1 run 链接核对结论（2026-11-19 21:35，经 GitHub Actions API 按 sha 精确查询）

原表 6 行填「（暂时无链接，需后续补充）」，本次按提交逐一核对，结论分三类：

| 提交 | 核对结果 | 依据 |
| --- | --- | --- |
| `2bb4650` | ✅ 已回填 run 43797123659，conclusion=failure | API `actions/runs?head_sha=` 命中 |
| `a1af126` | ✅ 已回填 run 43843812521，conclusion=failure | 同上 |
| `c850d86` | ✅ 已回填 run 44057265412，conclusion=success | 同上 |
| `6c226b5` | ⚠️ **无 CI 门禁 run** | 该 sha 无任何 workflow run；同日前后最近 run 为 11-16 13:55（`96fa4aa`），19:51 推送未产生 CI run |
| `5f20287` | ⚠️ **未触发**（路径过滤） | 提交内容为 `docs/赵蕊-测试用例集-第3周.md`，落在**根 `docs/`**，不命中 `v2/**`；文档已于 `976714c` 迁至 `v2/docs/` |
| `9e756bb` | ⚠️ **未触发**（路径过滤） | 提交内容为 `docs/ai-usage-log.md`，同上不在 `v2/**` |

**必须更正的三处原记录**：原表把 `6c226b5`、`5f20287`、`9e756bb` 三行记为「✅ GREEN / ✅ GREEN」，但这三条**当时没有对应的 CI run**，没有可核验的 job 结论。原记录属推定而非实测，按 G5（不补造）更正为「无 run」/「未触发」。若需为这三笔提交补一条绿证据，只能在当前 HEAD 上重跑并另行标注为「补跑」，不得回填为当时结论。

**当前 HEAD 状态（2026-11-19 21:02–21:31）**：

| 提交 | CI 结论 | run 链接 |
| --- | --- | --- |
| `5a323cf` docs: [TK-V2-607] 补充 AI 使用日志条目 | ❌ failure | [run 44529479604](https://github.com/onetwothree-go/smart-daily/actions/runs/44529479604) |
| `c917978` docs: [TK-V2-701] 归档零复制与密钥红线自查 | ❌ failure | [run 44534255554](https://github.com/onetwothree-go/smart-daily/actions/runs/44534255554) |
| `6ac60fd` docs: [方赫] 补 TK-V2-104 红绿循环记录 | ✅ success | [run 44505355884](https://github.com/onetwothree-go/smart-daily/actions/runs/44505355884) |
| **`f3140b1`** docs: [TK-V2-702] 归档静态扫描与 CI 门禁结果（含 `9e2b97e` ruff 修复） | ✅ **success** | [run 44535812635](https://github.com/onetwothree-go/smart-daily/actions/runs/44535812635) |
| `cfc4b74` docs: [TK-V2-702] 补记 CI 转绿 run 与 job 级核对 | ✅ success | [run 44536033486](https://github.com/onetwothree-go/smart-daily/actions/runs/44536033486) |

两连红均源于 `6081e82` 引入的 ruff 错误，详见 §5.2。该缺陷已由 `9e2b97e` 修复，**`f3140b1` 的 run 44535812635 起 CI 转绿，两连红状态结束**。

**转绿 run 的 job 级核对**（2026-11-19 21:40，非跳过、非缓存命中）：

| Job | 状态 | 关键步骤结论 |
| --- | --- | --- |
| Ruff 静态扫描 | ✅ success | Ruff 规则检查 ✅ / Ruff 格式检查 ✅ |
| 测试 + 覆盖率 | ✅ success | 安装依赖（含 dev）✅ / 运行测试并采集覆盖率 ✅ / 归档覆盖率报告 ✅ |

两 job 均 `completed`，所有 step 均为 `success`，无 `skipped`。run 与 job 级原始字段归档于 `v2/docs/testing/证据/ci-run-20261119.txt`（含 `f3140b1` / `cfc4b74` 两次 run；日志正文接口 403 无 admin 权限，故归档 API 原始字段，不代写结论）。

## 3. 负向验证记录

### TK-V2-002 验收标准④验证
**任务**：TK-V2-002 · 目录隔离方案 + CI / 分支规范同步  
**验收标准④**：故意留一条 F401 → CI 判红  
**提交**：2bb4650  
**验证结果**：✅ 通过

**验证过程**：
1. 故意在 `v2/src/smart_daily_v2/__init__.py` 留下 `import os` 未使用
2. CI 运行时 Ruff 检测到 F401（`unused import`）
3. Ruff job 失败，CI 整体判 RED
4. 符合验收标准：CI 能正确识别代码质量问题

**注意**：此为故意为之的负向验证，实际开发中应避免此类问题。

**2026-11-19 复核**：负向验证结论仍有效，ci.yml 的 lint job 未改动（Ruff 两个 step 在第 34–37 行，`ruff check` 第 35 行、`ruff format --check` 第 37 行）。

## 4. 覆盖率门槛说明

- **现行门槛**：`--cov-fail-under=80`，写在 `.github/workflows/ci.yml` 第 61 行（test job 的 pytest 命令内）。
- **实测值**：2026-11-19 21:29 本机复跑 **TOTAL 97%**（Stmts 287 / Miss 9），高于门槛 17 个百分点。
- **门槛来源**：该 80% 为**组内自定**值，**不是教师公布阈值**。指导书未规定具体覆盖率数字，只要求提供覆盖率数据并与阈值对比。
- **若教师公布更高阈值**：须重跑 `pytest --cov` 并如实记录新差距，**不得为了对上阈值补写无意义用例**；补测须走正常红绿流程并单独记录。
- **口径提醒**：本机 Python 3.14.2（`.venv`），CI 为 3.13。两处版本差异可能造成个别分支覆盖不同，判定时以同批次命令输出为准，不跨版本拼数据。

## 5. 本机复跑结论与 ruff 阻断项（2026-11-19 21:29 首轮 → 21:37 修复后复跑）

### 5.1 复跑结论

| 检查项 | 命令 | 退出码 | 结论 |
| --- | --- | --- | --- |
| 测试 + 覆盖率 | `pytest -q --cov=smart_daily_v2 --cov-report=term-missing` | 0 | ✅ **GREEN**，126 passed，TOTAL 97% |
| Ruff 规则检查 | `ruff check .` | **0** | ✅ **GREEN**，All checks passed!（修复前为 exit 1 / 6 errors，见 §5.2） |
| Ruff 格式检查 | `ruff format --check .` | **0** | ✅ **GREEN**，53 files already formatted（修复前为 exit 1 / 2 files would be reformatted） |

> 上表为 **2026-11-19 21:37 修复后复跑**结果，TK-V2-702 验收标准①（两项退出码均为 0）**已满足**。
> 修复前的红灯原始输出已随证据文件一并保留在下述「首轮证据」中，未做删除。

原始输出见 `v2/docs/testing/证据/`（修复后复跑 4 份 + 修复前 2 份 + CI run 1 份）：
- 修复后：`pytest-cov-20261119.txt`、`ruff-check-20261119.txt`、`ruff-format-check-20261119.txt`、`env-20261119.txt`
- 修复前：`ruff-check-20261119-before-fix.txt`（101 行，exit=1）、`ruff-format-check-20261119-before-fix.txt`（87 行，exit=1）——由 `git worktree` 从 `c917978` 原样检出修复前代码复现，保证红灯原始输出可追溯
- CI run：`ci-run-20261119.txt`（73 行，run 元数据 + job/step 结论，来自 GitHub REST API）

**首轮证据（21:29，红灯状态）**：`ruff check` exit=1（Found 6 errors / 4 fixable）、`ruff format --check` exit=1（2 files would be reformatted）、`pytest` exit=0（126 passed / 97%）。该状态已由 §5.3 的修复消除，数字与明细见 §5.2。

### 5.2 阻断项明细

**引入提交**：`6081e82 feat: [TK-V2-607] 提升测试覆盖率从 91% 到 97%`（已推送到 `origin/dev`）

该提交新增两个测试文件，把覆盖率从 91% 提到 97%，但同时带进 6 个 ruff 错误与 2 处格式问题：

| 文件 | 规则 | 位置 | 说明 |
| --- | --- | --- | --- |
| `tests/test_coverage_improvement.py` | I001 | 3:1 | import 块未排序 |
| `tests/test_coverage_improvement.py` | F401 | 6:35 | `load_config` 导入未使用 |
| `tests/test_coverage_improvement.py` | B011 | 15:20 | 用 `assert False` 而非 `raise AssertionError` |
| `tests/test_dispatch_real_calls.py` | I001 | 3:1 | import 块未排序 |
| `tests/test_dispatch_real_calls.py` | F401 | 6:46 | `load_member_emails` 导入未使用 |
| `tests/test_dispatch_real_calls.py` | E501 | 21:99 | 单行 102 字符，超 100 |

格式检查另有 2 个文件需重排（同上两个文件，含单引号改双引号、尾逗号、长行折行）。

**影响**：按 §1.2，lint job 要求两项退出码均为 0。修复前该状态推送到 `dev` 会使 CI 判 RED，TK-V2-702 验收标准①（`ruff check` / `ruff format --check` 退出码 0）**不满足**。**该条为阻断期原始记录，2026-11-19 21:37 已修复，见 §5.3；修复后两项退出码均回归 0，验收标准①已满足。**

**CI 侧已实证**：该缺陷推上 `dev` 后连续两次 run 判 failure ——
`5a323cf`（含 `6081e82`）→ [run 44529479604](https://github.com/onetwothree-go/smart-daily/actions/runs/44529479604) failure；
`c917978` → [run 44534255554](https://github.com/onetwothree-go/smart-daily/actions/runs/44534255554) failure。
本机复跑与 CI 结论一致，可确认红因是 lint job 而非测试 job（本机 pytest 为 GREEN）。

**处置结果（2026-11-19 21:37 已执行，§5.3 记明细）**：6 个错误与 2 处格式问题全部消除，`ruff check` 与 `ruff format --check` 退出码均回归 0，`pytest` 仍为 126 passed / TOTAL 97%（无回归）。原拟五步中，第 1–2 步改为手工精确修改（改动面更小、可逐条对应规则），第 3–5 步按原计划执行。

**附带问题（另案登记，不在 702 范围）**：`6081e82` 同时把 `v2/coverage.xml`（372 行）提交入库。该文件是 pytest-cov 生成的产物，属 CI artifact，通常应进 `.gitignore`。是否移除由组内定，本次不动。

### 5.3 阻断项修复记录（2026-11-19 21:37）

**责任归属**：`6081e82` 的提交作者为赵蕊（zhaorui715），两个测试文件由本人编写，ruff 问题由本人引入并修复。同时按角色，测试代码归测试工程师、CI 门禁红灯归配置管理员，两项均在本岗范围内。

**改动明细（全部为等价变换，未改动任何断言语义）**：

| 文件 | 规则 | 修复方式 |
| --- | --- | --- |
| `tests/test_coverage_improvement.py` | I001 | import 排序：`normalize, WorkItem, CommitEntry` → `CommitEntry, WorkItem, normalize` |
| `tests/test_coverage_improvement.py` | F401 | 删除未使用的 `load_config` 导入 |
| `tests/test_coverage_improvement.py` | B011 | `try/except + assert False, "…"` → `with pytest.raises(ValueError, match="Missing required credential")`，断言目标与消息匹配条件与原 `except` 分支完全一致 |
| `tests/test_dispatch_real_calls.py` | I001 | `patch, MagicMock` → `MagicMock, patch` |
| `tests/test_dispatch_real_calls.py` | F401 | 删除未使用的 `load_member_emails` 导入 |
| `tests/test_dispatch_real_calls.py` | E501 | 长行折行为 `assert_called_once_with(\n … \n)`，实参不变 |
| 上述两文件 | 格式 | `ruff format .` 重排（2 files reformatted，51 unchanged） |

**修复后验证（同一工作区、同一命令）**：

| 检查项 | 修复前 | 修复后 |
| --- | --- | --- |
| `ruff check .` | exit **1**，Found 6 errors | exit **0**，All checks passed! |
| `ruff format --check .` | exit **1**，2 files would be reformatted | exit **0**，53 files already formatted |
| `pytest --cov` | exit 0，126 passed / 97% | exit 0，**126 passed / 97%（无回归）** |

**证据同步**：`v2/docs/testing/证据/` 内三份文件已按修复后输出重新生成（第二行标注「ruff 修复后复跑」）；修复前的完整红灯输出（101 行 / 87 行，均 exit=1）另存为 `*-before-fix.txt`，用 `git worktree` 从 `c917978` 复现，未被覆盖。

**已闭环**：修复已提交并推送 —— `9e2b97e style: [TK-V2-607] 修正新增测试的 ruff 告警`、`f3140b1 docs: [TK-V2-702] 归档静态扫描与 CI 门禁结果`。推送后 CI run [44535812635](https://github.com/onetwothree-go/smart-daily/actions/runs/44535812635) 结论 **success**，两个 job 全绿，CI 两连红结束。

## 6. 待补事项（原 §4 顺延，编号变更说明：原「§4 待补」因新增覆盖率门槛说明顺延为 §6）

### 6.1 CI 日志访问问题
- **问题**：GitHub Actions 日志接口返回 403，无 admin 权限无法获取原始输出
- **影响**：无法获取准确的覆盖率数字和详细的错误信息
- **建议**：后续在 ci.yml 中添加 `--cov-report=term` 输出到控制台，便于抓取数据
- **2026-11-19 补充**：`ci.yml` 第 57–61 行已含 `--cov-report=term-missing`（第 59 行），控制台会打印模块级数字；本机复跑已按同一命令取得 97%，可作为 CI 数字的对照口径

### 6.2 覆盖率数据采集方法
- **问题**：覆盖率数字目前从 CI 日志直接取数的方法未解决
- **现状**：本机复跑可直接取数（`pytest-cov-20261119.txt`），CI 侧仍需日志权限
- **建议**：CI 数字以 artifact `coverage-report`（coverage.xml）为准，本机数字作对照，两者不一致时以 CI 为准并在文档注明差异

### 6.3 run 链接补全
- **已完成**：`2bb4650` / `a1af126` / `c850d86` 三条已回填真实 run 链接（见 §2、§2.1）
- **无需补**：`5f20287` / `9e756bb` 当时落在根 `docs/`，不命中 `v2/**`，本就没有 run，补链接反而失真
- **待定**：`6c226b5` 未查到 run。若需为这笔提交留绿证据，只能在当前 HEAD 补跑并标注「补跑」，不得回填为 11-16 当时的结论

---

**统计**：
- 归档历史 run：6 个（3 条已回填真实链接 / 3 条经核对确认无 run 或未触发，见 §2.1）
- 已补：本机复跑证据 4 份（测试/覆盖率、ruff 规则、ruff 格式、环境版本）
- 已补：当前 HEAD 两连红的 run 链接 2 条（§5.2）
- 历史覆盖率数字：6 条均为 `-`（日志接口 403，无权限取数，不推测）
- 已闭环：ruff 两项检查原 RED（§5.2），2026-11-19 21:37 修复为 exit 0，证据文件已重新生成（§5.3）
- 已闭环：修复提交 `9e2b97e` + `f3140b1` 已落库推送，CI run 44535812635 结论 success（§2.1）
