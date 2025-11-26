# 分布式测试协调插件
import pytest
import os
import json
import socket
import uuid
import time
import random
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
import logging
import threading
import queue

# 插件元数据
__version__ = "1.0.0"
__description__ = "分布式测试协调插件，支持大规模测试的分片执行和协调"

# 配置日志记录器
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("distributed_test_plugin")

def pytest_addoption(parser):
    """添加命令行参数选项"""
    group = parser.getgroup("distributed", "分布式测试设置")
    group.addoption(
        "--node-total",
        action="store",
        type=int,
        default=1,
        dest="node_total",
        help="总节点数"
    )
    group.addoption(
        "--node-index",
        action="store",
        type=int,
        default=0,
        dest="node_index",
        help="当前节点索引（从0开始）"
    )
    group.addoption(
        "--shard-method",
        action="store",
        default="round_robin",
        dest="shard_method",
        help="分片方法: round_robin, hash, random, module"
    )
    group.addoption(
        "--coordinator-url",
        action="store",
        dest="coordinator_url",
        help="中央协调服务器URL（可选）"
    )
    group.addoption(
        "--test-timeout",
        action="store",
        type=float,
        dest="test_timeout",
        help="单个测试的超时时间（秒）"
    )

def pytest_configure(config):
    """配置插件"""
    # 添加自定义标记
    config.addinivalue_line(
        "markers", 
        "shard_group(group_name): 标记测试属于特定的分片组"
    )
    config.addinivalue_line(
        "markers", 
        "no_shard: 标记测试不应被分片，每个节点都应执行"
    )
    
    # 创建分布式测试管理器实例
    node_total = config.getoption("node_total")
    node_index = config.getoption("node_index")
    shard_method = config.getoption("shard_method")
    coordinator_url = config.getoption("coordinator_url")
    test_timeout = config.getoption("test_timeout")
    
    # 验证节点配置
    if node_index >= node_total:
        raise ValueError(f"节点索引 {node_index} 必须小于总节点数 {node_total}")
    
    config._distributed_manager = DistributedTestManager(
        node_total=node_total,
        node_index=node_index,
        shard_method=shard_method,
        coordinator_url=coordinator_url,
        test_timeout=test_timeout
    )
    
    # 添加插件信息到配置对象
    config.metadata["distributed_plugin"] = {
        "version": __version__,
        "node_index": node_index,
        "node_total": node_total,
        "shard_method": shard_method,
        "hostname": socket.gethostname()
    }
    
    print(f"分布式测试配置: 节点 {node_index+1}/{node_total} (分片方法: {shard_method})")

def pytest_sessionstart(session):
    """测试会话开始时初始化"""
    if hasattr(session.config, "_distributed_manager"):
        session.config._distributed_manager.start_session()

def pytest_sessionfinish(session, exitstatus):
    """测试会话结束时清理"""
    if hasattr(session.config, "_distributed_manager"):
        session.config._distributed_manager.finish_session()

def pytest_collection_modifyitems(session, config, items):
    """修改收集到的测试项，实现分片逻辑"""
    if not hasattr(config, "_distributed_manager"):
        return
    
    distributed_manager = config._distributed_manager
    
    # 获取应该在当前节点运行的测试
    items_to_run, skipped_items = distributed_manager.shard_tests(items)
    
    # 替换items列表，只保留应该运行的测试
    items[:] = items_to_run
    
    # 记录跳过的测试数量
    distributed_manager.skipped_tests_count = len(skipped_items)
    
    print(f"\n分片结果:")
    print(f"  总测试数: {len(items_to_run) + len(skipped_items)}")
    print(f"  当前节点运行: {len(items_to_run)}")
    print(f"  当前节点跳过: {len(skipped_items)}")

def pytest_runtest_protocol(item, nextitem):
    """实现测试超时控制"""
    distributed_manager = item.config._distributed_manager
    
    # 检查是否需要超时控制
    if not distributed_manager.test_timeout:
        return None
    
    # 记录测试开始
    distributed_manager.start_test(item.nodeid)
    
    # 使用线程执行测试，支持超时控制
    result_queue = queue.Queue()
    
    def run_test():
        try:
            # 执行原始的测试协议
            result = pytest.hooks.pytest_runtest_protocol(item, nextitem)
            result_queue.put((True, result))
        except Exception as e:
            result_queue.put((False, e))
    
    # 启动测试线程
    test_thread = threading.Thread(target=run_test)
    test_thread.daemon = True
    test_thread.start()
    
    try:
        # 等待测试完成或超时
        success, result = result_queue.get(timeout=distributed_manager.test_timeout)
        
        if success:
            # 记录测试完成
            distributed_manager.finish_test(item.nodeid)
            return result
        else:
            # 测试线程异常
            raise result
    except queue.Empty:
        # 测试超时
        distributed_manager.record_timeout(item.nodeid)
        print(f"\n⚠️  测试超时: {item.nodeid} (超过 {distributed_manager.test_timeout} 秒)")
        
        # 创建失败报告
        item.config.hook.pytest_runtest_logstart(nodeid=item.nodeid, location=item.location)
        rep = item.config.hook.pytest_runtest_makereport(item=item, call=None)
        rep.when = "call"
        rep.failed = True
        rep.passed = False
        rep.longrepr = f"测试执行超时 (超过 {distributed_manager.test_timeout} 秒)"
        
        item.config.hook.pytest_runtest_logreport(report=rep)
        item.config.hook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location)
        
        return True

