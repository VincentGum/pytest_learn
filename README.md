# pytest_demo - 全面掌握pytest测试框架

本文档总结了pytest框架的核心概念、使用方法、最佳实践以及面试相关知识点，帮助开发者从入门到精通pytest测试框架。

## 目录结构

```
/Users/bytedance/Documents/pytest_demo/
├── app/                  # 应用程序代码
│   ├── models.py         # 数据模型
│   ├── pricing.py        # 定价相关逻辑
│   └── service.py        # 服务层逻辑
├── common/               # 通用组件
│   ├── factories.py      # 测试数据工厂
│   └── plugins/          # 自定义pytest插件
│       ├── example_plugin.py    # 基础插件示例
│       └── advanced_plugin.py   # 高级插件示例
├── config/               # 配置文件
├── tests/                # 测试目录（分层测试）
│   ├── unit/             # 单元测试
│   ├── contract/         # 契约测试
│   ├── integration/      # 集成测试
│   └── e2e/              # 端到端测试
├── conftest.py           # pytest配置和共享fixture
└── pytest.ini            # pytest配置文件
```

## 1. pytest核心概念

### 1.1 Fixture（夹具）

**定义**：Fixture是pytest中用于提供测试数据、准备测试环境或清理资源的函数。

**特性**：
- 通过`@pytest.fixture`装饰器定义
- 支持依赖注入（直接作为参数传递给测试函数）
- 提供不同的作用域控制执行频率
- 支持yield语法进行资源的设置和清理

**作用域（从大到小）**：
- `session`：整个测试会话执行一次
- `module`：每个模块执行一次
- `class`：每个测试类执行一次
- `function`：每个测试函数执行一次（默认）

**示例**：
```python
# conftest.py中的session作用域fixture
@pytest.fixture(scope="session")
def env(pytestconfig):
    """提供环境配置，整个测试会话只执行一次"""
    return pytestconfig.getoption("--env")

# function作用域fixture
@pytest.fixture(scope="function")
def temp_db(tmp_path):
    """每个测试函数都会创建和清理临时数据库"""
    p = tmp_path / "db.txt"
    p.write_text("init")
    yield p  # 测试函数使用的返回值
    p.unlink(missing_ok=True)  # 测试结束后的清理工作
```

### 1.2 Hook（钩子）

**定义**：Hook是pytest提供的扩展点，允许在测试执行的不同阶段插入自定义逻辑。这是pytest高度可扩展性的核心机制。

**工作原理**：
- pytest在测试执行的特定阶段会自动查找并调用具有特定名称的函数
- 用户只需定义与Hook同名的函数，即可在对应阶段插入自定义逻辑
- 多个插件或模块中可以定义同名Hook，pytest会按特定顺序执行它们

#### 生命周期钩子机制详解

pytest的生命周期包含多个阶段，每个阶段都有对应的Hook函数，让用户能够精确控制测试流程的各个环节：

##### 1. 配置初始化阶段
- **pytest_addoption(parser)**：添加自定义命令行参数
- **pytest_addhooks(pluginmanager)**：注册自定义钩子
- **pytest_configure(config)**：测试配置完成后执行，适合进行环境初始化

##### 2. 会话准备阶段
- **pytest_sessionstart(session)**：测试会话开始时执行，可用于准备共享资源
- **pytest_collection_modifyitems(session, config, items)**：修改收集到的测试项
- **pytest_generate_tests(metafunc)**：动态生成参数化测试

##### 3. 测试执行阶段
- **pytest_runtest_setup(item)**：每个测试用例执行前，适合前置条件检查
- **pytest_runtest_call(item)**：执行测试函数本身
- **pytest_runtest_teardown(item)**：每个测试用例执行后，适合清理资源
- **pytest_runtest_logreport(report)**：生成测试报告时，可用于收集测试结果

##### 4. 会话结束阶段
- **pytest_sessionfinish(session, exitstatus)**：测试会话结束时执行，可用于清理全局资源
- **pytest_terminal_summary(terminalreporter, exitstatus, config)**：生成终端摘要时，用于输出自定义统计信息

#### 实际业务场景Demo

##### Demo 1: 环境感知的测试执行控制

