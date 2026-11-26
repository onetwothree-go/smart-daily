# v2-superpowers 打 tag 与发布记录 · 第 4 周

**编制人**：杨佳莹（配置管理员 / 测试工程师，第 4 周兼任）
**编制日期**：2026-11-26
**对应任务**：指导书第 4 周配置管理员产出②「v2 版打 tag（v2-superpowers）与发布记录」；总结报告表 B-1「两阶段源码」行与第 6 章改进项的收口
**状态**：☑ 已核验签认（2026-11-26，杨佳莹）——tag 已打并推送远端，发布数据为本机同日实测

## §1 tag 信息

| 项 | 内容 |
| --- | --- |
| tag 名 | `v2-superpowers` |
| 类型 | 附注标签（annotated） |
| 指向提交 | `d5715d7`（Revert "docs: [S11乙案]…"，当前 HEAD） |
| 打标日期 | 2026-11-26 |
| 推送 | `git push origin v2-superpowers` 已完成，远端可见 |
| tag 说明 | v2-Superpowers 阶段交付：飞书考勤采集变更涟漪闭环，全量回归 332 passed / 覆盖率 93.26%（2026-11-26 实测），ruff check/format 全绿（124 files），零复制 0 命中，CI 门禁通过 |

## §2 与 v1 的对照

| 阶段 | tag | 说明 |
| --- | --- | --- |
| 阶段一（SDD 流程） | `v1-sdd`、`v1-sdd-rc1` | 第 1–2 周产出，已有 |
| 阶段二（Superpowers 流程） | `v2-superpowers` | 本次补打 |

两阶段现在都有明确的版本标记，总结报告第 3 章的两阶段对比（缺陷闭环率、覆盖率、规范扫描）可以按 tag 逐一对账。

## §3 发布时验证数据（2026-11-26 本机实测）

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 全量回归与覆盖率 | `uv run pytest -q --cov=smart_daily_v2 --cov-fail-under=80` | **332 passed in 16.14s**，覆盖率 **93.26%**（1142 语句 / 77 未覆盖），80% 门限通过 |
| 规范扫描 | `uv run ruff check .` | All checks passed! |
| 格式检查 | `uv run ruff format --check .` | 124 files already formatted |
| 零复制红线 | `grep -rnE "^from smart_daily import\|^import smart_daily$" v2/src v2/tests` | 0 命中 |

## §4 复现命令

```bash
cd D:/pro/smart-daily
git tag -l                     # 应看到 v1-sdd / v1-sdd-rc1 / v2-superpowers
git show v2-superpowers        # 查看 tag 说明与指向的提交 d5715d7
cd v2
uv run pytest -q --cov=smart_daily_v2 --cov-fail-under=80
uv run ruff check . && uv run ruff format --check .
```

## §5 边界

- tag 打在 `d5715d7`，即打标时点仓库的最终提交；此后仓库若有新提交，tag 不随之移动。
- 本次发布未改任何源码 / specs / tests / 他人文档，只新增 tag 与本记录文件。
- GitHub Releases 页面未另建 release，课程以仓库 tag 为准；如老师要求 Release 页面再补。
