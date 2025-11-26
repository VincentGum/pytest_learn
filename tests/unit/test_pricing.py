import math
import logging
import pytest

from app.models import Item, User
from app.pricing import calculate_total, apply_tax, calculate_subtotal


# 使用标记对用例分层
@pytest.mark.unit
@pytest.mark.parametrize(
    "items,user,region,expect",
    [
        # 参数化并提供可读 ids
        ([Item("A", 10)], User("U1", "basic"), "CN", round(10 * 1.13, 2)),
        ([Item("A", 10), Item("B", 5)], User("U2", "vip"), "US", round((15 * (1 - 0.10)) * 1.07, 2)),
    ],
    ids=["basic-CN", "vip-US"],
)
def test_calculate_total_param(items, user, region, expect, log_capture):
    # 断言重写：直接使用 assert，能打印表达式值与差异
    total = calculate_total(items, user, region)
    assert total == expect
    # caplog：捕获日志并断言
    assert any("subtotal" in r.message for r in log_capture.records)


@pytest.mark.unit
def test_apply_tax_branching():
    # 展示容器差异与富失败信息
    amounts = [10, 20]
    taxed_cn = [apply_tax(a, "CN") for a in amounts]
    taxed_us = [apply_tax(a, "US") for a in amounts]
    assert taxed_cn != taxed_us


@pytest.mark.unit
def test_membership_and_coupon(monkeypatch):
    # monkeypatch：打补丁环境变量，影响折扣逻辑
    monkeypatch.setenv("COUPON_CODE", "SAVE5")
    total = calculate_total([Item("A", 100)], User("U", "vip"), "CN")
    # 折扣 10% + 5%，税 13%
    assert math.isclose(total, round((100 * 0.85) * 1.13, 2))


@pytest.mark.unit
def test_subtotal_logging(caplog):
    caplog.set_level(logging.INFO)
    s = calculate_subtotal([Item("A", 1), Item("B", 2)])
    assert s == 3
    assert "subtotal" in caplog.text


@pytest.mark.unit
@pytest.mark.skip(reason="演示跳过：条件未满足")
def test_skip_demo():
    assert True


@pytest.mark.unit
@pytest.mark.xfail(reason="演示预期失败：税率逻辑变更中", strict=False)
def test_xfail_demo():
    assert apply_tax(100, "EU") == 110.0
