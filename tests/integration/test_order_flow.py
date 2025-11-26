import time
import pytest

from common.factories import make_cart, make_items, make_user
from app.service import add_items, checkout


@pytest.mark.integration
def test_checkout_flow_with_temp_db(temp_db, monkeypatch):
    # tmp_path 夹具：临时文件系统隔离
    before = temp_db.read_text()
    assert before == "init"

    # monkeypatch：稳定时间戳，提高测试确定性
    monkeypatch.setattr(time, "time", lambda: 1700000000)

    cart = add_items(make_cart(), make_items(3))
    order = checkout(cart, make_user("U100", tier="vip"), region="US")

    # 容器断言与字典键存在
    assert len(order.items) == 3
    assert order.meta["ts"] == str(1700000000)
    assert order.meta["region"] == "US"

    # 写入并清理通过 yield 完成
    temp_db.write_text("ok")
    assert temp_db.read_text() == "ok"
