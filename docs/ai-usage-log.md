# AI 使用日志 · 智能日报生成器

> 记录每次借助 AI 实际完成的工作。

---

| 日期 | 工具 | 提交人 | 做了什么 |
| --- | --- | --- | --- |
| 2026-11-02 | Claude Code | 杨佳莹 | 生成第0周环境安装清单、第一周行动手册，整理指导书要点 → output/环境安装清单-智能日报课程.md、output/第一周行动手册-智能日报生成器.md |
| 2026-11-02 | Claude Code | 杨佳莹 | 搭建智能日报工程骨架（采集/生成/推送/主编排四层架构）→ src/smart_daily/ |
| 2026-11-02 | Claude Code | 杨佳莹 | 设计 WorkSource 协议与 RawRecord 联合类型，重构 CommitSource → src/smart_daily/collectors/base.py、models.py |
| 2026-11-03 | Claude Code | 杨佳莹 | 实现飞书自定义机器人 Webhook 签名校验（HMAC-SHA256）→ src/smart_daily/push/notifiers.py |
| 2026-11-03 | Claude Code | 杨佳莹 | 修复降级链空列表陷阱：源全不可用时抛异常而非返回空列表 → src/smart_daily/orchestrator.py |
| 2026-11-03 | Claude Code | 杨佳莹 | 新增 local_date()，修复 UTC .date() 导致东八区日报差一天 → src/smart_daily/collectors/models.py |
| 2026-11-03 | Claude Code | 杨佳莹 | 编写采集层验证脚本，断言由8条扩到39条 → scripts/verify_collectors.py |
| 2026-11-03 | Claude Code | 杨佳莹 | GitHub 访问失败分层诊断（DNS/TCP/TLS/应用层），定位链路上游污染 → scripts/check_github_net.py、docs/GitHub访问诊断报告.md |
| 2026-11-03 | Claude Code | 杨佳莹 | 安装 Clash Verge Rev 至 E:\\devtools，编写使用指引 → docs/Clash使用指引.md |
| 2026-11-03 | Claude Code | 杨佳莹 | 对照指导书生成差距清单与补全计划 → output/差距清单与补全计划.md |
| 2026-11-03 | Claude Code | 杨佳莹 | 生成 proposal.md 规范骨架 → specs/proposal.md |
| 2026-11-06 | Claude Code | 杨佳莹 | 生成需求澄清12问清单（数据源/时间窗/读者/粒度/协作归属/隐私边界）与五痛点解法对照表 → docs/需求澄清问答记录.md |
| 2026-11-06 | Claude Code | 杨佳莹 | 调研同类日报方案（daily-report / DevDiary / Teambition AI），整理功能流程与横向对比 → docs/同类方案调研底稿.md |
| 2026-11-06 | Claude Code | 杨佳莹 | 将 mock 演示数据从张三/李四/王五替换为小组成员真实姓名与角色分工 → src/smart_daily/collectors/mock.py |
| 2026-11-06 | Claude Code | 杨佳莹 | 修正成员邮箱映射：杨佳莹邮箱改为 yang13039348457@qq.com，清理 members.py 与 .env 注释中的示例 → src/smart_daily/push/members.py |
| 2026-11-06 | Claude Code | 杨佳莹 | 排查 11-03 飞书群日报性质：查 SQLite 确认为 mock 测试数据加无效身份，随后重发四人版 |
| 2026-11-06 | Claude Code | 杨佳莹 | 真实数据分发排障：MEMBER_EMAILS 补 GitHub 登录名映射，新增 _display_name() 登录名到中文名映射 → src/smart_daily/collectors/github.py |
| 2026-11-06 | Claude Code | 杨佳莹 | 按指导书角色产出表澄清第1周分工，重建16项任务清单并标注五角色责任人 |
| 2026-11-06 | Claude Code | 杨佳莹 | 将 proposal.md 从 0.1 骨架充实为 0.2 内容预填版：五痛点解法、范围实现状态、成功标准挂实测证据、隐含需求7条 → specs/proposal.md |
| 2026-11-06 | Claude Code | 杨佳莹 | 在本机桌面找到4个真实过往课设（弹幕反讽情感分析/建检智通/EOPMIS/智慧景区）并读取文件细节作素材 → docs/杨佳莹-陷阱自查.md、docs/陷阱自查-备选-本周项目版.md |
| 2026-11-09 | Claude Code | 杨佳莹 | 范围变更需求澄清问答（Q16–Q21），逐题回答落盘 → docs/需求澄清问答记录.md |
| 2026-11-09 | Claude Code | 于悦 | 起草验收标准可测性评审意见15条（可测7/有条件可测5/不可测3）→ docs/于悦-可测性评审意见.md |
| 2026-11-09 | Claude Code | 杨佳莹 | 代写《业务调研报告（初稿）》Word版，按指导书第八部分六章结构组织组内一手材料 → 杨佳莹-业务调研报告-初稿.docx |
| 2026-11-09 | Claude Code | 杨佳莹 | 把报告转为 md 交付版，新增附录C列全15张截图并生成单文件内嵌版 → docs/杨佳莹-业务调研报告-初稿.md |
| 2026-11-09 | Claude Code | 于悦 | 编制 proposal 成功标准逐条核对表 → docs/于悦-proposal成功标准逐条核对表.md |
| 2026-11-09 | Claude Code | 于悦 | 红队评审 specs/design.md：挑错9条（高3/中4/低2），逐条回应采纳8条、已知风险1条 → docs/于悦-红队评审意见清单.md |
| 2026-11-09 | Claude Code | 杨佳莹 | 依据 proposal 0.4 撰写架构设计 specs/design.md 0.1并升0.3：四层架构图、数据模型、接口契约、ADR-101~104、附录A → specs/design.md |
| 2026-11-09 | Claude Code | 赵蕊 | 完成第1周本职交付物三份：陷阱自查、环境验证记录、首次提交记录 → docs/赵蕊-陷阱自查.md、环境验证记录.md、首次提交记录.md |
| 2026-11-09 | Claude Code | 杨佳莹 | 撰写双轨建模对比300字（UML定边界、Markdown定规范、两者分工配合）→ docs/双轨建模对比.md |
| 2026-11-09 | Claude Code | 杨佳莹 | 阶段A飞书连通性测试与main推送权限测试 → .github/workflows/connectivity-test.yml、scripts/connectivity_test.py、docs/推送测试-20261109.md |
| 2026-11-09 | Claude Code | 杨佳莹 | 阶段C push实时提交通知：notify.yml + notify_push.py（只读事件文件、actor到中文名映射、标题含日报）→ .github/workflows/notify.yml、scripts/notify_push.py |
| 2026-11-09 | Claude Code | 杨佳莹 | design.md 0.4 在3.5补Actions实测证据段，回指已闭合契约并列出待验证契约2和7 → specs/design.md |
| 2026-11-09 | Claude Code | 杨佳莹 | tasks.md 0.1任务拆解：9阶段39条任务、依赖DAG、可测验收标准、proposal覆盖矩阵 → specs/tasks.md |
| 2026-11-09 | Claude Code | 赵蕊 | 拆解 Superpowers 技能包 subagent-driven-development → docs/赵蕊-技能拆解笔记.md |
| 2026-11-09 | Claude Code | 杨佳莹 | 系统分析报告框架版v0.1：6章加附录A–E、47张表、56个标题、40余处待补块 → docs/系统分析报告-框架版.docx |
| 2026-11-10 | Claude Code | 杨佳莹 | 建立 specs/ 规范版本总表并修正 README 目录结构描述 → specs/README.md |
| 2026-11-10 | Claude Code | 于悦 | 拆解 Superpowers brainstorming 技能（触发描述/工作步骤/配套脚本）→ docs/于悦-技能拆解笔记.md |
| 2026-11-10 | Claude Code | 杨佳莹 | 用 draw.io 绘制第2周1张类图加5张时序图（含PNG预览、分层重排消除连线交叉）→ docs/uml/ |
| 2026-11-10 | Claude Code | 杨佳莹 | 按N8计划列落地22:00自动推送：新建 run_daily.ps1、C7送达判定 any改all、推送失败退出码1、版本升1.1.0、注册计划任务 SmartDaily-2200 |
| 2026-11-10 | Claude Code | 杨佳莹 | 绘制ER图（PlantUML+HTML预览）与日报生成主流程泳道图（6泳道）→ docs/er-diagram.md、docs/er-diagram.html、docs/uml/ |
| 2026-11-10 | Claude Code | 赵蕊 | 逐条回应于悦红队评审8条（RT-01/02/04/05/06/07/08/09）→ docs/赵蕊-红队回应.md |
| 2026-11-10 | Claude Code | 杨佳莹 | 将 design.md 0.4.1升0.5：应送达集合加push_status五态、CLI退出码、3.4.1 push_detail、架构图拆团队日报直达路径等 → specs/design.md |
| 2026-11-10 | Claude Code | 杨佳莹 | 随design 0.5将 tasks.md 升0.1.2：同步TK-103/303/604/707/903 → specs/tasks.md |
| 2026-11-10 | Claude Code | 杨佳莹 | 新增仓库根目录 CLAUDE.md → CLAUDE.md |
| 2026-11-10 | Claude Code | 杨佳莹 | 修订 design.md 0.5.1 与 tasks.md 0.1.3：design补ER附件、ADR备选项等；tasks重画依赖图、新增并行组标记 → specs/ |
| 2026-11-10 | Claude Code | 杨佳莹 | 起草第2周开发工程师三项交付：接口契约工程可行性评审意见、技能拆解笔记、v1实现与审查提交历史 → docs/杨佳莹-接口契约工程可行性评审意见.md、技能拆解笔记.md、v1实现与审查提交历史.md |
| 2026-11-10 | Claude Code | 于悦 | 红队评审清单闭环回填与仓库同步：8行闭环记录补提交号，在清单说明下补闭环依据 → docs/于悦-红队评审意见清单.md |
| 2026-11-10 | Claude Code | 杨佳莹 | 按design 3.4落地CLI 0/1/2/3四码退出码，同步接口契约评审意见 → src/smart_daily/cli.py、orchestrator.py |
| 2026-11-10 | Claude Code | 于悦 | 核对表同步proposal 0.4.2可测性回应：G2/C6改观察项、C7恢复可测、G4时间口径对齐 → docs/于悦-proposal成功标准逐条核对表.md |
| 2026-11-10 | Claude Code | 杨佳莹 | 更新 specs/README.md 版本总表：登记 proposal 格式整理提交，备注状态行滞后等待处理项 → specs/README.md |
| 2026-11-10 | Claude Code | 杨佳莹 | 核对《小组角色分工与轮换表》第2周轮换并修正第六节失效待办 → docs/小组角色分工与轮换表.md |
| 2026-11-10 | Claude Code | 杨佳莹 | 在第14节评审签字表本人行签字，指向已成文的接口契约评审意见 → specs/tasks.md |
| 2026-11-10 | Claude Code | 方赫 | 【方赫】第2周需求分析师用例图重画：按proposal 0.4.2的S1–S9/C1–C10回指，补UC10/UC7/UC4/UCX → docs/uml/用例图-智能日报生成器.puml、.png |
| 2026-11-10 | Claude Code | 方赫 | 【方赫】建用例模板与需求可追溯对照表，填齐13个UC×10字段、S/C/N三张表 → docs/方赫-用例模板.md、需求可追溯对照表.md |
| 2026-11-10 | Claude Code | 方赫 | 【方赫】需求分析报告Word六章：自动目录域+三级编号+图3-1与表1-1引用+3张UML图嵌入 → docs/方赫-需求分析报告.docx |
| 2026-11-10 | Claude Code | 方赫 | 【方赫】全员项技能拆解笔记（executing-plans）、第5章思考题两问与第2周周报告 → docs/方赫-技能拆解笔记.md、第5章思考题.md、第2周周报告.md |
| 2026-11-10 | Claude Code | 方赫 | 【方赫】出用例红队评审单、处置N8规范冲突、编阶段评审会答辩提纲 → docs/方赫-用例红队评审单.md、N8范围冲突处置记录.md、阶段评审会答辩提纲.md |
| 2026-11-10 | Claude Code | 方赫 | 【方赫】第1周步骤1~4复核：用gh OAuth读取Actions Secrets键名列表，同步凭证登记表与轮换表口径，整理3条可贴群话术 → docs/第1周-凭证就绪登记.md、credentials-registry.md |
| 2026-11-10 | Claude Code | 方赫 | 【方赫】依据本人确认回填第1周步骤1~4的3个通知勾与发送日期 → docs/第1周-凭证就绪登记.md |
| 2026-11-10 | Claude Code | 方赫 | 【方赫】第1周步骤8用例执行记录补齐：74次Actions run日志、23条离线断言、28条单测，填齐TC-01~TC-08 → docs/testing/用例执行记录-第1周.md、证据/W1-* |
| 2026-11-10 | Claude Code | 方赫 | 【方赫】回填全组凭证登记表于悦、赵蕊两行并同步轮换表第三节 → docs/credentials-registry.md、docs/小组角色分工与轮换表.md |
| 2026-11-10 | Claude Code | 杨佳莹 | 修复日报把历史提交全算进当天的缺陷：run()按报告日期取本地自然日窗口并在编排层再裁剪 → src/smart_daily/orchestrator.py |
| 2026-11-11 | Claude Code | 杨佳莹 | 补交采集层验证脚本（34项断言）与实跑输出，交接说明改用仓库相对路径 → scripts/verify_collectors.py、docs/testing/证据/TK-701-验证脚本输出-2026-11-11.txt、docs/采集层交接说明.md |
| 2026-11-11 | Claude Code | 杨佳莹 | 补齐两处静默失败的日志：collect_with_fallback捕获异常时print到stdout，resolve_recipients未知成员时打身份未映射日志 → src/smart_daily/collectors/base.py、push/members.py |
| 2026-11-11 | Claude Code | 杨佳莹 | 把 tasks.md 中 TK-701 状态从⏳改为✅并附实测证据 → specs/tasks.md |
| 2026-11-11 | Claude Code | 杨佳莹 | 落实 tasks 0.1.4：架构签字落格，改写TK-404③/TK-706/TK-103②/TK-305③/TK-701③ → specs/tasks.md |
| 2026-11-11 | Claude Code | 杨佳莹 | 上传桌面版《系统分析报告》v1.1与《技术调研报告》v1.0至docs/并删除框架版v0.1 → docs/系统分析报告.docx、技术调研报告.docx |
| 2026-11-12 | Claude Code | 杨佳莹 | GitHub采集器TLS修复：改用系统证书库，commits查询加sha=GITHUB_BRANCH，空列表打印排查提示 → src/smart_daily/collectors/github.py |
| 2026-11-12 | Claude Code | 杨佳莹 | TK-902/TK-903阶段一发布：dev合并进main（a2d4940），打tag v1-sdd与v1-sdd-rc1，同步TK勾与BRANCHING.md → specs/tasks.md、BRANCHING.md |
| 2026-11-12 | Claude Code | 方赫 | 【方赫】完成第1周300字陷阱自查与附录E第1周两问，五大陷阱各举一例并附出处 → docs/方赫-陷阱自查.md |
| 2026-11-12 | Claude Code | 方赫 | 【方赫】补齐C4/G4口径A的规范追认：proposal加补记2，同步design/tasks/README与需求侧七份文档 → specs/、docs/ |
| 2026-11-12 | Claude Code | 方赫 | 【方赫】核proposal成功标准没测问题：§6两列回填真实测试名与证据编号，§4.1实现状态按事实更新 → specs/proposal.md |
| 2026-11-12 | Claude Code | 方赫 | 【方赫】勾讫 proposal §2 G1/G3/G4/G5 四个确认位并加授权留痕 → specs/proposal.md |
| 2026-11-12 | Claude Code | 方赫 | 【方赫】删除《proposal仍未测项清单》并清理全仓15处引用 → specs/proposal.md |
| 2026-11-12 | Claude Code | 方赫 | 【方赫】完成第1周TC-03/TC-05端到端补测：隔离分支跑3条真实Actions run，新增2份证据 → docs/testing/ |
| 2026-11-12 | Claude Code | 方赫 | 【方赫】收口两周遗留：代填陷阱自查核验勾、第1周AI日志归档、成功标准定稿、凭证确认，同步用例模板与对照表 → docs/ |
| 2026-11-12 | Claude Code | 杨佳莹 | 身份归并落地：新增identity.py::lookup_display_name收敛MEMBER_DISPLAY_NAMES解析，github.py与local_git.py统一映射 → src/smart_daily/identity.py、collectors/、.env.example |
| 2026-11-12 | Claude Code | 方赫 | 【方赫】最后收口：勾讫待确认行、同步规范版本总表、核销TK-803、预置TC-06操作卡 → docs/ai-usage-log.md、specs/README.md、specs/tasks.md |
| 2026-11-12 | Claude Code | 方赫 | 22:00自动定时定性修正：属N8计划列兑现、非范围变更，项目当前即v1.1 → specs/proposal.md、specs/tasks.md、README.md、docs/方赫-N8范围冲突处置记录.md |
| 2026-11-12 | Claude Code | 杨佳莹 | 为答辩涉及代码补设计说明注释（20个文件、+101行），标注分层职责与降级链语义 → 各源文件 |
| 2026-11-12 | Claude Code | 杨佳莹 | README顶部明示当前运行状态：每天22:00自动推送日报、项目为v1.1 → README.md |
| 2026-11-13 | Claude Code | 杨佳莹 | 补交第1周隐含需求清单（I1–I28共28条，逐条保留问答原文）→ docs/杨佳莹-隐含需求清单.md |
| 2026-11-13 | Claude Code | 杨佳莹 | 修正22:00自动定性的三处同步（proposal补记8、tasks守卫行、README待办区）→ specs/proposal.md、specs/tasks.md、README.md |
| 2026-11-13 | Claude Code | 方赫 | 修正N8处置记录节号重复（新增节与可核验出处节两处均为五，后者改六）→ docs/方赫-N8范围冲突处置记录.md |
| 2026-11-13 | Claude Code | 杨佳莹 | 为答辩涉及代码补设计说明注释（与11-12同批，20个文件、+101行、0删除）→ .github/workflows/notify.yml、main.py、pyproject.toml、scripts/、src/smart_daily/、tests/ |
| 2026-11-13 | Claude Code | 杨佳莹 | README开头明示22:00自动推送状态块 → README.md |
| 2026-11-16 | Claude Code | 赵蕊 | v2工程初始化：从baseline建v2-superpowers分支，搭骨架（pyproject.toml/README.md/__init__.py/.gitkeep），写初始化记录 → v2/、docs/赵蕊-v2初始化记录.md |
| 2026-11-16 | Claude Code | 杨佳莹 | v2方案由长驻分支改为目录隔离：git merge把v2骨架并入dev的v2/子目录，改BRANCHING.md/ci.yml/角色准入记录/.env.example → BRANCHING.md、.github/workflows/ci.yml等 |
| 2026-11-16 | Claude Code | 赵蕊 | 删除阶段二旧分支v2-superpowers并同步文档口径 → BRANCHING.md、docs/赵蕊-v2初始化记录.md |
| 2026-11-16 | Claude Code | 杨佳莹 | TK-V2-101身份归并走TDD绿步：实现identity.py的normalize_key与normalize_members，新增v2/.gitignore → v2/src/smart_daily_v2/identity.py、v2/.gitignore |
| 2026-11-16 | Claude Code | 赵蕊 | 第3周测试工程师产出：缺陷清单与系统化调试根因记录6条（DEF-01~DEF-06）→ docs/赵蕊-缺陷清单与根因记录.md |
| 2026-11-17 | Claude Code | 于悦 | 【于悦】核查第3周本机与远端dev环境，按指导书第3周第3步+附录B+writing-plans起草v2任务清单（36条TK-V2、七段链路、mermaid依赖图、并行组）→ v2/specs/tasks.md |
| 2026-11-17 | Claude Code | 赵蕊 | 【赵蕊】TK-V2-102数据模型与归一化TDD红步：新增test_models.py五个用例（含R4时区边界）→ v2/tests/test_models.py |
| 2026-11-17 | Claude Code | 赵蕊 | 【赵蕊】补tzdata依赖修复Windows时区库缺失：local_date改用ZoneInfo(Asia/Shanghai)，同步tasks验收④ → v2/pyproject.toml、v2/specs/tasks.md、v2/uv.lock |
| 2026-11-17 | Claude Code | 赵蕊 | 【赵蕊】TK-V2-102数据模型与归一化TDD绿步：实现frozen WorkItem、三种源记录、local_date与normalize → v2/src/smart_daily_v2/models.py |
| 2026-11-17 | Claude Code | 于悦 | 【于悦】修订tasks.md §8.2 U1为已闭环：核对issue #14 K1与补丁后改写U1并同步006/104/602过期表述 → v2/specs/tasks.md |
| 2026-11-17 | Claude Code | 赵蕊 | 【赵蕊】按issue #14 K1修订v2/README.md §2降级链语义（空列表停止、全失败抛AllSourcesUnavailableError）→ v2/README.md |
| 2026-11-17 | Claude Code | 杨佳莹 | v2 tasks.md起草与提交的日志补记 → docs/ai-usage-log.md |
| 2026-11-17 | Claude Code | 杨佳莹 | v1目录整体迁移：把docs/scripts/specs/src/tests及运行必需件整体移入v1/，改run_daily.ps1路径，根目录建转发脚本 → v1/、scripts/run_daily.ps1 |
| 2026-11-17 | Claude Code | 杨佳莹 | AI使用日志格式整理：按第3周拆出独立周表，第2周表头改为11-09至11-15，收敛空行 → v1/docs/ai-usage-log.md |
| 2026-11-17 | Claude Code | 方赫 | 【方赫】TK-V2-105配置与凭证读取模块TDD红→绿：实现config.py、test_config.py、.env.example → v2/src/smart_daily_v2/config.py等 |
| 2026-11-17 | Claude Code | 方赫 | 【方赫】按issue #14修订接口契约K2/K8/K5（退出码数据来源、异常继承、collect关键字参数）→ v2/specs/tasks.md |
| 2026-11-17 | Claude Code | 方赫 | 【方赫】TK-V2-103采集协议与异常契约TDD红→绿：实现sources/base.py与test_worksource.py → v2/src/smart_daily_v2/sources/base.py等 |
| 2026-11-18 | Claude Code | 于悦 | 【于悦】TK-V2-703把外部定稿的进度维护记录逐字复制入v2/docs并提交 → v2/docs/于悦-第3周-tasks进度维护记录.md |
| 2026-11-18 | Claude Code | 方赫 | 【方赫】TK-V2-301按成员分组TDD红→绿：实现reports/generator.py的group_by_member → v2/src/smart_daily_v2/reports/generator.py等 |
| 2026-11-18 | Claude Code | 方赫 | 【方赫】TK-V2-302单条渲染TDD红→绿：追加format_item与4条用例 → v2/src/smart_daily_v2/reports/generator.py等 |
| 2026-11-18 | Claude Code | 方赫 | 【方赫】TK-V2-303个人日报TDD红→绿：追加build_personal_report与3条用例 → v2/src/smart_daily_v2/reports/generator.py等 |
| 2026-11-18 | Claude Code | 方赫 | 【方赫】TK-V2-304团队日报TDD红→绿：追加build_team_report与3条用例 → v2/src/smart_daily_v2/reports/generator.py等 |
| 2026-11-18 | Claude Code | 方赫 | 【方赫】TK-V2-401成员邮箱映射TDD红→绿：新建notifiers/members.py实现load_member_emails与load_report_recipients → v2/src/smart_daily_v2/notifiers/members.py等 |
| 2026-11-18 | Claude Code | 于悦 | 【于悦】TK-V2-007按组内归位口径同步tasks.md文档落点至v2/docs → v2/specs/tasks.md |
| 2026-11-18 | Claude Code | 于悦 | 【于悦】TK-V2-703补记文档落点归位与007修订链 → v2/docs/于悦-第3周-tasks进度维护记录.md |
| 2026-11-18 | Claude Code | 于悦 | 【于悦】补2026-11-18每日站会记录 → v2/每日站会记录/2026-11-18.md |
| 2026-11-18 | Claude Code | 于悦 | 【于悦】站会记录补B-06（K7/S9/C10实时提醒范围意见）→ v2/每日站会记录/2026-11-18.md |
| 2026-11-18 | Claude Code | 方赫 | 【方赫】TK-V2-402 SMTP邮件通道TDD红→绿：新建notifiers/email.py → v2/src/smart_daily_v2/notifiers/email.py等 |
| 2026-11-18 | Claude Code | 方赫 | 【方赫】TK-V2-403群通道与签名TDD红→绿：新建notifiers/webhook.py实现gen_sign与FeishuWebhookNotifier → v2/src/smart_daily_v2/notifiers/webhook.py等 |
| 2026-11-18 | Claude Code | 方赫 | 【方赫】TK-V2-404分发规则与送达判定TDD红→绿：新建notifiers/dispatch.py实现dispatch与all_delivered → v2/src/smart_daily_v2/notifiers/dispatch.py等 |
| 2026-11-18 | Claude Code | 杨佳莹 | 第3周产出文档归位：把11份第3周产出git mv进v2/docs并同步24处路径引用 → v2/docs/ |
| 2026-11-18 | Claude Code | 杨佳莹 | AI使用日志按方案乙归位：从v1/docs迁回根docs/，同步7处现行路径引用 → docs/ai-usage-log.md |
| 2026-11-18 | Claude Code | 杨佳莹 | 第3周架构师两份产出定稿入库：code-review评审意见与设计与specs一致性检查记录 → v2/docs/杨佳莹-第3周-code-review评审意见.md等 |
| 2026-11-19 | Claude Code | 杨佳莹 | TK-V2-606身份归并回归扩展：新增身份集成测试与identity_harness fixture → v2/tests/test_integration_identity.py、conftest.py |
| 2026-11-19 | Claude Code | 于悦 | 【于悦】TK-V2-703同步11-19进度维护记录（补齐301–304/401–404/601九条证据）→ v2/docs/于悦-第3周-tasks进度维护记录.md |
| 2026-11-19 | Claude Code | 于悦 | 【于悦】补第3周code-review互评记录（评审方赫404/601两条提交）→ v2/docs/于悦-第3周-code-review互评记录.md |
| 2026-11-19 | Claude Code | 方赫 | 【方赫】TK-V2-605送达判定用例C7/R3：新增test_integration_delivery.py与delivery_harness fixture → v2/tests/ |
| 2026-11-19 | Claude Code | 方赫 | 【方赫】code-review意见回应与互评记录：回应于悦5条意见、互评他人2次提交共9条意见 → v2/docs/方赫-第3周-code-review意见回应.md、互评记录.md |
| 2026-11-19 | Claude Code | 方赫 | 【方赫】TK-V2-604格式一致性与计数用例：新增test_integration_format.py与format_harness fixture → v2/tests/ |
| 2026-11-19 | Claude Code | 于悦 | 【于悦】TK-V2-007按K1解锁104/602的⏸，改tasks.md三处状态注记与进度记录两行 → v2/specs/tasks.md、v2/docs/于悦-第3周-tasks进度维护记录.md |
| 2026-11-19 | Claude Code | 于悦 | 【于悦】TK-V2-703同步104/602解锁后的维护口径，§四第1条两处不一致改已一致 → v2/docs/于悦-第3周-tasks进度维护记录.md |
| 2026-11-19 | Claude Code | 于悦 | 【于悦】TK-V2-703登记604/605/606三行🟩待核对并更正§四第1条行号 → v2/docs/于悦-第3周-tasks进度维护记录.md |
| 2026-11-19 | Claude Code | 方赫 | 【方赫】TK-V2-104异常驱动降级链TDD红→绿：新增sources/fallback.py与test_fallback.py → v2/src/smart_daily_v2/sources/fallback.py等 |
| 2026-11-19 | Claude Code | 方赫 | 【方赫】TK-V2-607 C1–C10逐条核对表编制 → v2/tests/acceptance_matrix.md |
| 2026-11-19 | Claude Code | 方赫 | 【方赫】测试覆盖率提升：新增test_coverage_improvement.py与test_dispatch_real_calls.py，91%提升至97% → v2/tests/ |
| 2026-11-19 | Claude Code | 于悦 | 【于悦】补2026-11-19每日站会记录 → v2/每日站会记录/2026-11-19.md |
| 2026-11-19 | Claude Code | 杨佳莹 | GitHub日报采集器双分支改造：采集器改采main+dev并按sha去重，新增DEFAULT_BRANCHES/collect_commits_multi → v1/src/smart_daily/collectors/github.py、tests/、specs/ |
| 2026-11-19 | Claude Code | 方赫 | 【方赫】TK-V2-201 GitHub提交采集TDD红→绿：新增sources/github.py与test_source_github.py → v2/src/smart_daily_v2/sources/github.py等 |
| 2026-11-19 | Claude Code | 方赫 | 【方赫】TK-V2-202飞书任务采集TDD红→绿：新增sources/feishu_tasks.py与test_source_feishu_tasks.py → v2/src/smart_daily_v2/sources/feishu_tasks.py等 |
| 2026-11-20 | Claude Code | 方赫 | 【方赫】TK-V2-203飞书群消息采集（单群限定）TDD红→绿：新增sources/feishu_chat.py → v2/src/smart_daily_v2/sources/feishu_chat.py等 |
| 2026-11-20 | Claude Code | 于悦 | 【于悦】TK-V2-703进度维护记录周五汇总更新：六行补🟩待核对，新增§六进度汇总 → v2/docs/于悦-第3周-tasks进度维护记录.md |
| 2026-11-20 | Claude Code | 于悦 | 【于悦】TK-V2-703二次补记：补登203行并更正09:51首版，汇总🟩26/⬜10改🟩27/⬜9 → v2/docs/于悦-第3周-tasks进度维护记录.md |
| 2026-11-20 | Claude Code | 方赫 | 【方赫】TK-V2-501主编排流程TDD红→绿：新增orchestrator.py（9键返回、五态push_status）→ v2/src/smart_daily_v2/orchestrator.py等 |
| 2026-11-20 | Claude Code | 方赫 | 【方赫】TK-V2-502 SQLite幂等落库TDD红→绿：新增storage.py（upsert、UNIQUE约束）→ v2/src/smart_daily_v2/storage.py等 |
| 2026-11-20 | Claude Code | 方赫 | 【方赫】TK-V2-503历史查询list_reports TDD红→绿：storage.py追加ReportMeta与list_reports → v2/src/smart_daily_v2/storage.py等 |
| 2026-11-20 | Claude Code | 方赫 | 【方赫】TK-V2-504 CLI与退出码TDD红→绿：新增cli.py（五参数、退出码0/1/2/3）→ v2/src/smart_daily_v2/cli.py等 |
| 2026-11-20 | Claude Code | 杨佳莹 | TK-V2-602降级注入用例（P6-b集成测试）：新增test_integration_fallback.py与fallback_harness fixture → v2/tests/ |
| 2026-11-20 | Claude Code | 于悦 | 【于悦】TK-V2-007 tasks负责人列核定：§4新增负责人列、36条逐行标注、版本0.1.1→0.1.2 → v2/specs/tasks.md |
| 2026-11-20 | Claude Code | 杨佳莹 | CLI可用性补齐（范围外）：加__main__入口、README §5运行说明、CLI边界落库转发 → v2/src/smart_daily_v2/cli.py、v2/README.md、v2/tests/test_cli_usability.py |
| 2026-11-20 | Claude Code | 杨佳莹 | TK-V2-202/203飞书数据源鉴权修复：新增tenant_access_token换取与Bearer注入 → v2/src/smart_daily_v2/sources/feishu_tasks.py、feishu_chat.py等 |
| 2026-11-20 | Claude Code | 杨佳莹 | 飞书空数据响应缺items键崩溃修复：两处data[items]改data.get(items, []) → v2/src/smart_daily_v2/sources/ |
| 2026-11-20 | Claude Code | 杨佳莹 | GitHub源真实跑两处bug修复：author=None改条件添加参数，顶层author=null降级取commit.author.name → v2/src/smart_daily_v2/sources/ |
| 2026-11-20 | Claude Code | 杨佳莹 | 成员账号名到中文显示名映射（范围外）：identity.py加display_name，orchestrator采集后插入映射步 → v2/src/smart_daily_v2/ |
| 2026-11-20 | Claude Code | 于悦 | 【于悦】补2026-11-20每日站会记录 → v2/每日站会记录/2026-11-20.md |
| 2026-11-20 | Claude Code | 杨佳莹 | 团队日报格式美化（范围外）：生成器加贡献一览表、条目改三列表格、类型徽标 → v2/src/smart_daily_v2/reports/generator.py |
| 2026-11-20 | Claude Code | 杨佳莹 | 每日22:00自动日报定时（范围外）：新建v2/scripts/run_daily.ps1、修GITHUB_BRANCH、注册计划任务 → v2/scripts/run_daily.ps1 |
| 2026-11-20 | Claude Code | 杨佳莹 | 接通老师邮箱团队日报通道（3de8afd）：orchestrator导入并传team_recipients，.env设老师邮箱 |
| 2026-11-20 | Claude Code | 杨佳莹 | dev到main一次性合并（92b8919）：临时worktree基于origin/main合并，冲突日志按双方保留解 → origin/main |
| 2026-11-20 | Claude Code | 杨佳莹 | 22:00首次自动触发实证：LastRunTime=22:00:00、LastTaskResult=0、落库23条 |
| 2026-11-20 | Claude Code | 杨佳莹 | GitHub采集器main+dev双分支并采与SHA去重（范围外）：新增_branch_list与collect_commits_multi → v2/src/smart_daily_v2/sources/github.py、tests/ |
| 2026-11-20 | Claude Code | 杨佳莹 | 团队日报/个人日报二次美化（范围外）：generator.py加_clean/_headline/_supplement，同步4个测试 → v2/src/smart_daily_v2/reports/generator.py等 |
| 2026-11-20 | Claude Code | 方赫 | V1入口/U2实时提醒口径核验（只读）：核实v2无import smart_daily、任务指向v2脚本 → v2/docs/方赫-V1入口与U2实时提醒-口径说明-2026-11-20.md |
| 2026-11-20 | Claude Code | 杨佳莹 | 创建issue #16（澄清V1/V2入口争议与U2实时提醒归属） |
| 2026-11-21 | Claude Code | 杨佳莹 | 【杨佳莹】实时提醒纳入v2方案草稿：核对tasks §8.2 U2、C10、notify.yml后起草v2/docs/实时提醒纳入v2-方案草稿.md |
| 2026-11-21 | Claude Code | 杨佳莹 | 【杨佳莹】实时提醒纳入v2本轮实现：新增notify_push.py与9条测试，根notify.yml的run改python -m smart_daily_v2.notify_push → v2/src/smart_daily_v2/notify_push.py、.github/workflows/notify.yml |
| 2026-11-22 | Claude Code | 杨佳莹 | TK-V2-803根notify.yml切到v2实时提醒通道：新增test_notify_workflow.py 7用例，根notify.yml改pip install -e ./v2与python -m → .github/workflows/notify.yml、v2/tests/ |
| 2026-11-22 | Claude Code | 杨佳莹 | 补推notify.yml改动：http.proxy+HTTP/1.1后成功推dev → origin/dev |
| 2026-11-22 | Claude Code | 杨佳莹 | 创建issue #17并补CI实证：两次dev push各触发通知与CI门禁共4个run全success |
| 2026-11-23 | Claude Code | 方赫 | 【方赫】第3周本人30条AI日志条目统一签认 |
| 2026-11-23 | Claude Code | 于悦 | 【于悦】第3周周报/方法切换回顾/第5章思考题三份文档签认 → v2/docs/于悦-第3周周报告.md等 |
| 2026-11-23 | Claude Code | 杨佳莹 | U2状态与验收矩阵C10判定回写：S9/C10改已实现/✅通过，C1/C2/C5/C8一并回写 → v2/specs/tasks.md、v2/tests/acceptance_matrix.md |
| 2026-11-23 | Claude Code | 赵蕊 | 第4周待办issue化+第3周返工归类：建issue #19/#20/#21/#22，三项改第3周返工 → GitHub issue、v2/docs/赵蕊-缺陷清单与根因记录.md |
| 2026-11-23 | Claude Code | 杨佳莹 | 对issue #19–#22补assign与正文@责任人 |
| 2026-11-23 | Claude Code | 杨佳莹 | 第4周#20覆盖率缺口补测：补两条用例覆盖config.py有值返回与members.py空名跳过 → v2/tests/、v2/docs/testing/覆盖率报告-第3周.md |
| 2026-11-23 | Claude Code | 杨佳莹 | 第4周测试产出①回归测试全量执行报告 → v2/docs/testing/回归测试全量执行报告-第4周.md |
| 2026-11-23 | Claude Code | 杨佳莹 | 第4周测试产出②评审专家追问清单（20题/6类）与模拟答辩记录模板 → v2/docs/杨佳莹-第4周-评审专家追问清单与模拟答辩记录.md |
| 2026-11-23 | Claude Code | 杨佳莹 | 第4周测试产出③总结报告第3章质量数据素材 → v2/docs/杨佳莹-第4周-总结报告第3章质量数据素材.md |
| 2026-11-23 | Claude Code | 杨佳莹 | 配置管理员产出：AI使用合规声明汇总与总结报告第4章素材 → v2/docs/杨佳莹-第4周-AI使用合规声明汇总.md、第4章素材.md |
| 2026-11-24 | Claude Code | 杨佳莹 | 分工与轮换表移至根docs并补齐第3/4周分工 → docs/小组角色分工与轮换表.md |
| 2026-11-24 | Claude Code | 于悦 | 第3周进度维护记录§四12条本人核对结论回填 → v2/docs/于悦-第3周-tasks进度维护记录.md |
| 2026-11-24 | Claude Code | 杨佳莹 | 分工与轮换表去重整理：四周分工收敛为第四节唯一权威表，111行改83行 → docs/小组角色分工与轮换表.md |
| 2026-11-24 | Claude Code | 于悦 | 第3周code-review互评三处签认回填 → v2/docs/于悦-第3周-code-review互评记录.md等 |
| 2026-11-24 | Claude Code | 杨佳莹 | 分工与轮换表删除来源说明与签字声明 → docs/小组角色分工与轮换表.md |
| 2026-11-24 | Claude Code | 赵蕊 | 【赵蕊】变更单落地proposal差异版0.5-diff 0.1：基线声明+S10+FR-KQ1+C11+I29+术语+N3解除 → v2/specs/proposal.md、docs/赵蕊-第4周-proposal变更对照表.md、落点分析纪要.md |
| 2026-11-24 | Claude Code | 杨佳莹 | DEF-05应送达集合分母返工（Issue #19）：expected独立构造、push_detail覆盖全scope → v2/src/smart_daily_v2/orchestrator.py、v2/tests/test_def05_expected.py |
| 2026-11-24 | Claude Code | 杨佳莹 | DEF-05补绿轮：补齐no_recipient/no_channel error标记 → v2/src/smart_daily_v2/orchestrator.py |
| 2026-11-24 | Claude Code | 方赫 | #21确认留痕备料：列--source取值集合与退出码表唯一事实源结论及证据 → v2/docs/方赫-第3周-TK-V2-504两处口径确认留痕.md |
| 2026-11-24 | Claude Code | 杨佳莹 | DEF-05补绿轮失败诊断与重跑：Claude自动更新致Bash 127，重开会话补齐error标记后273 passed |
| 2026-11-24 | Claude Code | 杨佳莹 | design 0.7差异版初稿起草：按方案A差异登记、以v2代码为事实源做影响预判 → v2/specs/design.md |
| 2026-11-24 | Claude Code | 赵蕊 | 【赵蕊】DEF-05修复测试侧闭环：复跑273 passed，缺陷清单四处改已闭环，产出issue #19评论草稿 → v2/docs/testing/证据/、v2/docs/赵蕊-缺陷清单与根因记录.md |
| 2026-11-24 | Claude Code | 杨佳莹 | design 0.7-diff 0.2定稿：核实飞书考勤接口user_tasks/query，定案架构师职权内契约 → v2/specs/design.md |
| 2026-11-24 | Claude Code | 赵蕊 | 【赵蕊】新记DEF-10：ruff format扫描Markdown代码块致CI红 → v2/docs/赵蕊-缺陷清单与根因记录.md |
| 2026-11-24 | Claude Code | 杨佳莹 | design 0.7-diff 0.3追认登记：A组待追认项改已全组评审追认 → v2/specs/design.md |
| 2026-11-24 | Claude Code | 杨佳莹 | design 0.7-diff 0.4本人拍定四项：#4走方案A、#7取上班卡回落下班卡、#9登记第五源同步义务、#10签认 → v2/specs/design.md、#21留痕文档 |
| 2026-11-24 | Claude Code | 方赫 | DEF-10甲案修复：design.md §4-1契约代码块按ruff 0.17.5重排；备B组6项催办话术 → v2/specs/design.md、v2/docs/方赫-第4周-变更涟漪B组催办清单.md |
| 2026-11-24 | Claude Code | 杨佳莹 | 撤回催办清单正式文档改工作区群聊话术，删催办清单文档 → v2/docs/ |
| 2026-11-24 | Claude Code | 方赫 | 第4周架构师三件本职产出：规范守护自检记录、规范审计报告、总结报告第2章过程回顾，另起草第5章思考题 → v2/docs/方赫-第4周-*.md |
| 2026-11-24 | Claude Code | 方赫 | 第4周四份产出签认：状态改本人已核验签认 → v2/docs/方赫-第4周-*.md |
| 2026-11-24 | Claude Code | 方赫 | 起草第5章职业道德与规范践行心得（草稿v0.1）并随后签认 → v2/docs/方赫-第4周-总结报告第5章职业道德与规范践行心得.md |
| 2026-11-24 | Claude Code | 方赫 | 清理第3周两份文档签认话术残留7处 → v2/docs/方赫-第3周周报告.md、code-review互评记录.md |
| 2026-11-24 | Claude Code | 杨佳莹 | 补发10点未送出的日报：定位采集全失败，用github源真推飞书群+老师邮箱，落库34条 → v2/data/logs/、reports.db |
| 2026-11-24 | Claude Code | 方赫 | 10点日报未发根因诊断：WinINET代理SSL EOF叠加GitHub匿名限额耗尽+feishu源失败 → v2/docs/方赫-11-24-22点日报未发根因诊断.md |
| 2026-11-25 | Claude Code | 赵蕊 | 【赵蕊】proposal 0.5-diff 0.2：C11行格式改表格行、record_id内嵌detail、DEF-10闭环回写、tasks增9xx组4条 → v2/specs/proposal.md、tasks.md、缺陷清单等 |
| 2026-11-25 | Claude Code | 赵蕊 | 【赵蕊】第3周签字栏5处回填 → v2/docs/于悦-第3周-tasks进度维护记录.md等 |
| 2026-11-25 | Claude Code | 赵蕊 | 【赵蕊】F1-01落实：README §1/§4补空列表对照句 → v2/README.md |
| 2026-11-25 | Claude Code | 赵蕊 | 【赵蕊】第1–4周思考题补齐四份 → v1/docs/赵蕊-第1周思考题.md、第2周、v2/docs/第3周、第4周 |
| 2026-11-25 | Claude Code | 于悦 | 【于悦】TK-V2-901考勤采集源TDD红→绿：新增sources/attendance.py与test_source_attendance.py → v2/src/smart_daily_v2/sources/attendance.py等 |
| 2026-11-25 | Claude Code | 杨佳莹 | 【杨佳莹】TK-V2-904用例骨架+U13 B#6映射方案草稿：新增test_integration_attendance.py 5用例（skipif）与映射方案 → v2/tests/、v2/docs/杨佳莹-第4周-U13配置前置B6映射方案草稿.md |
| 2026-11-25 | Claude Code | 于悦 | 【于悦】TK-V2-902/903考勤支路合流与badge映射TDD红→绿：orchestrator加独立支路、cli加第五源、generator加考勤badge → v2/src/smart_daily_v2/ |
| 2026-11-25 | Claude Code | 赵蕊 | 【赵蕊】组内裁决1A/2A回填三份规范：proposal 0.5-diff 0.3、design §8-B、tasks 904验收 → v2/specs/ |
| 2026-11-25 | Claude Code | 赵蕊 | 【赵蕊】新记DEF-11：901-903与904集成口径未对齐致CI红 → v2/docs/赵蕊-缺陷清单与根因记录.md |
| 2026-11-25 | Claude Code | 方赫 | 清理第3周红绿循环记录残留解释性话术3处 → v2/docs/方赫-红绿循环记录-第3周.md |
| 2026-11-26 | Claude Code | 杨佳莹 | 应于悦请求代修杨佳莹904两条用例（补group_by_member层、改SQLite正文验证）+ 于悦自修901 ruff → v2/tests/ |
| 2026-11-26 | Claude Code | 于悦 | 【于悦】第4周产出①变更涟漪代码实现与回归通过记录代起草 → v2/docs/于悦-第4周-变更涟漪代码实现与回归通过记录.md |
| 2026-11-26 | Claude Code | 于悦 | 【于悦】第4周产出②答辩演示环境与演示脚本代起草 → v2/docs/于悦-第4周-答辩演示环境与演示脚本.md |
| 2026-11-26 | Claude Code | 方赫 | 【方赫】第4周第二层扩展架构师预判与裁定清单草稿（E1–E5）→ v2/docs/方赫-第4周-第二层扩展-架构师预判与裁定清单.md |
| 2026-11-26 | Claude Code | 方赫 | 【方赫】需求侧落条目草案（供赵蕊粘贴）起草后撤回删除 → v2/docs/ |
| 2026-11-26 | Claude Code | 赵蕊 | 【赵蕊】第二层考勤扩展落条目proposal 0.5-diff 0.4：新增S11–S15、C12、I30、开放问题#7–#11 → v2/specs/proposal.md、变更对照表.md |
| 2026-11-26 | Claude Code | 赵蕊 | 【赵蕊】第4周周报告起草+DEF-11闭环回写 → v2/docs/赵蕊-第4周周报告.md、缺陷清单.md |
| 2026-11-26 | Claude Code | 杨佳莹 | 补考勤行代码进默认日报：cli默认源加FeishuAttendanceSource、config加FEISHU_ATTENDANCE_MEMBER_MAP解析 → v2/src/smart_daily_v2/ |
| 2026-11-26 | Claude Code | 杨佳莹 | 日报考勤条目脱敏：generator.py的_headline对考勤固定返回已打卡、_supplement只摘record_id → v2/src/smart_daily_v2/reports/generator.py |
| 2026-11-26 | Claude Code | 杨佳莹 | 真实打卡联调修复：attendance.py的_pick_occurred_at/_pick_record_id/_pick_status兼容嵌套格式与unix秒戳 → v2/src/smart_daily_v2/sources/attendance.py |
| 2026-11-26 | Claude Code | 于悦 | 同步于悦三份第4周文档的过时数字与口径（308→314、HEAD、format文件数）→ v2/docs/于悦-第4周-*.md |
| 2026-11-26 | Claude Code | 方赫 | 【方赫】design 0.7-diff 0.5落地事实回填：§9新增6条能力对照、§8-B #5/#6/#8闭环 → v2/specs/design.md |
| 2026-11-26 | Claude Code | 赵蕊 | 【赵蕊】真实联调对齐：proposal 0.5-diff 0.5脱敏口径、tasks 901/903/904验收完善 → v2/specs/proposal.md、tasks.md、变更对照表.md |
| 2026-11-26 | Claude Code | 赵蕊 | 【赵蕊】proposal 0.1–0.5评审通过归档+第4周周报告签认 → v2/docs/赵蕊-第4周-变更涟漪评审记录.md、proposal.md、周报告.md |
| 2026-11-26 | Claude Code | 赵蕊 | 【赵蕊】proposal 0.5-diff 0.6 S11呈现口径#7乙案裁定回填 → v2/specs/proposal.md |
| 2026-11-26 | Claude Code | 赵蕊 | 【赵蕊】proposal 0.6全组追认通过登记 → v2/specs/proposal.md、评审记录.md |
| 2026-11-26 | Claude Code | 方赫 | 【方赫】design 0.7-diff 0.6 S11 #7乙案个人日报版式局部翻案 → v2/specs/design.md |
| 2026-11-26 | Claude Code | 方赫 | 【方赫】design 0.6翻案签认 → v2/specs/design.md |
| 2026-11-26 | Claude Code | 于悦 | 【于悦】tasks 0.1.3排TK-V2-905/906（issue #24第3条）→ v2/specs/tasks.md |
| 2026-11-26 | Claude Code | 于悦 | 【于悦】考勤条目置顶修复打卡夹在提交中间：group_by_member把考勤抽出置顶 → v2/src/smart_daily_v2/reports/generator.py |
| 2026-11-26 | Claude Code | 于悦 | 【于悦】按design 0.6落地个人日报双块呈现TK-V2-905：build_personal_report改今日考勤独立块+工作记录列表 → v2/src/smart_daily_v2/reports/generator.py、tests/ |
| 2026-11-26 | Claude Code | 方赫 | 【方赫】design 0.6/乙案双块代码落地后真推送验证（跳过老师邮箱） |
| 2026-11-26 | Claude Code | 杨佳莹 | 配置管理员产出②：打附注tag v2-superpowers指向d5715d7并写发布记录 → v2/docs/杨佳莹-第4周-v2-superpowers打tag与发布记录.md |
| 2026-11-26 | Claude Code | 杨佳莹 | 测试工程师产出②配套：代起草第4周思考题两问 → v2/docs/杨佳莹-第4周思考题.md |
| 2026-11-26 | Claude Code | 杨佳莹 | 测试工程师产出①签认收口：回归测试报告状态改☑并追加§8复核记录，同步总结报告docx 4处tag表述 → v2/docs/testing/回归测试全量执行报告-第4周.md、桌面docx |
| 2026-11-26 | Claude Code | 杨佳莹 | 本机配置v2/.env与用户级环境变量：替换飞书凭证、加考勤成员映射、清旧变量，dry-run验证4人日报含考勤行 |
| 2026-11-26 | Claude Code | 杨佳莹 | 真推送2026-11-26日报（跳过老师邮箱）：飞书群+4成员邮箱，落库于悦11/方赫6/杨佳莹1/赵蕊9 |
| 2026-11-26 | Claude Code | 赵蕊 | 【赵蕊】核验范围说明：本人产出文档集中签认清单 |
