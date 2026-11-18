# CI 门禁与静态扫描归档

**配置管理员**：赵蕊  
**撰写日期**：2026-11-17  
**文档状态**：第1轮归档（6组数据）

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

| run 链接 | 触发提交（短号+message） | Ruff job 结论 | 测试 job 结论 | 覆盖率数字（若日志可见） | 备注 |
| --- | --- | --- | --- | --- | --- |
| （暂时无链接，需后续补充） | 2bb4650 ci: [TK-V2-001] 新增 CI 门禁 — RED 验证（故意留 ruff F401 告警） | ❌ RED（F401） | ❌ RED（依赖失败） | - | 负向验证：故意留未使用导入 |
| （暂时无链接，需后续补充） | a1af126 test: [TK-V2-101] 身份归并用例（红） | ❌ RED（剧本外） | ❌ RED（预期） | - | RED 剧本内，Ruff 红属剧本外、根因待确认 |
| （暂时无链接，需后续补充） | 6c226b5 feat: [TK-V2-101] 实现身份归并模块 identity.py（绿） | ✅ GREEN | ✅ GREEN | - | GREEN 后双 job 稳定绿 |
| （暂时无链接，需后续补充） | c850d86 feat: [TK-V2-102] 实现 WorkItem 与单次归一化入口 | ✅ GREEN | ✅ GREEN | - | 双 job 稳定绿 |
| （暂时无链接，需后续补充） | 5f20287 docs: [TK-V2-102] 新增第3周测试用例集（101 已执行映射 + 全任务用例设计） | ✅ GREEN | ✅ GREEN | - | 双 job 稳定绿 |
| （暂时无链接，需后续补充） | 9e756bb docs: [TK-V2-102] 补 AI 使用日志记录 | ✅ GREEN | ✅ GREEN | - | 双 job 稳定绿 |

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

## 4. 待补

### 4.1 CI 日志访问问题
- **问题**：GitHub Actions 日志接口返回 403，无 admin 权限无法获取原始输出
- **影响**：无法获取准确的覆盖率数字和详细的错误信息
- **建议**：后续在 ci.yml 中添加 `--cov-report=term` 输出到控制台，便于抓取数据

### 4.2 覆盖率数据采集方法
- **问题**：覆盖率数字目前从 CI 日志直接取数的方法未解决
- **现状**：只能通过覆盖率报告文件（coverage.xml）间接查看
- **建议**：修改 ci.yml 增加 term 输出，但改动需走 TK-V2-702 任务流程，不自行修改

### 4.3 run 链接补全
- **待办**：待获得 CI run 访问权限后，补充完整的 GitHub Actions run 链接
- **格式**：`https://github.com/onetwothree-go/smart-daily/actions/runs/xxxxxx`

---

**统计**：
- 归档了 6 个 run
- 待补：6 条 run 链接，6 条覆盖率数字