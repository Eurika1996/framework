# CSGClaw UI 自动化测试用例集

> 基于 HAT 测试框架（Python + pytest + Selenium + 关键字驱动）为 CSGClaw 多智能体平台编写的 UI 自动化测试用例。

---

## 一、项目概述

本项目为 **CSGClaw**（基于 Go + React/TypeScript 的本地多智能体协作平台）提供了完整的 UI 自动化测试用例集。

### 覆盖模块

| 模块 | 说明 | 用例数量 |
|------|------|---------|
| 服务启动与页面加载 | 验证服务启动成功、首页正确加载 | 1 |
| Agent 管理 | 智能体列表、创建、详情查看 | 3 |
| 对话功能 | 消息发送、新建对话 | 2 |
| 房间管理 | 房间列表、创建房间 | 1 |
| Hub 集成 | Hub 列表、创建 Hub | 1 |
| 计算机工作区 | 工作区信息展示 | 1 |
| 用户管理 | 用户列表展示 | 1 |
| 端到端完整流程 | 从创建 Agent 到对话的完整流程 | 1 |
| 数据清理 | 删除测试过程中产生的数据 | 1 |

**总计: 11 个 YAML 用例文件 + 1 个 Excel 示例 + 1 份全局配置**

---

## 二、目录结构

```
ui_auto_testing/
├── main.py                              # 测试入口脚本
├── generate_excel_cases.py              # Excel 用例生成脚本
│
├── hat-test-cases/                      # 测试用例目录
│   ├── context.yaml                     # 全局配置（浏览器、元素定位、变量）
│   │
│   ├── 0_服务启动与页面加载.yaml        # 基础验证用例
│   ├── 1_Agent列表页面.yaml             # Agent 列表验证
│   ├── 2_创建新Agent.yaml               # 创建 Agent 功能
│   ├── 3_查看Agent详情.yaml             # Agent 详情查看
│   ├── 4_对话发送消息.yaml              # 消息发送测试
│   ├── 5_新建对话.yaml                  # 新建对话/房间
│   ├── 6_房间管理.yaml                  # 房间创建与验证
│   ├── 7_Hub管理.yaml                   # Hub 集成功能
│   ├── 8_计算机工作区.yaml              # 工作区验证
│   ├── 9_用户管理.yaml                  # 用户管理页面
│   ├── 10_完整端到端流程.yaml           # E2E 完整流程测试
│   └── 11_清理测试Agent.yaml            # 测试数据清理
│
└── [HAT框架目录]                        # 需要与 HAT 框架配合使用
    ├── HAT/core/                        # 框架核心（TestRunner.py 等）
    ├── HAT/parse/                       # 用例解析器（YAML/Excel）
    ├── HAT/keywords/                    # 关键字库（web_keywords.py）
    └── HAT/utils/                       # 工具类（变量渲染、日志等）
```

---

## 三、关键字说明

以下是用例中使用的核心关键字（在 HAT 框架的 `web_keywords.py` 中实现）：

| 关键字 | 功能说明 | 参数示例 |
|--------|---------|---------|
| `访问网址` | 打开指定 URL | `网址: http://127.0.0.1:18080` |
| `输入内容` | 在指定元素中输入文本 | `_页面元素: Agent_名称输入框, 数据内容: "测试Agent"` |
| `点击元素` | 点击指定元素 | `_页面元素: Agent_保存按钮` |
| `强制等待` | 等待指定秒数 | `数据内容: "3"` |
| `获取元素文本` | 获取元素文本并存入变量 | `_页面元素: Agent_列表容器, 变量名: list_text` |
| `断言文本` | 通用文本断言 | `预期结果: "xxx", 实际结果: "{{var}}"` |
| `断言文本包含` | 断言文本包含指定内容 | `预期结果: "测试", 实际结果: "{{list_text}}"` |
| `断言文本不包含` | 断言文本不包含指定内容 | `预期结果: "测试", 实际结果: "{{list_text}}"` |
| `断言浏览器路径` | 断言当前页面 URL | `数据内容: "http://xxx"` |

### 变量渲染机制

使用 `{{变量名}}` 语法实现步骤间数据传递：
- 从 `context.yaml` 的全局变量获取: `{{base_url}}`、`{{test_agent_name}}`
- 从 `数据驱动` 获取当前测试数据: `{{test_message}}`
- 从前面步骤通过 `获取元素文本` 存入的变量: `{{agent_list_content}}`

---

## 四、快速开始

### 前置条件

1. **Python 3.7+**
2. **Chrome 浏览器** + **chromedriver**（版本需与 Chrome 匹配）
3. **HAT 测试框架**（Python + pytest + Selenium 关键字驱动框架）
4. **CSGClaw 服务已启动**:
   ```bash
   csgclaw serve
   # 默认服务地址: http://127.0.0.1:18080
   ```

