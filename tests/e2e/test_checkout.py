import json
import pytest

from common.factories import make_cart, make_items, make_user
from app.service import add_items, checkout, print_receipt


@pytest.mark.e2e
def test_full_checkout_and_receipt(capsys, set_coupon):
    # e2e：端到端，串联多个组件
    cart = add_items(make_cart(), make_items(2))
    order = checkout(cart, make_user("U200", tier="vip"), region="CN")
    text = print_receipt(order)

    # capsys：捕获标准输出
    out = capsys.readouterr().out.strip()
    assert out == text

    payload = json.loads(text)
    # 断言重写：展示 dict 差异
    assert payload["user"] == "U200"
    assert payload["count"] == 2
    assert payload["region"] == "CN"
