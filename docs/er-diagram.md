# ER 图 —— daily_reports 表结构

> 与 `specs/design.md` §2.3 SQLite 表结构一致。  
> `work_items` 表为【本期约定】预留，默认不建；用虚线边框标注。

## Mermaid ERD

```mermaid
erDiagram
    daily_reports ||--o{ work_items : contains

    daily_reports {
        INTEGER id PK "自增主键"
        TEXT report_date UK "日期 YYYY-MM-DD"
        TEXT member UK "成员显示名"
        TEXT content "日报全文 Markdown"
        INTEGER item_count "条目数 DEFAULT 0"
        TEXT source_name "生效数据源名 可空"
        TEXT created_at "写入时间 UTC ISO格式"
    }

    work_items {
        TEXT report_date PK_FK "日期 关联daily_reports"
        TEXT member FK "成员"
        TEXT record_id PK "源平台唯一ID"
        TEXT source "来源类型"
        TEXT title "条目标题"
        TEXT timestamp "事件时间"
    }
```

## 说明

| 表 | 状态 | 幂等键 | 说明 |
|---|---|---|---|
| `daily_reports` | ✅ 已实现 | `UNIQUE(report_date, member)` + `ON CONFLICT DO UPDATE` | 同日同人重复执行覆盖而非追加 |
| `work_items` | 📋 本期约定 (默认不建) | `PRIMARY KEY(report_date, record_id)` | 条目级对账用；是否引入取决于对账测试粒度 |

**关系**：`daily_reports` 1 ⟶ * `work_items`，通过 `(report_date, member)` 做逻辑外键（SQLite 无强制外键约束，由应用层保证一致性）。

**幂等策略**：日报级用 `INSERT ... ON CONFLICT DO UPDATE`；条目级（若建表）用联合主键天然幂等。