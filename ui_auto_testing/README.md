# HAT 框架 - 项目级 UI 自动化测试

> Hybrid Automation Testing Framework - 用例驱动的混合自动化测试框架

---

## 🏗 框架架构

```
项目根 (ui_auto_testing/)
├── main.py                      # 入口脚本: 解析参数 + 调用 pytest
├── conftest.py                  # pytest 配置: 注册 CasesPlugin
├── requirements.txt             # 依赖清单
│
├── HAT/                         # 🌍 框架核心代码 (与用例完全解耦)
│   ├── core/
│   │   ├── globalContext.py     #   全局变量池: 用例间数据共享
│   │   ├── CasesPlugin.py       #   pytest 插件: 解析用例 + 参数化
│   │   └── TestRunner.py        #   用例执行引擎: 驱动每个步骤
│   │
│   ├── parse/
│   │   ├── caseParser.py        #   解析器统一入口
│   │   ├── YamlCaseParser.py    #   YAML 文件解析器
│   │   └── ExcelCaseParser.py   #   Excel 文件解析器
│   │
│   ├── keywords/
│   │   └── web_keywords.py      #   Web 关键字库 (20+ 关键字方法)
│   │
│   ├── context/
│   │   └── WebCaseContext.py    #   浏览器驱动管理器
│   │
│   ├── utils/
│   │   ├── VarRender.py         #   Jinja2 模板变量渲染
│   │   └── allure_step_logger.py #  Allure 步骤日志装饰器
│   │
│   ├── extend/
│   │   └── script/
│   │       └── run_script.py    #   动态 Python 脚本执行器
│   │
│   └── key_dir/                 #   自定义关键字目录 (可扩展)
│       └── 生成随机手机号.py    #   示例: 自定义关键字
│
└── hat-test-cases/              # 📝 测试用例 (与框架完全解耦)
    ├── context.yaml             #   全局配置 + 元素定位表
    ├── 0_服务启动与页面加载.yaml
    ├── 1_Agent列表页面.yaml
    ├── 2_创建新Agent.yaml
    ├── 3_查看Agent详情.yaml
    ├── 4_对话发送消息.yaml
    ├── 5_新建对话.yaml
    ├── 6_房间管理.yaml
    ├── 7_Hub管理.yaml
    ├── 8_计算机工作区.yaml
    ├── 9_用户管理.yaml
    ├── 10_完整端到端流程.yaml
    └── 11_清理测试Agent.yaml
```

---

## 🔑 核心设计原则 - 解耦

### 1. 用例与框架代码分离

| 关注点 | 位置 | 维护者 |
|-------|------|-------|
| 测试逻辑 | `hat-test-cases/*.yaml` | 测试工程师 / 业务方 |
| 关键字实现 | `HAT/keywords/web_keywords.py` | 框架维护者 |
| 变量与元素定位 | `hat-test-cases/context.yaml` | 测试工程师 |

### 2. 关键字驱动 (Keyword-Driven)

用例由一系列 **"步骤关键字"** 组成，每个关键字对应框架中的一个方法：

```yaml
用例步骤:
  - 步骤描述: 访问首页
    操作类型: 访问网址           # → WebKeywords.访问网址()
    网址: "{{base_url}}/"        #    参数: 网址
```

框架自动通过 `getattr(keywords, 操作类型)` 反射调用方法。

### 3. 模板变量渲染

所有字符串参数支持 `{{变量名}}` 模板语法，由 `HAT/utils/VarRender.py` 处理，变量来源：
- `context.yaml` 中定义的常量
- 用例步骤中用 `变量名:` 字段设置的动态值
- `g_context().set_dict()` 程序化设置

### 4. 元素定位集中管理

页面元素定位全部在 `context.yaml` 的 `_WEB页面元素` 中定义：

```yaml
_WEB页面元素:
  Agent_导航链接:
    定位方式: css
    目标对象: "a[href*='agent']"
```

用例使用时只需传别名：
```yaml
操作类型: 点击元素
_页面元素: Agent_导航链接
```

> 页面改版时，只需改 `context.yaml`，不用改任何用例文件。

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 确保 CSGClaw 服务运行

```bash
# 服务需监听在 context.yaml 中配置的 base_url (默认 http://127.0.0.1:18080)
csgclaw serve
```

### 3. 预览所有用例（不执行浏览器）

```bash
python main.py --dry-run
```

### 4. 执行全部测试用例

