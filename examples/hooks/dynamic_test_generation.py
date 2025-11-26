# 动态测试生成与参数化 Hook 示例
import pytest
import inspect
import json
import os
import importlib.util
from typing import List, Dict, Any, Callable, Optional, Union

# 测试配置管理器
class TestConfigManager:
    def __init__(self):
        self.test_configs = {}
        self.param_sets = {}
    
    def load_config_from_file(self, file_path: str):
        """从文件加载测试配置"""
        if not os.path.exists(file_path):
            print(f"警告: 配置文件不存在: {file_path}")
            return False
        
        try:
            with open(file_path, 'r') as f:
                config = json.load(f)
                
                if "test_configs" in config:
                    self.test_configs.update(config["test_configs"])
                if "param_sets" in config:
                    self.param_sets.update(config["param_sets"])
            return True
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return False
    
    def get_test_config(self, test_name: str) -> Optional[Dict[str, Any]]:
        """获取测试配置"""
        return self.test_configs.get(test_name)
    
    def get_param_set(self, param_set_name: str) -> Optional[List[Any]]:
        """获取参数集"""
        return self.param_sets.get(param_set_name)

# 全局配置管理器实例
_config_manager = TestConfigManager()

def pytest_configure(config):
    """配置pytest时加载测试配置"""
    # 尝试从多个位置加载配置
    config_paths = [
        os.path.join(os.getcwd(), "test_configs.json"),
        os.path.join(os.getcwd(), "configs", "test_configs.json")
    ]
    
    for path in config_paths:
        if _config_manager.load_config_from_file(path):
            print(f"已加载测试配置: {path}")
    
    # 添加自定义标记
    config.addinivalue_line(
        "markers", 
        "dynamic_params(param_set_name): 标记测试使用动态参数集"
    )
    
    config.addinivalue_line(
        "markers", 
        "config_based: 标记测试使用基于配置的参数化"
    )

def pytest_generate_tests(metafunc):
    """动态生成测试参数"""
    # 获取测试名称
    test_name = metafunc.definition.nodeid.split("::")[-1]
    
    # 检查是否有dynamic_params标记
    dynamic_params_marker = metafunc.definition.get_closest_marker("dynamic_params")
    if dynamic_params_marker and dynamic_params_marker.args:
        param_set_name = dynamic_params_marker.args[0]
        param_set = _config_manager.get_param_set(param_set_name)
        
        if param_set:
            # 获取测试函数的参数名
            sig = inspect.signature(metafunc.function)
            param_names = list(sig.parameters.keys())
            
            if param_names:
                # 使用第一个参数名作为参数化的目标
                param_name = param_names[0]
                
                # 检查参数值类型以确定如何参数化
                if all(isinstance(item, dict) for item in param_set):
                    # 如果是字典列表，使用ids和参数名
                    ids = [str(item.get("id", i)) for i, item in enumerate(param_set)]
                    metafunc.parametrize(param_name, param_set, ids=ids)
                    print(f"为测试 {test_name} 使用动态参数集 {param_set_name}")
                else:
                    # 简单值列表
                    ids = [str(item) for item in param_set]
                    metafunc.parametrize(param_name, param_set, ids=ids)
                    print(f"为测试 {test_name} 使用动态参数集 {param_set_name}")
    
    # 检查是否有config_based标记
    config_based_marker = metafunc.definition.get_closest_marker("config_based")
    if config_based_marker:
        # 尝试从配置中获取该测试的配置
        test_config = _config_manager.get_test_config(test_name)
        
        if test_config and "params" in test_config:
            params = test_config["params"]
            
            # 参数化测试
            for param_name, param_values in params.items():
                if param_name in metafunc.fixturenames:
                    # 生成参数ID
                    ids = [str(val) for val in param_values]
                    metafunc.parametrize(param_name, param_values, ids=ids)
                    print(f"为测试 {test_name} 的参数 {param_name} 配置参数化")
    
    # 检查是否有需要动态生成的测试
    if hasattr(metafunc.function, "_generate_tests_from"):
        # 从指定数据源生成测试
        data_source = metafunc.function._generate_tests_from
        
        # 根据数据源类型处理
        if isinstance(data_source, str) and os.path.exists(data_source):
            # 从文件生成测试
            try:
                with open(data_source, 'r') as f:
                    test_data = json.load(f)
                    
                    if isinstance(test_data, list):
                        param_names = list(inspect.signature(metafunc.function).parameters.keys())
                        if param_names:
                            param_name = param_names[0]
                            ids = [str(item.get("id", i)) for i, item in enumerate(test_data)]
                            metafunc.parametrize(param_name, test_data, ids=ids)
                            print(f"从文件 {data_source} 为测试 {test_name} 生成测试参数")
            except Exception as e:
                print(f"从文件生成测试失败: {e}")

# 用于装饰测试函数的装饰器
def generate_tests_from(source):
    """
    装饰器，指定测试函数从何处生成测试数据
    
    示例:
    @generate_tests_from('test_data.json')
    def test_with_dynamic_data(data_item):
        assert data_item['expected'] == some_function(data_item['input'])
    """
    def decorator(func):
        func._generate_tests_from = source
        return func
    return decorator

@pytest.fixture(scope="session")
def test_config_manager():
    """提供测试配置管理器的fixture"""
    return _config_manager

@pytest.fixture(scope="function")
def dynamic_test_data(request):
    """根据测试名称提供动态测试数据"""
    test_name = request.node.nodeid.split("::")[-1]
    test_config = _config_manager.get_test_config(test_name)
    
    if test_config and "test_data" in test_config:
        return test_config["test_data"]
    
    return None