class DistributedTestManager:
    """分布式测试管理器"""
    def __init__(self, node_total: int = 1, node_index: int = 0,
                 shard_method: str = "round_robin", coordinator_url: Optional[str] = None,
                 test_timeout: Optional[float] = None):
        self.node_total = node_total
        self.node_index = node_index
        self.shard_method = shard_method
        self.coordinator_url = coordinator_url
        self.test_timeout = test_timeout
        
        # 会话信息
        self.session_id = str(uuid.uuid4())[:8]
        self.hostname = socket.gethostname()
        self.start_time = None
        self.end_time = None
        
        # 测试统计
        self.skipped_tests_count = 0
        self.running_tests: Dict[str, float] = {}
        self.completed_tests: Dict[str, Dict[str, Any]] = {}
        self.timeout_tests: List[str] = []
        
        # 协调器客户端（如果配置了）
        self.coordinator = None
        if coordinator_url:
            # 这里可以实现与中央协调服务器的通信
            self.coordinator = DummyCoordinatorClient(coordinator_url)
    
    def start_session(self):
        """开始测试会话"""
        self.start_time = time.time()
        
        # 记录会话开始
        if self.coordinator:
            self.coordinator.report_session_start({
                "session_id": self.session_id,
                "node_index": self.node_index,
                "hostname": self.hostname,
                "timestamp": datetime.now().isoformat()
            })
    
    def finish_session(self):
        """结束测试会话"""
        self.end_time = time.time()
        
        # 计算统计数据
        total_duration = self.end_time - self.start_time if self.start_time else 0
        
        report = {
            "session_id": self.session_id,
            "node_index": self.node_index,
            "node_total": self.node_total,
            "hostname": self.hostname,
            "shard_method": self.shard_method,
            "start_time": datetime.now().isoformat() if self.start_time else None,
            "end_time": datetime.now().isoformat(),
            "duration": total_duration,
            "completed_tests": len(self.completed_tests),
            "skipped_tests": self.skipped_tests_count,
            "timeout_tests": len(self.timeout_tests),
            "test_timeout": self.test_timeout
        }
        
        # 保存报告
        report_file = f"distributed_report_node_{self.node_index}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n===== 分布式测试报告 =====")
        print(f"会话ID: {self.session_id}")
        print(f"节点: {self.node_index+1}/{self.node_total} ({self.hostname})")
        print(f"总耗时: {total_duration:.2f} 秒")
        print(f"完成测试: {len(self.completed_tests)}")
        print(f"跳过测试: {self.skipped_tests_count}")
        print(f"超时测试: {len(self.timeout_tests)}")
        print(f"报告文件: {report_file}")
        
        # 向协调器报告会话结束
        if self.coordinator:
            self.coordinator.report_session_end(report)
    
    def shard_tests(self, items: List) -> tuple:
        """根据分片方法将测试分配到不同节点"""
        items_to_run = []
        skipped_items = []
        
        # 为每个测试项决定是否在当前节点运行
        for item in items:
            # 检查是否有no_shard标记
            if item.get_closest_marker("no_shard"):
                # 每个节点都应执行的测试
                items_to_run.append(item)
                continue
            
            # 检查是否应该在当前节点运行
            if self.should_run_on_current_node(item):
                items_to_run.append(item)
            else:
                skipped_items.append(item)
        
        return items_to_run, skipped_items
    
    def should_run_on_current_node(self, item) -> bool:
        """判断测试是否应该在当前节点运行"""
        # 获取分片组标记
        shard_group_marker = item.get_closest_marker("shard_group")
        group_name = shard_group_marker.args[0] if shard_group_marker and shard_group_marker.args else None
        
        # 根据不同的分片方法计算
        if self.shard_method == "round_robin":
            # 轮询分片
            return self._round_robin_shard(item, group_name)
        elif self.shard_method == "hash":
            # 哈希分片
            return self._hash_shard(item, group_name)
        elif self.shard_method == "random":
            # 随机分片（使用固定种子确保一致性）
            return self._random_shard(item, group_name)
        elif self.shard_method == "module":
            # 按模块分片
            return self._module_shard(item)
        else:
            # 默认使用轮询分片
            return self._round_robin_shard(item, group_name)
    
    def _round_robin_shard(self, item, group_name=None) -> bool:
        """轮询分片方法"""
        # 如果有组，按组分片
        if group_name:
            # 使用组名的哈希作为基础
            base_index = hash(group_name) % self.node_total
            return base_index == self.node_index
        
        # 否则按测试索引分片
        # 这里简化处理，实际应该使用更可靠的方式获取索引
        return hash(item.nodeid) % self.node_total == self.node_index
    
    def _hash_shard(self, item, group_name=None) -> bool:
        """哈希分片方法"""
        # 计算哈希值
        if group_name:
            hash_value = hash(group_name)
        else:
            hash_value = hash(item.nodeid)
        
        # 确保哈希值为正
        hash_value = abs(hash_value)
        
        # 计算分片索引
        shard_index = hash_value % self.node_total
        
        return shard_index == self.node_index
    
    def _random_shard(self, item, group_name=None) -> bool:
        """随机分片方法"""
        # 使用固定种子确保多次运行结果一致
        if group_name:
            seed = hash(group_name)
        else:
            seed = hash(item.nodeid)
        
        # 设置随机种子
        random.seed(seed)
        
        # 随机选择节点
        selected_node = random.randint(0, self.node_total - 1)
        
        return selected_node == self.node_index
    
    def _module_shard(self, item) -> bool:
        """按模块分片"""
        # 获取模块名
        module_name = item.module.__name__
        
        # 按模块名哈希分片
        shard_index = hash(module_name) % self.node_total
        
        return shard_index == self.node_index
    
    def start_test(self, nodeid: str):
        """记录测试开始"""
        self.running_tests[nodeid] = time.time()
    
    def finish_test(self, nodeid: str):
        """记录测试完成"""
        if nodeid in self.running_tests:
            duration = time.time() - self.running_tests[nodeid]
            del self.running_tests[nodeid]
            
            self.completed_tests[nodeid] = {
                "duration": duration,
                "completed_at": datetime.now().isoformat()
            }
    
    def record_timeout(self, nodeid: str):
        """记录测试超时"""
        self.timeout_tests.append(nodeid)
        if nodeid in self.running_tests:
            del self.running_tests[nodeid]