```bash
python main.py                       # 运行 YAML 用例
python main.py --type yaml           # 同上，显式指定类型
python main.py --headless            # 无头模式（不弹出浏览器窗口）
python main.py --report              # 运行后生成 Allure 报告
```

### 5. 运行单个用例文件

```bash
python main.py --cases ./hat-test-cases  # 运行目录中所有用例
# 或直接运行一个文件（配合用例编号实现精确测试）
```

---

## 📝 YAML 用例编写规范

### 完整示例

```yaml
基础配置:
  用例类型: WebCase
  一级模块: Agent管理
  二级模块: Agent创建
  用例标题: 验证创建新Agent功能

前置脚本: ""           # 可选，执行前运行的 Python 代码
后置脚本: ""           # 可选，执行后运行的 Python 代码

用例步骤:
  - 步骤描述: 访问首页
    操作类型: 访问网址
    网址: "{{base_url}}/"

  - 步骤描述: 等待2秒
    操作类型: 强制等待
    数据内容: "2"

  - 步骤描述: 点击Agent导航
    操作类型: 点击元素
    _页面元素: Agent_导航链接

  - 步骤描述: 获取列表并保存到变量
    操作类型: 获取元素文本
    _页面元素: Agent_列表容器
    变量名: my_list

  - 步骤描述: 验证列表包含新Agent
    操作类型: 断言文本包含
    预期结果: "测试智能体"
    实际结果: "{{my_list}}"

数据驱动:
  - description: 正常场景
    test_agent_name: "测试智能体"
```

### 字段说明

| 字段 | 必填 | 说明 |
|-----|-----|------|
| 基础配置.用例类型 | ✅ | `WebCase` / `ApiCase` / `AppCase` |
| 基础配置.一级模块 | ✅ | 报告中显示的模块分类 |
| 基础配置.二级模块 | ✅ | 报告中显示的子模块分类 |
| 基础配置.用例标题 | ✅ | 用例的简短描述 |
| 用例步骤[].操作类型 | ✅ | 要调用的关键字方法名 |
| 用例步骤[]._页面元素 | ❌ | 元素别名（在 `context.yaml` 中定义） |
| 用例步骤[].变量名 | ❌ | 把当前步骤结果存入变量 |
| 数据驱动[] | ❌ | 多组数据驱动同一用例 |

### 用例文件命名规则

- 文件格式: `{数字编号}_{描述}.yaml`
- 数字编号决定用例执行顺序
- 例如: `0_启动验证.yaml`, `1_列表加载.yaml`, `2_创建功能.yaml`

---

## 🔧 可用关键字清单

### 页面操作类

| 关键字 | 说明 | 参数 |
|-------|------|------|
| 访问网址 | 打开指定 URL | 网址 / url |
| 点击元素 | 点击指定元素 | _页面元素 |
| 输入内容 | 在输入框输入文本 | _页面元素, 数据内容 |
| 执行脚本 | 执行 JavaScript 代码 | 代码 / script, 变量名(可选) |
| 滚动到元素 | 滚动页面到指定元素 | _页面元素 |
| 选择下拉框 | 选择下拉框选项 | _页面元素, 文本/值/索引 |
| 按回车 | 按回车键 | _页面元素(可选) |
| 切换iframe | 切换到 iframe | _页面元素 / _索引 / _默认 |
| 关闭浏览器 | 关闭当前浏览器实例 | 无 |

### 断言类

| 关键字 | 说明 | 参数 |
|-------|------|------|
| 断言文本 | 通用断言（支持多比较符） | 预期结果, 实际结果, 比较符 |
| 断言文本相等 | 断言两个文本相等 | 预期结果, 实际结果 |
| 断言文本包含 | 断言文本包含子串 | 预期结果, 实际结果 |
| 断言文本不包含 | 断言文本不含子串 | 预期结果, 实际结果 |
| 断言浏览器路径 | 断言当前 URL | 数据内容, 比较符 |
| 断言元素存在 | 断言元素存在于 DOM | _页面元素 |
| 断言元素可见 | 断言元素可见 | _页面元素 |
| 断言元素不可见 | 断言元素不可见 | _页面元素 |
| 断言数字大于 | 断言数字比较 | 预期结果, 实际结果 |
| 断言数字小于 | 断言数字比较 | 预期结果, 实际结果 |

### 数据获取类

