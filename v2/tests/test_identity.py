"""身份归并测试。

覆盖合约：normalize_key(raw)→str, normalize_members(raws)→dict[str, list[str]]

依据 v2/README.md §2：归属键统一 strip()+casefold()，单点归一化，下游禁止二次归一化。
"""

import pytest

from smart_daily_v2.identity import normalize_key, normalize_members


class TestNormalizeKey:
    """单一身份键的 strip+casefold。"""

    def test_same_person_case_insensitive(self) -> None:
        # ① 同一人不同大小写归并为同一键
        assert normalize_key("ZhaoRui715") == normalize_key("zhaorui715")

    def test_leading_trailing_whitespace(self) -> None:
        # ② 首尾空格不影响归并
        assert normalize_key(" zhaorui715 ") == normalize_key("zhaorui715")

    def test_different_people_not_merged(self) -> None:
        # ③ 不同人不得误并
        assert normalize_key("zhaorui715") != normalize_key("zhaorui716")

    def test_empty_string_normalizes_to_empty(self) -> None:
        # ④ 空字符串经 strip+casefold 仍为空串
        assert normalize_key("") == ""
        assert normalize_key("   ") == ""

    def test_none_raises_type_error(self) -> None:
        # ④ None 表示调用方传入了无身份输入，应明确拒绝
        with pytest.raises(TypeError):
            normalize_key(None)  # type: ignore[arg-type]

    def test_chinese_name_vs_login_dont_merge(self) -> None:
        # ⑤ 中文全名与拼音/登录名不应互相归并
        assert normalize_key("赵蕊") != normalize_key("zhaorui")


class TestNormalizeMembers:
    """批量归并：不同原始身份→同一键时合并列表。"""

    def test_merge_case_and_whitespace_variants(self) -> None:
        raws = ["ZhaoRui715", " zhaorui715 ", "zhaorui716"]
        result = normalize_members(raws)

        assert len(result) == 2  # 两个不同人
        assert "zhaorui715" in result
        assert "zhaorui716" in result

        # 归并后的原始列表应包含两个变体
        merged = result["zhaorui715"]
        assert "ZhaoRui715" in merged
        assert " zhaorui715 " in merged

    def test_empty_input(self) -> None:
        assert normalize_members([]) == {}

    def test_none_in_list_raises(self) -> None:
        with pytest.raises(TypeError):
            normalize_members(["ok", None])  # type: ignore[list-item]
