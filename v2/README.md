# smart-daily-v2

v2 工程设计备忘（只录结论，不贴代码）。

## 1. 继承的架构决策

- **ADR-101**：httpx 直连，无 ORM/中间层。
- **ADR-102**：sqlite3 + UNIQUE 约束实现幂等写入。
- **ADR-103**：异常驱动降级；采集器自身不重试，由上层 orchestrator 统一降级。
- **ADR-104**：Actions 触发、branches 过滤、`github.actor` 归属、关键词 `19024`、`gen_sign` 单点复用。

## 2. 接口契约要点

- `WorkSource.collect()` 输入参数、输出 `list[WorkItem]`、异常协议见 ADR-103。
- `collect_with_fallback()` 降级语义：源抛 `SourceUnavailableError` → 切下一源；源返回空列表 → 停止降级并返回空结果（空列表 ≠ 失败）；全部源抛异常 → 抛 `AllSourcesUnavailableError`，不返回空列表（C8 / ADR-103）。
- `normalize` 只执行一次，下游禁止二次归一化。
- `local_date` 按东八区（Asia/Shanghai）归属。
- 生成层为纯函数，无副作用。
- `Notifier.send()` 返回 `bool`，不抛异常。
- `Notifier.from_env()` 缺凭证抛 `ValueError`；采集层缺凭证抛 `SourceUnavailableError`。
- **团队日报分发**：群渠道 1 条（`send(subject, body, [])`）+ `REPORT_RECIPIENTS` 非空时 1 封外部邮件；两条通道各自独立 `try`、各自 1 条回执（`scope` 分别为 `team` / `team:report_recipients`）。外部收件人**只**来自 `REPORT_RECIPIENTS`，不复用 `MEMBER_EMAILS` / `resolve_recipients`；未配置时不发、不产生回执，应送达集合退回 `len(groups) + 1`（与 `v1/specs/design.md` 0.6 的 3.3 / 3.4 一致）。

## 3. 数据模型经验

- 单表 `daily_reports`，`UNIQUE(report_date, member)`。
- `INSERT ... ON CONFLICT DO UPDATE` 实现同日重跑覆盖。
- `work_items` 本期只预留表结构，不建业务逻辑。

## 4. v1 三个坑

1. 采集器吞异常返回空列表 → 跳过兜底、产出 0 条空日报（对应 `130ccf7`）。
2. `pushed = any(ok)` 让部分送达被判成功（对应 TK-707，v2 必须用应送达集合 + `all`）。
3. 身份映射大小写敏感，与实时通道的 `.lower()` 不同规（对应 RT-06，v2 统一 `casefold`）。

## 5. 运行方式

安装开发依赖：

```bash
uv sync --dev
```

无凭证演示（使用占位数据，不推送）：

```bash
python -m smart_daily_v2.cli --mock --no-notify --day 2026-11-18
```

查询已保存的日报元数据：

```bash
python -m smart_daily_v2.cli --list
```

进程退出码：

| 退出码 | 含义 |
| --- | --- |
| 0 | 成功 |
| 1 | 采集或落库失败 |
| 2 | 参数错误 |
| 3 | 推送存在失败项 |

真实数据源与数据库路径由环境变量配置；按实际环境设置凭证，不要将凭证提交到仓库：`GITHUB_TOKEN`、`FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_CHAT_ID`、`FEISHU_WEBHOOK_URL`、`EMAIL_*`、`DB_PATH`。

运行口径（☐ 待确认）：CLI 边界的落库接线；`DB_PATH` 默认值；`source_name` 由降级原因拼接；K6 的 6 条送达口径尚未注入。