```python
# conftest.py或插件中
def pytest_collection_modifyitems(config, items):
    """根据环境自动跳过不适合的测试"""
    # 获取当前环境
    current_env = config.getoption("--env", default="dev")
    
    # 生产环境跳过慢测试和不稳定测试
    if current_env == "prod":
        skipped = 0
        for item in items:
            # 检查标记
            markers = [m.name for m in item.iter_markers()]
            
            # 跳过标记为slow或flaky的测试
            if "slow" in markers or "flaky" in markers:
                skip_reason = f"{current_env}环境跳过{'慢' if 'slow' in markers else '不稳定'}测试"
                item.add_marker(pytest.mark.skip(reason=skip_reason))
                skipped += 1
        
        if skipped > 0:
            print(f"环境: {current_env}, 已跳过{skipped}个测试")
    
    # 按测试优先级排序
    def get_priority(item):
        markers = [m.name for m in item.iter_markers()]
        if "unit" in markers: return 0
        if "contract" in markers: return 1
        if "integration" in markers: return 2
        if "e2e" in markers: return 3
        return 999
    
    items.sort(key=get_priority)
```

##### Demo 2: 测试前置条件检查与资源管理

```python
def pytest_runtest_setup(item):
    """执行测试前的前置条件检查"""
    # 检查需要数据库的测试
    if item.get_closest_marker("require_db"):
        # 检查数据库连接是否可用
        import os
        if not os.environ.get("DB_CONNECTION_STRING"):
            pytest.skip("数据库连接信息未配置")
        
        # 检查数据库是否可访问
        try:
            # 这里可以添加实际的数据库连接测试
            test_db_connection()
        except Exception as e:
            pytest.skip(f"数据库连接失败: {str(e)}")
    
    # 检查需要特定API版本的测试
    if item.get_closest_marker("api_version"):
        marker = item.get_closest_marker("api_version")
        required_version = marker.args[0]
        current_version = get_current_api_version()
        
        if current_version != required_version:
            pytest.skip(
                f"需要API版本 {required_version}, 当前版本 {current_version}"
            )

def pytest_sessionstart(session):
    """测试会话开始时初始化全局资源"""
    print("初始化测试会话资源...")
    # 创建资源池
    session._resource_pool = {
        "api_clients": {},
        "temp_files": [],
        "start_time": time.time()
    }

def pytest_sessionfinish(session, exitstatus):
    """测试会话结束时清理全局资源"""
    print("清理测试会话资源...")
    # 关闭所有API客户端
    for client in session._resource_pool["api_clients"].values():
        try:
            client.close()
        except:
            pass
    
    # 删除临时文件
    for file_path in session._resource_pool["temp_files"]:
        try:
            os.unlink(file_path)
        except:
            pass
    
    # 计算测试会话时长
    duration = time.time() - session._resource_pool["start_time"]
    print(f"测试会话总时长: {duration:.2f}秒")
```

##### Demo 3: 自定义测试报告与结果统计

```python
def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """生成自定义测试结果统计"""
    # 获取测试统计信息
    stats = terminalreporter.stats
    
    # 输出标准统计
    terminalreporter.write_sep("=", "自定义测试统计")
    
    # 统计按标记分类的测试结果
    marker_stats = {}
    for status in stats:
        for report in stats[status]:
            if hasattr(report, "item"):
                for marker in report.item.iter_markers():
                    if marker.name not in marker_stats:
                        marker_stats[marker.name] = {"passed": 0, "failed": 0, "skipped": 0}
                    if status in marker_stats[marker.name]:
                        marker_stats[marker.name][status] += 1
    
    # 输出按标记分类的统计
    if marker_stats:
        terminalreporter.write_line("按标记分类的测试结果:")
        for marker, counts in marker_stats.items():
            total = sum(counts.values())
            terminalreporter.write_line(
                f"  {marker}: 总测试数={total}, 通过={counts['passed']}, "
                f"失败={counts['failed']}, 跳过={counts['skipped']}"
            )
    
    # 计算平均测试时长
    durations = [report.duration for status in stats 
                for report in stats[status] if hasattr(report, "duration")]
    if durations:
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        terminalreporter.write_line(
            f"测试执行时长: 平均={avg_duration:.3f}s, 最长={max_duration:.3f}s"
        )
    
    # 生成JSON格式报告（如果需要）
    if config.getoption("--export-results"):
        results = {
            "summary": {k: len(v) for k, v in stats.items()},
            "marker_stats": marker_stats,
            "duration": sum(durations) if durations else 0,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open("test_results.json", "w") as f:
            json.dump(results, f, indent=2)
        terminalreporter.write_line("测试结果已导出到 test_results.json")
```