| 关键字 | 说明 | 参数 |
|-------|------|------|
| 获取元素文本 | 获取元素文本内容 | _页面元素, 变量名 |
| 生成随机数 | 生成指定长度随机数 | 位数, 变量名 |
| image_recognition | 验证码图片识别 | _页面元素, 变量名 |
| 识别验证码 | 同上（中文别名） | 同上 |
| 提取数据MYSQL | 从 MySQL 表查询数据 | _数据库, SQL, 变量名 |
| 切换到最新窗口 | 切换到最新打开的浏览器窗口 | 无 |

### 等待类

| 关键字 | 说明 | 参数 |
|-------|------|------|
| 强制等待 | 固定等待时间 | 数据内容（秒数） |

---

## 📊 Allure 报告

使用 `--report` 参数运行后，可生成详细的测试报告：

```bash
python main.py --report

# 启动本地报告服务器查看
allure serve ./allure-results

# 或生成静态 HTML 报告
allure generate ./allure-results -o ./allure-report --clean
```

报告包含:
- 按一级模块 / 二级模块分组的用例统计
- 每个步骤的详细日志和截图
- 失败用例的异常堆栈
- 历史趋势图

---

## 🔨 扩展框架

### 1. 添加新的关键字方法

编辑 `HAT/keywords/web_keywords.py`:

```python
class WebKeywords:
    # ... 现有方法 ...

    def 自定义新关键字(self, **kwargs):
        """新关键字的功能说明"""
        param1 = kwargs.get("参数1")
        param2 = kwargs.get("参数2", "默认值")
        # 在这里写具体逻辑
        print(f"新关键字执行: {param1}, {param2}")
```

### 2. 注册新的用例类型

编辑 `HAT/core/TestRunner.py`:

```python
from my_module import MyContext
_CASE_TYPE_MAP["ApiCase"] = MyContext
```

### 3. 添加自定义关键字文件

在 `HAT/key_dir/` 目录创建新 Python 文件，文件名 = 类名 = 方法名，
例如 `生成手机号.py`:

```python
class 生成手机号:
    def __init__(self, driver=None):
        self.driver = driver

    def 生成手机号(self, **kwargs):
        # 自定义逻辑
        phone = "138" + "".join(random.choices("0123456789", k=8))
        var_name = kwargs.get("变量名")
        if var_name:
            g_context().set_dict(var_name, phone)
        return phone
```

在 context.yaml 中配置:

```yaml
key_dir: ./HAT/key_dir
```

在测试用例中使用:

```yaml
- 步骤描述: 生成测试手机号
  操作类型: 生成手机号
  变量名: test_phone

- 步骤描述: 使用手机号
  操作类型: 输入内容
  _页面元素: 手机号输入框
  数据内容: "{{test_phone}}"
```

---

## 📁 完整目录清单

```
ui_auto_testing/
├── main.py                           # 入口脚本
├── conftest.py                       # pytest 配置
├── requirements.txt                  # 依赖
├── HAT/                              # 框架核心 (12个文件)
│   ├── __init__.py
│   ├── core/
│   │   ├── globalContext.py
│   │   ├── CasesPlugin.py
│   │   └── TestRunner.py
│   ├── parse/
│   │   ├── caseParser.py
│   │   ├── YamlCaseParser.py
│   │   └── ExcelCaseParser.py
│   ├── keywords/
│   │   └── web_keywords.py
│   ├── context/
│   │   └── WebCaseContext.py
│   ├── utils/
│   │   ├── VarRender.py
│   │   └── allure_step_logger.py
│   ├── extend/script/
│   │   └── run_script.py
│   └── key_dir/
│       ├── README.txt
│       └── 生成随机手机号.py
└── hat-test-cases/                   # 测试用例 (13个文件)
    ├── context.yaml
    ├── README.md
    └── *.yaml (11个用例文件)
```

---

## 🌳 扩展方向

| 方向 | 说明 | 涉及文件 |
|-----|------|---------|
| API 测试 | 新增 ApiKeywords 类 | HAT/keywords/api_keywords.py |
| App 测试 | 接入 Appium | HAT/keywords/app_keywords.py |
| 更多浏览器 | Edge / Safari 支持 | HAT/context/WebCaseContext.py |
| 并行执行 | 用 pytest-xdist 并行跑 | conftest.py |
| 数据驱动增强 | CSV / JSON 数据源 | HAT/parse/ |
| 定时任务 | 集成到 CI/CD 流水线 | main.py + 部署配置 |

---

**✓ 框架与用例已完全解耦**
- 修改用例: 只需编辑 `hat-test-cases/*.yaml`
- 扩展功能: 只需编辑 `HAT/` 目录下的框架代码
- 元素定位维护: 只需编辑 `context.yaml`