### 安装依赖

```bash
pip install pytest selenium pyyaml openpyxl allure-pytest
pip install allure-combine   # 可选：用于生成单文件 HTML 报告
```

### 运行测试

```bash
# 方式一：使用入口脚本运行所有 YAML 用例
python main.py

# 方式二：指定用例目录
python main.py --cases ./hat-test-cases

# 方式三：运行 Excel 格式用例（需先生成 Excel 文件）
python generate_excel_cases.py
python main.py --type excel
```

### 查看测试报告

```bash
# 使用 allure CLI 生成 HTML 报告
allure generate ./allure-results -o ./allure-report --clean

# 如需单文件 HTML 报告（需安装 allure-combine）
allure-combine ./allure-report
```

---

## 五、用例编写规范

### YAML 用例结构模板

```yaml
基础配置:
  用例类型: WebCase                    # 必填
  一级模块: 模块名称                    # Allure 报告分组
  二级模块: 子功能名称                  # Allure 报告子分组
  用例标题: 用例说明                    # Allure 报告用例名

前置脚本: ""                           # 可选: Python 代码字符串
后置脚本: ""                           # 可选: Python 代码字符串

用例步骤:
  - 步骤描述: 步骤1说明
      操作类型: 关键字名                # 必须与 web_keywords.py 中的方法名匹配
      参数名1: 参数值1
      参数名2: 参数值2

  - 步骤描述: 步骤2说明
      操作类型: 关键字名
      参数名: '{{变量名}}'              # 使用变量渲染

数据驱动:                               # 可选: 多组数据并行执行
  - description: 场景1说明
    参数1: 值1
    参数2: 值2
  - description: 场景2说明
    参数1: 值3
    参数2: 值4
```

### 元素定位管理规范

所有页面元素定位集中在 `context.yaml` 的 `_WEB页面元素` 中，按模块分组：

```yaml
_WEB页面元素:
  Agent_名称输入框:
    定位方式: css                     # css / id / name / xpath / tag
    目标对象: "input[name='name']"
```

**优点**: 页面元素变更时只需修改 `context.yaml` 一处，无需修改各用例文件。

---

## 六、用例执行顺序

用例文件名的**数字前缀**决定执行顺序（配合 `session_reuse: True` 可复用同一浏览器实例）：

```
0_*  → 服务基础验证
1_*  → Agent列表
2_*  → 创建Agent
3_*  → 查看Agent详情
4_*  → 对话功能
5_*  → 新建对话
6_*  → 房间管理
7_*  → Hub管理
8_*  → 计算机工作区
9_*  → 用户管理
10_* → 完整端到端流程
11_* → 数据清理
```

---

## 七、扩展与维护

### 添加新模块测试

1. 在 `context.yaml` 的 `_WEB页面元素` 中添加新模块的元素定位
2. 创建 `{序号}_{模块名称}.yaml` 用例文件
3. 运行测试验证

### 修改元素定位

页面改版导致元素定位失效时，只需修改 `context.yaml` 中对应元素的 `定位方式` 和 `目标对象`。

### 添加自定义关键字

在 HAT 框架的 `HAT/key_dir/` 目录下添加 Python 类文件，类名即关键字名：

```python
class 自定义关键字:
    def __init__(self, driver):
        self.driver = driver

    def 自定义关键字(self, **kwargs):
        # 实现自定义操作
        pass
```

---

## 八、注意事项

1. **服务启动**: 运行测试前必须确保 `csgclaw serve` 已启动，服务地址与 `context.yaml` 中的 `base_url` 匹配。
2. **浏览器复用**: `session_reuse: True` 会在所有用例间复用同一浏览器窗口；如需独立环境，设为 `False`。
3. **等待时间**: 用例中的 `强制等待` 时间根据网络和服务性能可适当调整（AI 响应建议 8-15 秒）。
4. **元素定位**: CSS 选择器与 XPath 是最灵活的定位方式，但依赖具体页面实现。建议先通过浏览器开发者工具验证定位表达式。
5. **测试数据清理**: `11_清理测试Agent.yaml` 用于删除测试创建的数据，建议在完整测试套件末尾执行。
6. **AI 响应断言**: 对话功能的断言基于消息列表是否包含用户输入内容，不依赖 AI 具体回复内容，提高用例稳定性。

---

## 九、相关文档

- **CSGClaw 项目**: 位于 `./csgclaw/` 目录
- **HAT 框架说明**: `ui自动化框架.md`
- **测试入口脚本**: `main.py`
- **Excel 用例生成**: `generate_excel_cases.py`