##### Demo 4: 动态测试生成与参数化

```python
def pytest_generate_tests(metafunc):
    """动态生成测试参数"""
    # 为需要feature_flag参数的测试生成参数
    if "feature_flag" in metafunc.fixturenames:
        # 从环境配置中获取可用的特性标志
        available_flags = get_available_feature_flags()
        
        # 为每个特性标志生成测试参数
        metafunc.parametrize(
            "feature_flag",
            available_flags,
            ids=[f"flag_{flag}" for flag in available_flags]
        )
    
    # 为API测试生成版本参数
    if "api_version" in metafunc.fixturenames and "endpoint" in metafunc.fixturenames:
        # 获取支持的API版本
        supported_versions = get_supported_api_versions()
        
        # 生成API版本和端点的组合
        parametrize_data = []
        ids = []
        
        for version in supported_versions:
            endpoints = get_endpoints_for_version(version)
            for endpoint in endpoints:
                parametrize_data.append((version, endpoint))
                ids.append(f"v{version}_{endpoint}")
        
        metafunc.parametrize(
            "api_version,endpoint",
            parametrize_data,
            ids=ids
        )

# 配套的fixture定义
@pytest.fixture
def feature_flag(request):
    """提供特性标志的fixture"""
    flag = request.param
    # 启用特性标志
    enable_feature_flag(flag)
    yield flag
    # 测试结束后清理
    disable_feature_flag(flag)

```

### 1.3 Plugin（插件）

**定义**：Plugin是包含多个Hook实现的模块，用于扩展pytest的功能。

**插件类型**：
- 内置插件：pytest自带
- 外部插件：通过pip安装
- 本地插件：项目中的自定义插件

**激活插件**：
```python
# conftest.py中激活自定义插件
pytest_plugins = [
    "common.plugins.example_plugin",  # 相对导入路径
    "common.plugins.advanced_plugin"
]
```

**插件实现示例**：
```python
# 高级插件示例
class AdvancedPlugin:
    def __init__(self):
        self.name = "AdvancedPlugin"
        self.version = "1.0.0"

def pytest_configure(config):
    """配置pytest，初始化插件"""
    config._advanced_plugin = AdvancedPlugin()
    config.addinivalue_line("markers", "database: 需要数据库的测试")

# 提供自定义fixture
@pytest.fixture(scope="session")
def api_version(pytestconfig):
    """提供API版本配置"""
    return pytestconfig.getoption("--api-version")
```

## 2. 测试分层策略

### 2.1 分层测试结构

按照从小到大的颗粒度排序：

| 层级 | 标记 | 目录 | 定位 | 特点 |
|------|------|------|------|------|
| **Unit (单元测试)** | `@pytest.mark.unit` | `tests/unit/` | 测试最小功能单元 | 最快、最独立、隔离性最好 |
| **Contract (契约测试)** | `@pytest.mark.contract` | `tests/contract/` | 验证API接口规范 | 关注输入输出格式和契约 |
| **Integration (集成测试)** | `@pytest.mark.integration` | `tests/integration/` | 测试组件间交互 | 验证模块间协作 |
| **E2E (端到端测试)** | `@pytest.mark.e2e` | `tests/e2e/` | 测试完整业务流程 | 最真实、最慢、资源消耗大 |

### 2.2 功能标记

除了分层标记外，还可以使用功能标记：

- `@pytest.mark.slow`：慢测试，可在特定环境跳过
- `@pytest.mark.flaky`：不稳定测试，允许重试
- `@pytest.mark.skipif`：条件跳过
- `@pytest.mark.xfail`：预期失败的测试

### 2.3 分层设计原因

1. **执行效率**：单元测试快速执行，集成和E2E测试资源消耗大
2. **问题定位**：底层测试失败更容易定位具体问题
3. **资源分配**：CI/CD中可以灵活配置不同环境执行不同层级测试
4. **测试覆盖率**：多层测试共同提供全面的代码覆盖率

## 3. 测试工程实现指南（从0到1）

