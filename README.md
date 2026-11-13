# 智能日报生成器（Smart Daily Report Generator）

> 《软件工程职业技能实践》课程仿真企业项目 · 阶段一（SDD 规范驱动）
> 规格先行：本项目所有功能以 `specs/` 目录下的规范为唯一事实来源，代码与规范冲突时走规范变更流程。

## 它解决什么问题

写日报的五个痛点：下班靠记忆翻找、痕迹散落多平台、忙起来必遗漏、协作成果无人认领、格式不一组长手工汇总。
本系统让日报从成员的真实工作数据里**自动长出来**。

## 系统架构（四层）

```
┌─────────────────────────────────────────────┐
│ 主编排入口  cli.py / orchestrator.py          │  降级链调度 + 个人/团队日报分发
├─────────────────────────────────────────────┤
│ 推送层      push/notifiers.py                │  邮件 + 飞书群机器人（支持签名校验）
├─────────────────────────────────────────────┤
│ 生成层      push/generator.py                │  WorkItem → 日报条目 → 团队日报
├─────────────────────────────────────────────┤
│ 采集层      collectors/                      │  GitHub / 飞书 / local-git / mock
└─────────────────────────────────────────────┘
```

## 快速开始

```bash
# 1. 安装依赖（uv）
uv sync

# 2. 配置环境变量（严禁写入代码或提交仓库）
cp .env.example .env
# 编辑 .env，填入 GitHub PAT、飞书凭证、SMTP 授权码

# 3. 无凭证演示（mock 数据源）
uv run smart-daily --mock --day 2026-11-02

# 4. 真实采集（默认降级链 GitHub → 飞书 → local-git）
uv run smart-daily --day 2026-11-02

# 5. 只生成不推送
uv run smart-daily --no-notify

# 6. 查看已有日报
uv run smart-daily --list
```

## 环境变量清单

| 变量 | 用途 | 必需 |
| --- | --- | --- |
| `GITHUB_TOKEN` | GitHub 个人访问令牌（仅只读权限） | GitHub 采集时 |
| `GITHUB_REPO_OWNER` / `GITHUB_REPO_NAME` | 小组仓库标识 | GitHub 采集时 |
| `FEISHU_APP_ID` / `FEISHU_APP_SECRET` | 飞书自建应用凭证 | 飞书采集时 |
| `FEISHU_CHAT_ID` | 飞书群标识 | 飞书采集时 |
| `FEISHU_WEBHOOK_URL` | 群自定义机器人 Webhook | 飞书推送时 |
| `FEISHU_WEBHOOK_SECRET` | 机器人签名密钥 | 可选，开启签名校验时 |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` | 邮件通道 | 邮件推送时 |
| `REPORT_RECIPIENTS` / `MEMBER_EMAILS` | 团队收件人 / 成员邮箱映射 | 邮件推送时 |
| `DAILY_CUTOFF` | 日报统计截止时间 | 可选 |
| `DB_PATH` | SQLite 路径 | 可选 |

完整说明见 [.env.example](.env.example)。**凭证一律走环境变量，严禁写入代码或提交到仓库。**

## 验证脚本

| 脚本 | 用途 |
| --- | --- |
| `scripts/verify_collectors.py` | 采集层回归（39 项断言） |
| `scripts/check_feishu.py` | 飞书凭证与开放平台连通性 |
| `scripts/check_webhook.py` | 飞书 Webhook 推送实测 |
| `scripts/verify_security.py` | 签名与关键词安全设置反向探测 |
| `scripts/check_email.py` | SMTP 通道实测 |
| `scripts/check_github_net.py` | GitHub 网络分层诊断 |

## 文档

| 文档 | 内容 |
| --- | --- |
| [specs/proposal.md](specs/proposal.md) | 需求规范（范围 / 不做什么 / 可度量成功标准） |
| [docs/ai-usage-log.md](docs/ai-usage-log.md) | AI 使用日志（每周日晚提交） |
| [docs/采集层交接说明.md](docs/采集层交接说明.md) | 采集层接口契约与降级链 |
| [docs/飞书配置指引.md](docs/飞书配置指引.md) | 飞书开放平台与机器人配置 |
| [docs/GitHub访问诊断报告.md](docs/GitHub访问诊断报告.md) | GitHub 网络问题根因与解法 |
| [docs/Clash使用指引.md](docs/Clash使用指引.md) | 代理工具使用 |

## 当前进度

- [x] 采集层：GitHub / 飞书 / local-git / mock 四源 + 统一降级链
- [x] 生成层：个人日报 + 团队日报 + 本地时区归属
- [x] 推送层：邮件 + 飞书群机器人（签名校验）
- [x] 主编排：CLI + SQLite 幂等存储
- [x] 三份规范：`proposal.md` 0.4.2、`design.md` 0.5.1、`tasks.md` 0.1.4（含变更记录与 §12 覆盖矩阵）
- [x] 验收单测 28 条（`tests/test_acceptance_pure.py` / `test_acceptance_runtime.py`，2026-11-12 本机实跑 `Ran 28 tests / OK`）；第 1 / 2 周用例执行记录见 `docs/testing/`
- [ ] v1.1 考勤数据采集（**第 4 周变更涟漪演练**，不属阶段一 v1 验收范围，保留为后续周待办）
- [x] v1.1（已落地）：`scripts/run_daily.ps1` + 本机计划任务 `SmartDaily-2200`（`3f2b3ee`）把 22:00 改为自动触发；按需求方 2026-11-10 口径，**项目当前为 v1.1，该自动定时属 N8 计划列兑现、非范围变更**。`specs/proposal.md` 0.4.2 的 S7 / N8 / I4 正文与 `docs/杨佳莹-需求澄清问答记录.md` 的 Q1–Q21 作为 v1 基线原文保留，现行口径见 `proposal.md` 变更记录「2026-11-13 0.4.2 补记 8（不升版）」及 `docs/方赫-N8范围冲突处置记录.md` 第五节

> 2026-11-12 22:48 按仓库实际状态更新本节：三份规范与 28 条验收单测均已落地，原两处 `[ ] 待写` 据实勾讫；v1.1 考勤一项注明属第 4 周演练范围，避免被误读为本期缺口。
