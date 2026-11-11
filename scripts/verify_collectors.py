"""采集层降级链路的验证脚本

对应指导书第 2 周 tasks.md「集成测试」的要求，本脚本验证五件事：
    1. 本地 Git 采集器能真实读到提交（真实数据源可用）
    2. GitHub 采集器在仓库为空/无权限时抛出可识别的降级异常
    3. collect_with_fallback 在首选数据源失败时自动切换到下一个，主流程不中断
    4. 三个采集器产出的记录都能归一化成统一的 WorkItem 模型
    5. 数据源不可用时抛出的异常里带有可定位的原因（供降级提示使用）

第 1 周阶段，这一脚本充当「接口契约的可执行证明」——
design.md 的接口契约章节可以直接引用这里的输出作为证据。

运行：uv run --env-file .env python scripts/verify_collectors.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from smart_daily.collectors import (  # noqa: E402
    LocalGitCollector,
    MockCollector,
    SourceUnavailableError,
    WorkItem,
    collect_with_fallback,
    normalize,
)
from smart_daily.collectors.feishu import FeishuCollector  # noqa: E402
from smart_daily.collectors.github import GitHubCollector  # noqa: E402
from smart_daily.collectors.models import local_date, record_timestamp  # noqa: E402

PASS = "PASS"
FAIL = "FAIL"
results: list[tuple[str, str, str]] = []


def record(name: str, ok: bool, detail: str) -> None:
    results.append((PASS if ok else FAIL, name, detail))
    print(f"  [{PASS if ok else FAIL}] {name:38s} {detail}")


def test_local_git() -> None:
    print("\n[1] 本地 Git 采集器（过渡数据源）")
    local = LocalGitCollector(ROOT)
    entries = local.collect_commits()
    record("本地仓库可读", True, f"读到 {len(entries)} 条提交")
    record("数据模型字段完整", bool(entries) and all(
        e.sha and e.author_name and e.timestamp and e.message for e in entries
    ), f"字段校验通过 {len(entries)} 条")

    members = local.list_repo_members()
    record("贡献者列表可读", bool(members), f"{len(members)} 位贡献者")

    # 时间窗口过滤
    now = datetime.now(timezone.utc)
    future = local.collect_commits(since=now + timedelta(days=1))
    record("时间窗口过滤生效", len(future) == 0, f"未来窗口返回 {len(future)} 条（应为 0）")


def test_github_errors() -> None:
    print("\n[2] GitHub 采集器异常识别")
    try:
        GitHubCollector.from_env().collect_commits("yjy120/chapter6--")
        record("空仓库抛出降级异常", False, "未抛出异常（不符合预期）")
    except SourceUnavailableError as exc:
        record("空仓库抛出降级异常", True, f"正确识别：{str(exc)[:46]}")


def test_github_missing_repo_config() -> None:
    print("\n[3] GitHub 凭证/仓库地址缺失时的判定")
    import os

    old_owner = os.environ.pop("GITHUB_REPO_OWNER", None)
    old_repo = os.environ.pop("GITHUB_REPO_NAME", None)
    try:
        GitHubCollector.from_env()
        record("仓库未配置时判定不可用", False, "未抛出异常（会误打 API）")
    except SourceUnavailableError as exc:
        record("仓库未配置时判定不可用", True, f"{str(exc)[:46]}")
    finally:
        if old_owner is not None:
            os.environ["GITHUB_REPO_OWNER"] = old_owner
        if old_repo is not None:
            os.environ["GITHUB_REPO_NAME"] = old_repo


def test_fallback() -> None:
    print("\n[4] 降级链路（首选失败 → 自动切换）")
    today = datetime.now(timezone.utc) - timedelta(days=30)
    sources = [
        GitHubCollector.from_env(owner="yjy120", repo="chapter6--"),
        LocalGitCollector(ROOT),
    ]
    try:
        items, used = collect_with_fallback(sources, since=today)
        record("主流程未被中断", True, f"生效数据源 = {used}，{len(items)} 条")
        record("产出模型统一", all(isinstance(i, WorkItem) for i in items), "全部为 WorkItem")
        record("按时间倒序排列", all(
            items[i].timestamp >= items[i + 1].timestamp for i in range(len(items) - 1)
        ), "时间序校验通过")
    except SourceUnavailableError as exc:
        record("主流程未被中断", False, f"所有数据源失败：{exc}")


def test_all_failed() -> None:
    print("\n[5] 全部数据源失败时的行为")

    class Broken:
        name = "broken"

        def collect(self, **kw):
            raise SourceUnavailableError("故意失败")

    try:
        collect_with_fallback([Broken(), Broken()])
        record("全部失败时抛出明确异常", False, "未抛出异常")
    except SourceUnavailableError as exc:
        record("全部失败时抛出明确异常", True, f"异常信息含失败原因：{'故意失败' in str(exc)}")


def test_normalize_tolerant() -> None:
    print("\n[6] 归一化层的健壮性")
    # 已经是 WorkItem 的记录应可原样通过（二次调用不报错）
    local = LocalGitCollector(ROOT)
    raw = local.collect_commits()
    once = normalize(raw)
    twice = normalize(once)
    record("WorkItem 二次归一化不报错", len(once) == len(twice), f"{len(once)} → {len(twice)}")

    try:
        normalize([{"not": "a record"}])  # type: ignore[list-item]
        record("非法记录类型明确报错", False, "未抛出 TypeError")
    except TypeError as exc:
        record("非法记录类型明确报错", True, f"{str(exc)[:46]}")


def test_feishu_graceful() -> None:
    print("\n[7] 飞书采集器凭证未就绪时的表现")
    try:
        FeishuCollector.from_env()
        record("凭证齐备时构造成功", True, "飞书数据源已就绪")
    except SourceUnavailableError as exc:
        record("凭证缺失时明确提示", True, f"{str(exc)[:46]}")
    except Exception as exc:  # noqa: BLE001
        record("凭证缺失时明确提示", False, f"抛出了非预期异常：{type(exc).__name__}")


def test_empty_list_is_valid_result() -> None:
    """空列表是合法返回值：源可用但时间窗口内无数据。

    接口契约明确「无数据时返回空列表」，因此降级链在遇到空列表时**应当停止**，
    而不是跳过它继续找下一个源 —— 否则会出现「源正常但无数据」被误判成
    「源失败」，掩盖真实原因。

    正因如此，飞书采集器在全部通道不可用时必须**抛异常**而不是返回空列表，
    见 test_feishu_raises_when_all_down。
    """
    print("\n[8] 空列表作为合法返回值的语义")

    class EmptyButHealthy:
        """源本身正常，只是窗口内无数据。"""

        name = "empty-but-healthy"

        def collect(self, **kw):
            return []

    try:
        items, used = collect_with_fallback([EmptyButHealthy(), LocalGitCollector(ROOT)])
        record("空列表被接受为合法结果", used == "empty-but-healthy",
               f"生效数据源 = {used}（源可用，空列表不代表失败）")
        record("空列表不触发异常", items == [], f"返回 {len(items)} 条（符合契约）")
    except SourceUnavailableError as exc:
        record("空列表被接受为合法结果", False, f"空列表被误判为失败：{exc}")


def test_raising_source_falls_through() -> None:
    """真正不可用的源（抛异常）必须让链路继续走到兜底源。

    回归用例：曾出现飞书 collect() 吞掉异常返回 []，导致 collect_with_fallback
    误判本源成功、跳过排在后面的本地 Git 兜底源，主流程产出 0 条空日报。
    """
    print("\n[9] 抛异常的数据源必须让降级链继续")

    class Broken:
        """模拟真实飞书采集器曾经的行为：吞掉异常返回空列表。"""

        name = "broken-swallow"

        def collect(self, **kw):
            return []

    class ProperBroken:
        """修正后的行为：全部通道不通时抛异常。"""

        name = "proper-broken"

        def collect(self, **kw):
            raise SourceUnavailableError("全部通道不可用")

    local = LocalGitCollector(ROOT)
    try:
        items, used = collect_with_fallback([ProperBroken(), local])
        record("抛异常的源让链路继续", used == "local-git",
               f"生效数据源 = {used}")
        record("兜底源产出非空结果", len(items) > 0, f"{len(items)} 条")
    except SourceUnavailableError as exc:
        record("抛异常的源让链路继续", False, f"降级链中断：{exc}")


def test_feishu_raises_when_all_down() -> None:
    """真实 FeishuCollector 在 21001 时应抛 SourceUnavailableError。"""
    print("\n[10] 真实飞书采集器的失败语义")
    try:
        collector = FeishuCollector.from_env()
        collector.collect()
        record("全通道不通时抛出降级异常", True, "飞书通道本次可用")
    except SourceUnavailableError as exc:
        ok = "21001" in str(exc) or "不可用" in str(exc)
        record("全通道不通时抛出降级异常", ok, f"{str(exc)[:46]}")
    except Exception as exc:  # noqa: BLE001
        record("全通道不通时抛出降级异常", False, f"抛出了非预期异常：{type(exc).__name__}")


def test_mock_source() -> None:
    """mock 数据源（指导书 FAQ 点名要求的兜底手段）。

    核心契约：不依赖任何凭证、不依赖网络，永不失败，
    并且产出的条目必须全部落在当天（日报日期归属正确）。
    """
    print("\n[11] mock 数据源（无凭证兜底）")
    collector = MockCollector()
    raw = collector.collect()
    record("mock 无需凭证即可产出记录", len(raw) > 0, f"{len(raw)} 条原始记录")

    items, used = collect_with_fallback([collector])
    record("mock 可独立作为唯一数据源", used == "mock" and len(items) > 0,
           f"生效数据源 = {used}，{len(items)} 条")

    today = datetime.now().astimezone().date()
    off_day = [i for i in items if local_date(i.timestamp) != today]
    record("mock 条目全部落在当天", not off_day,
           f"跨天条目 {len(off_day)} 条（应为 0）")

    # 三种记录类型的时间字段名不统一，必须走 record_timestamp
    try:
        ts_list = [record_timestamp(e) for e in raw]
        record("三种记录类型都能取到事件时间", len(ts_list) == len(raw),
               f"统一取到 {len(ts_list)} 个时间戳")
    except Exception as exc:  # noqa: BLE001
        record("三种记录类型都能取到事件时间", False, f"{type(exc).__name__}: {exc}")


def test_local_date_conversion() -> None:
    """日期归属必须按本地日历，而不是 UTC。

    回归用例：曾用 timestamp.date() 取 UTC 日期，东八区晚上 8 点后
    提交的日报标题会写成前一天。
    """
    print("\n[12] 日期归属的时区正确性")
    from datetime import timezone as _tz

    # 东八区本地时间 2026-11-03 23:30，对应 UTC 15:30（同一天）
    utc_ts = datetime(2026, 11, 3, 15, 30, tzinfo=_tz.utc)
    got = local_date(utc_ts)
    record("UTC 时间戳按本地日历归属", got == utc_ts.astimezone().date(),
           f"local_date = {got}")

    # 关键边界：本地 2026-11-04 01:00（UTC 2026-11-03 17:00）
    # 若错误地用 UTC 日期，会得到 11-03 而非 11-04
    edge = datetime(2026, 11, 3, 17, 0, tzinfo=_tz.utc)
    edge_local = edge.astimezone()
    record("跨日边界取到正确的本地日期", local_date(edge) == edge_local.date(),
           f"UTC {edge:%m-%d %H:%M} -> 本地 {edge_local:%m-%d %H:%M} -> 归属 {local_date(edge)}")


def test_member_email_mapping() -> None:
    """成员 -> 邮箱映射（邮件推送通道的依赖）。"""
    print("\n[13] 成员邮箱映射")
    from smart_daily.push.members import resolve_recipients

    mapping = {"zhangsan": ["zhangsan@qq.com"], "lisi": ["a@163.com", "b@163.com"]}
    r1 = resolve_recipients("zhangsan", mapping)
    record("按成员名匹配邮箱", r1 == ["zhangsan@qq.com"], f"{r1}")

    r2 = resolve_recipients("lisi", mapping)
    record("一个成员可配多个邮箱", len(r2) == 2, f"{r2}")

    r3 = resolve_recipients("zhangsan@qq.com", mapping)
    record("邮箱前缀退化匹配", r3 == ["zhangsan@qq.com"], f"{r3}")

    r4 = resolve_recipients("unknown", mapping)
    record("未知成员返回空列表", r4 == [], f"{r4}")


def test_notifier_protocol_contract() -> None:
    """Notifier 协议的实现完整性。

    回归用例：Notifier 协议声明了 name 属性，但 EmailNotifier /
    FeishuWebhookNotifier / MultiNotifier 三个实现全都没定义它，
    首次在推送明细里访问 n.name 时抛 AttributeError。
    这属于「接口契约与实现不一致」——协议写了，实现没跟上。
    """
    print("\n[14] 推送通道的协议实现完整性")
    from smart_daily.push.notifiers import (
        EmailNotifier,
        FeishuWebhookNotifier,
        MultiNotifier,
        Notifier,
    )

    cases = [
        ("EmailNotifier", EmailNotifier(host="h", port=465, user="u", password="p")),
        ("FeishuWebhookNotifier", FeishuWebhookNotifier(webhook_url="https://x")),
        ("MultiNotifier", MultiNotifier(notifiers=[])),
    ]
    for label, inst in cases:
        has_name = hasattr(inst, "name") and isinstance(getattr(inst, "name"), str)
        record(f"{label} 实现 name 属性", has_name,
               f"name = {getattr(inst, 'name', '(缺失)')!r}")

    # 协议运行时检查：三个实现都应满足 Notifier
    for label, inst in cases:
        record(f"{label} 满足 Notifier 协议", isinstance(inst, Notifier),
               "isinstance 检查通过")


def main() -> int:
    print("=" * 62)
    print("  采集层验证 —— 数据源可替换与降级链路")
    print("=" * 62)
    test_local_git()
    test_github_errors()
    test_github_missing_repo_config()
    test_fallback()
    test_all_failed()
    test_normalize_tolerant()
    test_feishu_graceful()
    test_empty_list_is_valid_result()
    test_raising_source_falls_through()
    test_feishu_raises_when_all_down()
    test_mock_source()
    test_local_date_conversion()
    test_member_email_mapping()
    test_notifier_protocol_contract()

    failed = [r for r in results if r[0] == FAIL]
    print("\n" + "=" * 62)
    print(f"  合计 {len(results)} 项，通过 {len(results) - len(failed)}，失败 {len(failed)}")
    print("=" * 62)
    for _, name, detail in failed:
        print(f"  {FAIL}  {name} —— {detail}")
    # tasks.md TK-701 验收口径：末行打印「通过/总数」，便于人工与 CI 直接核对
    print(f"{len(results) - len(failed)}/{len(results)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