### 3.1 环境搭建

```bash
# 创建虚拟环境
python -m venv .venv
# 激活虚拟环境
source .venv/bin/activate  # Linux/Mac
echo "source .venv/bin/activate" >> ~/.zshrc  # 可选：设置自动激活
# 安装pytest
pip install pytest pytest-cov
# 验证安装
pytest --version
```

### 3.2 项目结构搭建

```bash
# 创建基础目录结构
mkdir -p app common/plugins tests/unit tests/integration tests/contract tests/e2e config
# 创建配置文件
touch pytest.ini conftest.py
# 创建示例应用代码
touch app/__init__.py app/models.py app/pricing.py app/service.py
```

### 3.3 核心配置文件

**pytest.ini 配置**：
```ini
[pytest]
markers =
    unit: 单元测试
    integration: 集成测试
    contract: 契约测试
    e2e: 端到端测试
    slow: 慢测试
    flaky: 不稳定测试
    require_db: 需要数据库的测试
    mock_api: 使用模拟API的测试
    feature_flag: 特性标志测试

# 收集测试的根目录
testpaths = tests

# 测试文件名模式
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

**conftest.py 核心配置**：
```python
import pytest

# 激活自定义插件
pytest_plugins = ["common.plugins.example_plugin"]

# 添加自定义命令行选项
def pytest_addoption(parser):
    parser.addoption("--env", action="store", default="dev", help="运行环境")
    parser.addoption("--api-version", action="store", default="v1", help="API版本")

# 共享fixture定义
@pytest.fixture(scope="session")
def env(pytestconfig):
    return pytestconfig.getoption("--env")
```

### 3.4 Fixture设计模式

1. **资源管理模式**：使用yield进行资源的创建和清理
2. **数据准备模式**：生成测试数据
3. **环境配置模式**：设置测试环境变量
4. **依赖注入模式**：提供依赖组件的模拟或实例

### 3.5 分层测试实现

**单元测试示例**：
```python
# tests/unit/test_pricing.py
import pytest
from app.pricing import calculate_price

@pytest.mark.unit
def test_basic_price_calculation():
    """测试基本价格计算"""
    result = calculate_price(100, 0.1)  # 原价100，折扣0.1
    assert result == 90

@pytest.mark.unit
def test_with_coupon(set_coupon):
    """测试使用优惠券的价格计算"""
    # set_coupon fixture会设置环境变量COUPON_CODE
    result = calculate_price(100, 0.1)
    assert result < 90  # 使用优惠券后价格更低
```

**契约测试示例**：
```python
# tests/contract/test_api_shape.py
import pytest
import json

@pytest.mark.contract
def test_api_response_structure():
    """测试API响应结构符合契约"""
    # 这里通常会调用API或模拟API响应
    response_data = {
        "items": [
            {"id": 1, "name": "Product 1", "price": 99.99},
            {"id": 2, "name": "Product 2", "price": 199.99}
        ],
        "total": 2,
        "page": 1,
        "page_size": 10
    }
    
    # 验证响应结构
    assert isinstance(response_data, dict)
    assert "items" in response_data
    assert isinstance(response_data["items"], list)
    assert "total" in response_data
    assert isinstance(response_data["total"], int)
```

## 4. 测试工程维护最佳实践

### 4.1 质量保障

- **代码覆盖率**：使用pytest-cov监控测试覆盖率
  ```bash
  pytest --cov=app tests/
  ```
- **测试命名规范**：清晰描述测试场景和期望结果
- **测试隔离性**：确保测试之间不相互影响
- **测试数据管理**：使用工厂模式生成测试数据

### 4.2 CI/CD集成

- **不同环境执行不同测试**：
  ```yaml
  # .github/workflows/tests.yml 示例
  jobs:
    unit-tests:
      runs-on: ubuntu-latest
      steps:
        - run: pytest -m unit --cov=app
    
    integration-tests:
      runs-on: ubuntu-latest
      steps:
        - run: pytest -m integration
    
    e2e-tests:
      runs-on: ubuntu-latest
      if: github.ref == 'refs/heads/main'
      steps:
        - run: pytest -m e2e
  ```

### 4.3 插件和钩子应用

- **环境感知**：根据环境自动跳过不适合的测试
- **测试报告增强**：自定义测试报告格式
- **资源管理优化**：智能分配和回收测试资源

### 4.4 问题排查

1. **详细日志**：使用fixture捕获和分析日志
   ```python
   @pytest.fixture