class DummyCoordinatorClient:
    """模拟中央协调服务器客户端"""
    def __init__(self, url: str):
        self.url = url
        print(f"初始化协调器客户端: {url}")
    
    def report_session_start(self, data: Dict[str, Any]):
        """报告会话开始"""
        print(f"报告会话开始到协调器: {data['session_id']}")
    
    def report_session_end(self, data: Dict[str, Any]):
        """报告会话结束"""
        print(f"报告会话结束到协调器: {data['session_id']}")

@pytest.fixture(scope="session")
def distributed_info(request):
    """提供分布式测试信息的fixture"""
    if hasattr(request.config, "_distributed_manager"):
        manager = request.config._distributed_manager
        return {
            "session_id": manager.session_id,
            "node_index": manager.node_index,
            "node_total": manager.node_total,
            "hostname": manager.hostname,
            "shard_method": manager.shard_method
        }
    
    # 如果未启用分布式测试，返回默认值
    return {
        "session_id": "local",
        "node_index": 0,
        "node_total": 1,
        "hostname": socket.gethostname(),
        "shard_method": "local"
    }

# 使用示例：
"""
# 1. 标记需要特殊处理的测试
# @pytest.mark.no_shard
# def test_critical_function():
#     # 这个测试在每个节点都运行
#     # ...
#
# @pytest.mark.shard_group("database_tests")
# def test_database_operation():
#     # 同一组的测试会被分配到同一个节点
#     # ...
#
# 2. 运行分布式测试
# # 在节点0上运行：
# pytest tests/ --node-total=3 --node-index=0 --shard-method=hash
# 
# # 在节点1上运行：
# pytest tests/ --node-total=3 --node-index=1 --shard-method=hash
# 
# # 在节点2上运行：
# pytest tests/ --node-total=3 --node-index=2 --shard-method=hash
#
# 3. 设置测试超时
# pytest tests/ --test-timeout=30  # 单个测试最多运行30秒
"""
