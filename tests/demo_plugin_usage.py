import pytest
import os


@pytest.mark.unit
def test_basic_plugin_functionality(feature_flags):
    """测试插件的基本功能 - 特性标志"""
    # 验证feature_flags fixture正常工作
    assert isinstance(feature_flags, dict)
    # 无论是否设置了特性标志，都应该返回字典


@pytest.mark.unit
def test_api_client_fixture(api_client):
    """测试API客户端fixture"""
    # 验证API客户端功能
    response = api_client.get("/test")
    assert response["status"] == "success"
    assert "version" in response
    
    # 验证POST请求
    post_response = api_client.post("/create", data={"name": "test"})
    assert post_response["status"] == "created"
    
    # 验证调用记录
    assert len(api_client.calls) == 2
    assert api_client.calls[0][0] == "GET"
    assert api_client.calls[1][0] == "POST"


@pytest.mark.require_db
def test_require_db_marker():
    """测试require_db标记的功能"""
    # 这个测试在DB_AVAILABLE环境变量未设置时应该被跳过
    # 我们可以设置环境变量来测试通过情况
    # os.environ["DB_AVAILABLE"] = "true"
    # 但默认情况下应该被example_plugin中的pytest_runtest_setup钩子跳过
    pass


@pytest.mark.mock_api
def test_mock_api_marker(api_client):
    """测试mock_api标记与api_client的结合使用"""
    # 这个测试使用mock_api标记和api_client fixture
    response = api_client.get("/users")
    assert response["status"] == "success"


@pytest.mark.feature_flag
def test_feature_flag_usage(feature_flags):
    """测试特性标志的使用"""
    # 演示如何根据特性标志调整测试行为
    if feature_flags.get("new_ui"):
        print("使用新UI特性")
    else:
        print("使用旧UI特性")
    # 测试应该通过，无论特性标志如何设置
    assert True


@pytest.mark.slow
def test_slow_marker():
    """测试slow标记 - 在生产环境应该被跳过"""
    # 模拟慢测试
    import time
    time.sleep(0.1)  # 短暂睡眠模拟慢操作
    assert True


@pytest.mark.parametrize("test_input,expected", [
    (1, 2),
    (2, 3),
    (3, 4)
])
def test_parametrized_with_plugins(test_input, expected):
    """测试参数化测试与插件的结合"""
    # 验证参数化测试正常工作
    assert test_input + 1 == expected
    # 这个测试同时也会受到插件中的测试排序逻辑影响


# 测试插件的钩子功能
def test_plugin_hooks_effect():
    """间接测试插件钩子的效果"""
    # 这个测试的主要目的是验证它会被正确排序和处理
    # 具体的钩子效果会在测试执行过程中体现
    assert True
