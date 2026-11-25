"""飞书考勤采集源（TK-V2-901，第 4 周变更涟漪）。

契约来源：design 0.7-diff 0.4 §3/§4-1/§4-2/§6、tasks TK-V2-901、proposal C11。
零复制 G5：不 import、不复制 v1 任一模块；沿用 v2 的 httpx 直连 + from_env() 工厂
（与 feishu_tasks.py / feishu_chat.py 同构，ADR-101/103 继承）。

范围与未决（B#5 / B#6，U13 前置未齐 → 真实接口联调项留 ☐，本模块只以桩/夹具验收）：
- **B#5**：飞书应用「导出打卡数据」权限与英文 scope 标识待配置侧后台核对；未开通
  则接口返回 code=1220005，本模块按既有中文提示封装抛 SourceUnavailableError、
  由独立采集支路留痕，不中断主流程。
- **B#6**：接口按 employee_type 返回 user_id / employee_no，而 v2 成员键是
  normalize_key(sender_name/creator_name) 的姓名键，两者不是同一标识。映射来源
  （配置表或通讯录关联）待配置侧确认，**不假定同名即同人**：本模块用注入的
  member_map（user_id → 姓名）转换，未命中则回落 user_id 原值并在 detail 标注
  「成员未映射」，不静默丢弃、不擅自归并。
- 接口选型：POST /open-apis/attendance/v1/user_tasks/query（查询打卡结果）。
  **明确不采用** user_flows/query（批量查询打卡流水）与 user_flows/:id，后者返回
  定位地址 / WiFi 信息 / 设备 ID，违反个人信息最小化硬约束（ADR-105）。
- 个人信息最小化：只取「出勤状态 + 上班/下班打卡时刻 + record_id」，不采定位、
  打卡图像、设备信息、WiFi 信息；出勤状态与 record_id 内嵌 detail 供 C11 对账。
- occurred_at：取上班打卡时间，缺上班卡回落下班卡，两者皆无不计入；归属日按
  local_date(occurred_at)，闭区间 [since, until] 过滤（design §4-2 定案）。
- 归一化：直接返回 WorkItem，经 normalize() 幂等放行，编排层不二次归一化（G7）。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from smart_daily_v2.config import load_config
from smart_daily_v2.identity import normalize_key
from smart_daily_v2.models import WorkItem, local_date
from smart_daily_v2.sources.base import SourceUnavailableError, WorkSource


def _fetch_tenant_access_token(app_id: str, app_secret: str, api_base: str) -> str:
    url = f"{api_base.rstrip('/')}/auth/v3/tenant_access_token/internal"
    try:
        response = httpx.post(
            url,
            json={"app_id": app_id, "app_secret": app_secret},
            timeout=15,
        )
    except httpx.HTTPError as exc:
        raise SourceUnavailableError("feishu_attendance", f"token 请求失败：{exc}") from exc
    if not response.is_success:
        raise SourceUnavailableError(
            "feishu_attendance", f"token 请求失败（HTTP {response.status_code}）"
        )
    payload = response.json()
    if payload.get("code") != 0:
        raise SourceUnavailableError(
            "feishu_attendance",
            f"token 接口错误 code={payload.get('code')}：{payload.get('msg', '')}",
        )
    token = payload.get("tenant_access_token", "")
    if not token:
        raise SourceUnavailableError(
            "feishu_attendance", "token 响应缺少 tenant_access_token"
        )
    return token


@dataclass(frozen=True)
class FeishuAttendanceSource(WorkSource):
    feishu_app_id: str
    feishu_app_secret: str
    feishu_api: str
    member_map: Mapping[str, str] = field(default_factory=dict)
    employee_type: str = "employee_id"

    name = "feishu_attendance"

    @classmethod
    def from_env(cls) -> FeishuAttendanceSource:
        config = load_config()
        return cls(
            feishu_app_id=config.feishu_app_id,
            feishu_app_secret=config.feishu_app_secret,
            feishu_api=config.feishu_api,
        )

    def collect(
        self,
        *,
        since: datetime,
        until: datetime,
        author: str | None = None,
    ) -> list[WorkItem]:
        missing = [
            name
            for name, value in (
                ("FEISHU_APP_ID", self.feishu_app_id),
                ("FEISHU_APP_SECRET", self.feishu_app_secret),
            )
            if not value
        ]
        if missing:
            raise SourceUnavailableError(
                self.name, f"凭证未配置：{', '.join(missing)}"
            )

        token = _fetch_tenant_access_token(
            self.feishu_app_id, self.feishu_app_secret, self.feishu_api
        )
        url = f"{self.feishu_api.rstrip('/')}/attendance/v1/user_tasks/query"
        headers = {
            "X-Application-Id": self.feishu_app_id,
            "X-Application-Secret": self.feishu_app_secret,
            "Authorization": f"Bearer {token}",
        }
        params = {"employee_type": self.employee_type}
        body = {
            "user_ids": list(self.member_map),
            "check_date_from": since.strftime("%Y%m%d"),
            "check_date_to": until.strftime("%Y%m%d"),
        }

        try:
            response = httpx.post(
                url, json=body, params=params, headers=headers, timeout=15
            )
        except httpx.HTTPError as exc:
            raise SourceUnavailableError(self.name, f"请求失败：{exc}") from exc
        if not response.is_success:
            raise SourceUnavailableError(
                self.name, f"请求失败（HTTP {response.status_code}）"
            )
        payload = response.json()
        code = payload.get("code", 0)
        if code != 0:
            raise SourceUnavailableError(
                self.name,
                f"飞书考勤接口错误 code={code}：{payload.get('msg', '')}",
            )

        data = payload.get("data") or {}
        user_tasks = data.get("user_task_results") or []

        items: list[WorkItem] = []
        for task in user_tasks:
            user_id = task.get("user_id", "")
            for record in task.get("records") or []:
                occurrence = _pick_occurred_at(record)
                if occurrence is None:
                    continue
                if not (since <= occurrence <= until):
                    continue

                record_id = str(record.get("record_id", ""))
                status = str(record.get("status", ""))
                mapped = self.member_map.get(user_id)
                if mapped is None:
                    member = normalize_key(user_id)
                    mapping_note = "成员未映射"
                else:
                    member = normalize_key(mapped)
                    mapping_note = ""

                detail_parts = [f"出勤状态：{status}"]
                if mapping_note:
                    detail_parts.append(mapping_note)
                detail_parts.append(f"record_id: {record_id}")
                detail = "\n".join(detail_parts)

                items.append(
                    WorkItem(
                        record_id=record_id,
                        source=self.name,
                        member=member,
                        kind="attendance",
                        title=f"考勤：{status}",
                        detail=detail,
                        occurred_at=occurrence,
                        local_day=local_date(occurrence),
                    )
                )
        return items


def _pick_occurred_at(record: Mapping[str, object]) -> datetime | None:
    """取上班打卡时刻，缺则回落下班卡，两者皆无返回 None（design §4-2 定案）。"""
    for key in ("check_time", "off_time"):
        raw = record.get(key)
        if raw:
            return datetime.fromisoformat(str(raw))
    return None
