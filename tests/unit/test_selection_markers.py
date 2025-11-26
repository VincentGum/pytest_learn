import pytest


@pytest.mark.unit
def test_unit_marker_selection():
    # 标记用例：可用 -m 选择运行
    assert True


@pytest.mark.slow
@pytest.mark.unit
def test_slow_mark_behavior():
    # 在 --env=prod 下通过插件自动跳过 slow
    assert True
