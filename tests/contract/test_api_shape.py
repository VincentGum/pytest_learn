import pytest
from app.models import Order, User, Item

@pytest.mark.contract
def test_order_to_dict_shape():
    # 契约测试：字典结构与键的形状
    o = Order(user=User("U300", "basic"), items=[Item("X", 1.0)], amount=1.13)
    d = o.to_dict()
    assert set(d.keys()) == {"user", "items", "amount", "meta"}
    assert {"id", "tier"}.issubset(set(d["user"].keys()))
    assert isinstance(d["items"], list)


@pytest.mark.contract
@pytest.mark.xfail(reason="演示：预期失败，未来计划变更 meta 结构", strict=False)
def test_meta_contains_region():
    o = Order(user=User("U300", "basic"), items=[Item("X", 1.0)], amount=1.13)
    d = o.to_dict()
    # 目前 meta 默认不含 region，此处 xfail 作为规范占位
    assert "region" in d["meta"]
