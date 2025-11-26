# 测试数据生成与清理插件
import pytest
import json
import os
import uuid
import tempfile
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

# 插件元数据
__version__ = "1.0.0"
__description__ = "测试数据生成与清理插件，支持自动管理测试数据生命周期"

def pytest_addoption(parser):
    """添加命令行参数选项"""
    group = parser.getgroup("test_data", "测试数据管理")
    group.addoption(
        "--data-dir",
        action="store",
        default=".test_data",
        dest="test_data_dir",
        help="测试数据存储目录"
    )
    group.addoption(
        "--keep-data",
        action="store_true",
        default=False,
        dest="keep_test_data",
        help="测试后保留数据（不清理）"
    )

def pytest_configure(config):
    """配置插件"""
    # 创建数据管理器实例
    data_dir = config.getoption("test_data_dir")
    keep_data = config.getoption("keep_test_data")
    
    config._test_data_manager = TestDataManager(data_dir, keep_data)
    
    # 添加插件信息到配置对象
    config.metadata["data_plugin"] = {
        "version": __version__,
        "data_dir": data_dir,
        "keep_data": keep_data
    }

def pytest_sessionfinish(session, exitstatus):
    """测试会话结束时清理数据"""
    if hasattr(session.config, "_test_data_manager"):
        session.config._test_data_manager.cleanup()

class TestDataManager:
    """测试数据管理器"""
    def __init__(self, data_dir: str, keep_data: bool = False):
        self.data_dir = data_dir
        self.keep_data = keep_data
        self.created_resources: List[Dict[str, Any]] = []
        self.temp_dirs: List[str] = []
        
        # 创建数据目录
        os.makedirs(data_dir, exist_ok=True)
        
        # 生成会话ID
        self.session_id = str(uuid.uuid4())[:8]
        print(f"测试数据管理器初始化完成 (会话ID: {self.session_id})")
    
    def create_temp_file(self, content: str = "", extension: str = ".txt") -> str:
        """创建临时文件"""
        filename = f"temp_{self.session_id}_{uuid.uuid4()[:8]}{extension}"
        filepath = os.path.join(self.data_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write(content)
        
        # 记录创建的资源
        self.created_resources.append({
            "type": "file",
            "path": filepath,
            "created_at": datetime.now().isoformat()
        })
        
        return filepath
    
    def create_temp_directory(self) -> str:
        """创建临时目录"""
        dirname = f"temp_dir_{self.session_id}_{uuid.uuid4()[:8]}"
        dirpath = os.path.join(self.data_dir, dirname)
        
        os.makedirs(dirpath, exist_ok=True)
        
        # 记录创建的资源
        self.temp_dirs.append(dirpath)
        self.created_resources.append({
            "type": "directory",
            "path": dirpath,
            "created_at": datetime.now().isoformat()
        })
        
        return dirpath
    
    def save_test_data(self, data: Any, name: str, format: str = "json") -> str:
        """保存测试数据到文件"""
        filename = f"data_{self.session_id}_{name}.{format}"
        filepath = os.path.join(self.data_dir, filename)
        
        if format == "json":
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(str(data))
        
        # 记录创建的资源
        self.created_resources.append({
            "type": "test_data",
            "path": filepath,
            "name": name,
            "created_at": datetime.now().isoformat()
        })
        
        return filepath
    
    def generate_test_data(self, template: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """基于模板生成测试数据"""
        result = template.copy()
        
        # 替换模板中的占位符
        def replace_placeholders(obj):
            if isinstance(obj, str):
                for key, value in kwargs.items():
                    placeholder = f"{{{{ {key} }}}}"
                    obj = obj.replace(placeholder, str(value))
                return obj
            elif isinstance(obj, dict):
                return {k: replace_placeholders(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_placeholders(item) for item in obj]
            else:
                return obj
        
        return replace_placeholders(result)
    
    def register_resource(self, resource_type: str, resource_id: str, cleanup_func: Optional[callable] = None):
        """注册需要清理的资源"""
        self.created_resources.append({
            "type": resource_type,
            "id": resource_id,
            "cleanup_func": cleanup_func,
            "created_at": datetime.now().isoformat()
        })
    
    def cleanup(self):
        """清理创建的所有资源"""
        if self.keep_data:
            print(f"测试数据保留模式: 不清理数据目录 {self.data_dir}")
            return
        
        # 清理文件资源
        for resource in self.created_resources:
            if resource["type"] in ["file", "test_data"] and "path" in resource:
                try:
                    if os.path.exists(resource["path"]):
                        os.remove(resource["path"])
                        print(f"已删除文件: {resource['path']}")
                except Exception as e:
                    print(f"删除文件失败 {resource['path']}: {e}")
            
            # 执行自定义清理函数
            if "cleanup_func" in resource and resource["cleanup_func"]:
                try:
                    resource["cleanup_func"]()
                    print(f"已执行自定义清理函数: {resource.get('id', 'unknown')}")
                except Exception as e:
                    print(f"执行清理函数失败: {e}")
        
        # 清理临时目录
        for dirpath in self.temp_dirs:
            try:
                if os.path.exists(dirpath):
                    shutil.rmtree(dirpath)
                    print(f"已删除目录: {dirpath}")
            except Exception as e:
                print(f"删除目录失败 {dirpath}: {e}")

@pytest.fixture(scope="session")
def data_manager(request):
    """提供测试数据管理器的fixture"""
    return request.config._test_data_manager

@pytest.fixture(scope="function")
def temp_file(data_manager):
    """创建临时文件的fixture"""
    filepath = data_manager.create_temp_file()
    yield filepath
    # 文件会在session结束时统一清理

@pytest.fixture(scope="function")
def temp_dir(data_manager):
    """创建临时目录的fixture"""
    dirpath = data_manager.create_temp_directory()
    yield dirpath
    # 目录会在session结束时统一清理

@pytest.fixture(scope="function")
def test_user_data(data_manager):
    """提供测试用户数据的fixture"""
    user_template = {
        "username": "test_user_{{unique_id}}",
        "email": "test_{{unique_id}}@example.com",
        "first_name": "Test",
        "last_name": "User",
        "is_active": True
    }
    
    unique_id = str(uuid.uuid4())[:8]
    user_data = data_manager.generate_test_data(user_template, unique_id=unique_id)
    
    # 保存用户数据到文件
    data_manager.save_test_data(user_data, f"user_{unique_id}")
    
    # 注册清理函数示例
    def cleanup_user():
        print(f"清理用户数据: {user_data['username']}")
        # 这里可以添加实际的用户删除逻辑
    
    data_manager.register_resource("user", user_data["username"], cleanup_user)
    
    yield user_data

# 使用示例：
"""
# 1. 在测试中使用测试数据
# def test_file_processing(temp_file):
#     # 写入测试内容
#     with open(temp_file, 'w') as f:
#         f.write("test content")
#     
#     # 测试文件处理逻辑
#     # ...
#     
# # 2. 使用用户数据fixture
# def test_user_registration(test_user_data):
#     print(f"测试用户: {test_user_data['username']}")
#     # 测试用户注册逻辑
#     # ...
#     
# 3. 使用数据管理器
# def test_data_generation(data_manager):
#     # 生成测试数据
#     product_data = data_manager.generate_test_data(
#         {"name": "Product {{id}}", "price": 99.99},
#         id=str(uuid.uuid4())[:4]
#     )
#     
#     # 保存测试数据
#     filepath = data_manager.save_test_data(product_data, "test_product")
#     print(f"产品数据已保存到: {filepath}")
#     
#     # 测试逻辑
#     # ...
"""
