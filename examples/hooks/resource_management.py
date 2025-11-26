# 测试前置条件检查与资源管理 Hook 示例
import pytest
import time
from typing import Dict, Any, List
import threading

# 资源管理器类
class ResourceManager:
    def __init__(self):
        self.resources = {}
        self.lock = threading.RLock()
        self.start_time = None
    
    def acquire_resource(self, resource_type: str, resource_id: str) -> Dict[str, Any]:
        """获取资源，如果不存在则创建"""
        with self.lock:
            if resource_type not in self.resources:
                self.resources[resource_type] = {}
            
            if resource_id not in self.resources[resource_type]:
                # 模拟资源创建
                self.resources[resource_type][resource_id] = {
                    "id": resource_id,
                    "type": resource_type,
                    "created_at": time.time(),
                    "status": "active"
                }
                print(f"创建资源: {resource_type}:{resource_id}")
            
            return self.resources[resource_type][resource_id]
    
    def release_resource(self, resource_type: str, resource_id: str):
        """释放资源"""
        with self.lock:
            if resource_type in self.resources and resource_id in self.resources[resource_type]:
                del self.resources[resource_type][resource_id]
                print(f"释放资源: {resource_type}:{resource_id}")
                
                # 如果资源类型下没有资源了，删除该类型
                if not self.resources[resource_type]:
                    del self.resources[resource_type]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取资源统计信息"""
        total_resources = sum(len(resources) for resources in self.resources.values())
        return {
            "total_resources": total_resources,
            "resource_types": dict(self.resources),
            "active_types": list(self.resources.keys())
        }

# 全局资源管理器实例
_resource_manager = ResourceManager()

def pytest_sessionstart(session):
    """测试会话开始时初始化资源管理器"""
    _resource_manager.start_time = time.time()
    print("资源管理器初始化完成")
    
    # 这里可以添加全局资源的初始化逻辑
    # 例如连接数据库、启动服务等

def pytest_sessionfinish(session, exitstatus):
    """测试会话结束时清理资源"""
    # 清理所有资源
    stats = _resource_manager.get_stats()
    print(f"\n资源使用统计:")
    print(f"  总资源数: {stats['total_resources']}")
    print(f"  资源类型: {', '.join(stats['active_types']) if stats['active_types'] else '无'}")
    
    # 计算测试耗时
    if _resource_manager.start_time:
        duration = time.time() - _resource_manager.start_time
        print(f"  测试总耗时: {duration:.2f} 秒")
    
    # 清理所有资源
    _resource_manager.resources.clear()
    print("所有资源已清理")

def pytest_runtest_setup(item):
    """每个测试用例执行前检查前置条件"""
    # 检查测试是否有数据库依赖
    db_marker = item.get_closest_marker("require_db")
    if db_marker:
        # 模拟检查数据库连接
        print(f"[{item.nodeid}] 检查数据库连接...")
        # 这里可以添加实际的数据库连接检查逻辑
        
        # 获取数据库资源
        db_config = db_marker.kwargs or {"db": "default"}
        _resource_manager.acquire_resource("database", db_config["db"])
    
    # 检查测试是否需要特定服务
    service_marker = item.get_closest_marker("require_service")
    if service_marker and service_marker.args:
        service_name = service_marker.args[0]
        print(f"[{item.nodeid}] 检查服务: {service_name}...")
        # 获取服务资源
        _resource_manager.acquire_resource("service", service_name)

@pytest.fixture(scope="function")
def resource_manager():
    """提供资源管理器的fixture"""
    yield _resource_manager
    
    # 测试结束后清理该测试创建的资源
    # 这里可以添加特定的清理逻辑

@pytest.fixture(scope="function")
def db_connection(request):
    """数据库连接fixture"""
    # 获取测试的数据库标记
    db_marker = request.node.get_closest_marker("require_db")
    db_name = db_marker.kwargs.get("db", "default") if db_marker else "default"
    
    # 获取数据库资源
    db_resource = _resource_manager.acquire_resource("database", db_name)
    
    # 模拟数据库连接
    class MockDBConnection:
        def __init__(self, db_info):
            self.db_info = db_info
            self.connected = True
        
        def execute(self, query):
            if not self.connected:
                raise Exception("数据库连接已关闭")
            print(f"执行SQL: {query} (数据库: {self.db_info['id']})")
            return {"status": "success"}
        
        def close(self):
            self.connected = False
    
    connection = MockDBConnection(db_resource)
    
    yield connection
    
    # 关闭连接并释放资源
    connection.close()
    _resource_manager.release_resource("database", db_name)
