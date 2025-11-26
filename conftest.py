import os
import sys
import logging
from typing import List

import pytest

# 激活自定义插件
pytest_plugins = [
    "common.plugins.example_plugin",
    "common.plugins.advanced_plugin"
]


def pytest_addoption(parser):
    parser.addoption("--env", action="store", default="dev", help="运行环境")


@pytest.fixture(scope="session")
def env(pytestconfig):
    return pytestconfig.getoption("--env")


@pytest.fixture(scope="function")
def set_coupon(monkeypatch):
    monkeypatch.setenv("COUPON_CODE", "SAVE5")
    yield
    monkeypatch.delenv("COUPON_CODE", raising=False)


@pytest.fixture(scope="function")
def log_capture(caplog):
    logger = logging.getLogger("app.pricing")
    caplog.set_level(logging.INFO, logger=logger.name)
    return caplog


def pytest_generate_tests(metafunc):
    if "size" in metafunc.fixturenames:
        metafunc.parametrize("size", [1, 2, 3], ids=["small", "medium", "large"])


@pytest.fixture(scope="function")
def temp_db(tmp_path):
    p = tmp_path / "db.txt"
    p.write_text("init")
    yield p
    p.unlink(missing_ok=True)


@pytest.fixture
def ensure_path_in_sys(tmp_path):
    old = list(sys.path)
    sys.path.append(str(tmp_path))
    yield
    sys.path = old
