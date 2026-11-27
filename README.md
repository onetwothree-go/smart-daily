# smart-daily 智能日报生成器

《软件工程职业技能实践》课程仿真企业项目——让日报从成员的真实工作数据里**自动长出来**：定时采集 GitHub 提交、飞书任务、群消息与考勤打卡，生成本人/团队日报，经邮件 + 飞书群机器人推送。解决写日报的五个痛点：下班靠记忆翻找、痕迹散落多平台、忙起来必遗漏、协作成果无人认领、格式不一组长手工汇总。

## 仓库结构

| 目录 | 说明 |
| --- | --- |
| `v1/` | 阶段一工程（SDD 规范驱动），v1.1 已上线：每天 22:00 计划任务自动采集/生成/推送，详见 `v1/README.md` |
| `v2/` | 阶段二工程（Superpowers/TDD 重写，目录级隔离，v1 只读不改），详见 `v2/README.md` |
| `docs/` | 课程过程文档：AI 使用日志、小组角色分工与轮换表等 |
| `scripts/` | 运维脚本（v1 定时任务入口 `run_daily.ps1` 等） |

规范先行：功能以各阶段 `specs/` 目录下的规范（proposal / design / tasks）为唯一事实来源，代码与规范冲突时走规范变更流程。

## 分支与协作

```
main ← 稳定发布分支，只接受合并
  └── dev ← 开发集成分支
        └── feature/<特性名> / fix/<问题名> / docs/<文档名>
```

- 完整规则见 [BRANCHING.md](BRANCHING.md)：受保护分支、PR 流程、提交信息格式（`<类型>: <描述>`）、里程碑标签（`v1-sdd` / `v2-superpowers`）。
- 阶段二以目录隔离（`v2/`），不以长驻分支隔离；v2 不 import v1 的包、不复制 v1 源码（CI 强制校验）。
- AI 参与的产出按 [CLAUDE.md](CLAUDE.md) 约定记入 `docs/ai-usage-log.md`。

## 快速开始

**v1**（`v1/` 目录）：

```bash
uv sync                                  # 安装依赖
cp .env.example .env                     # 配置凭证（不入仓）
uv run smart-daily --mock --day 2026-11-02   # 无凭证演示
```

**v2**（`v2/` 目录）：

```bash
uv sync --dev                            # 安装开发依赖
python -m smart_daily_v2.cli --mock --no-notify --day 2026-11-18   # 无凭证演示
python -m smart_daily_v2.cli --list      # 查看已存日报
```

## 质量门禁

- `pytest` 全量回归（v2 当前 343 passed，含 TDD 红绿证据存档于 `v2/docs/testing/`）；
- `ruff` 双项检查清零；
- CI（`.github/workflows/ci.yml`）按路径过滤，仅在 `v2/**` 或工作流自身变更时触发。
