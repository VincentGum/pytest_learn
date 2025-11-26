import pytest


@pytest.mark.unit
def test_dynamic_param_size(size):
    # 动态参数生成：通过 pytest_generate_tests 注入 size
    assert size in (1, 2, 3)