def log_capture(caplog):
       logger = logging.getLogger("app.pricing")
       caplog.set_level(logging.INFO, logger=logger.name)
       return caplog
   ```

2. **参数化调试**：使用参数化测试覆盖多种场景
   ```python
   @pytest.mark.parametrize("size", [1, 2, 3], ids=["small", "medium", "large"])
   def test_different_sizes(size):
       """测试不同尺寸的行为"""
       # 测试逻辑
   ```

## 5. 面试常见问题及回答建议

### 5.1 pytest核心特点

**回答要点**：
- **简洁的语法**：使用assert语句进行断言，无需特殊断言API
- **丰富的fixture系统**：依赖注入、资源管理、作用域控制
- **强大的标记系统**：灵活组织和选择测试
- **完善的插件生态**：超过300个官方和第三方插件
- **详细的失败报告**：提供清晰的错误信息和上下文

### 5.2 pytest vs unittest

**回答要点**：
- pytest更简洁，unittest更传统（基于类和继承）
- pytest支持函数式测试，unittest强制使用类
- pytest的fixture比unittest的setUp/tearDown更灵活
- pytest有更丰富的断言方式和更详细的错误报告
- pytest拥有更活跃的社区和更多的插件支持

### 5.3 如何设计高效的fixture

**回答要点**：
- 合理使用作用域：高频使用的资源使用session或module作用域
- 使用yield进行资源清理：确保测试后资源正确释放
- 避免fixture过度依赖：保持fixture的独立性和可重用性
- 参数化fixture：使用params参数支持多种场景
- 使用fixture工厂：动态生成测试数据

### 5.4 如何从0到1构建测试工程

**回答要点**：
1. **环境搭建**：创建虚拟环境，安装pytest及相关插件
2. **项目结构设计**：建立分层测试目录，遵循最佳实践
3. **核心配置**：编写pytest.ini和conftest.py，配置基本选项
4. **基础组件开发**：
   - 开发通用fixture（环境、数据库、API客户端等）
   - 实现自定义插件和钩子
   - 创建测试数据工厂
5. **分层测试实现**：从单元测试开始，逐步扩展到集成和E2E测试
6. **CI/CD集成**：配置自动化测试流程，优化执行效率
7. **文档和最佳实践**：编写测试规范，确保团队遵循

### 5.5 如何处理复杂测试场景

**回答要点**：
- **参数化测试**：处理多组输入输出场景
- **模拟和桩件**：使用monkeypatch模拟外部依赖
- **标记和过滤**：使用标记组织和选择测试
- **自定义插件**：开发插件解决特定问题
- **测试数据管理**：使用工厂模式和数据生成器

## 6. 项目实战示例

### 6.1 测试运行示例

```bash
# 运行所有测试
pytest

# 运行特定标记的测试
pytest -m unit
pytest -m "not slow"
pytest -m "unit or contract"

# 指定环境运行
pytest --env=prod

# 生成覆盖率报告
pytest --cov=app --cov-report=html

# 导出测试结果
pytest --export-results

# 调试模式运行
pytest -xvs tests/unit/test_pricing.py::test_basic_price_calculation
```

### 6.2 自定义插件功能展示

项目中实现了两个主要插件：

1. **example_plugin.py**：提供基础功能
   - 测试排序和过滤
   - 会话信息收集
   - 自定义测试摘要

2. **advanced_plugin.py**：提供高级功能
   - 特性标志支持
   - API客户端模拟
   - 测试结果导出
   - 自定义命令行选项

## 7. 进阶学习资源

- **官方文档**：[https://docs.pytest.org/](https://docs.pytest.org/)
- **插件索引**：[https://plugincompat.herokuapp.com/](https://plugincompat.herokuapp.com/)
- **pytest实战**：《Python测试之道》
- **持续集成**：结合GitHub Actions或Jenkins

---

本文档涵盖了pytest框架的核心概念、最佳实践和实战技巧，帮助开发者构建高效、可维护的测试工程。通过合理使用fixture、hook和plugin，可以充分发挥pytest的强大功能，提升测试效率和质量。