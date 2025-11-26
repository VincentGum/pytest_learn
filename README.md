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

**定义**：Hook是pytest提供的扩展点，允许在测试执行的不同阶段插入自定义逻辑。

**常见钩子函数**：
- `pytest_configure`：pytest配置时执行
- `pytest_collection_modifyitems`：收集测试项后修改
- `pytest_sessionstart`/`pytest_sessionfinish`：会话开始/结束时执行
- `pytest_runtest_setup`/`pytest_runtest_teardown`：测试函数执行前/后
- `pytest_generate_tests`：参数化测试生成
- `pytest_addoption`：添加自定义命令行选项

**示例**：
```python
# 自定义测试排序和过滤
def pytest_collection_modifyitems(config, items):
    """根据环境过滤测试并按标记排序"""
    # 生产环境跳过慢测试
    if config.getoption("--env") == "prod":
        for item in items:
            if "slow" in [m.name for m in item.iter_markers()]:
                item.add_marker(pytest.mark.skip(reason="生产环境跳过慢测试"))
    
    # 按测试类型排序
    items.sort(key=lambda x: ("unit" not in [m.name for m in x.iter_markers()],
                            "contract" not in [m.name for m in x.iter_markers()],
                            "integration" not in [m.name for m in x.iter_markers()],
                            "e2e" not in [m.name for m in x.iter_markers()]))
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