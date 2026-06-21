# HAT 测试框架完整分析报告

---

## 一、框架整体架构

这是一个基于 **Python + pytest + Selenium** 的**关键字驱动**的 Web 自动化测试框架（HAT = Hybrid Automation Testing）。核心设计思想是**将测试用例与代码分离**，测试人员只需编写 YAML/Excel 文件即可完成自动化测试，无需编写 Python 代码。

### 整体架构图

```
main.py (入口)
    │
    ├── pytest.main() 启动测试
    └── CasesPlugin (pytest 插件)
              │
              ▼
  ┌───────────────────────────────┐
  │   TestRunner.py (用例执行器)  │
  │  ├── 读取用例数据               │
  │  ├── 初始化浏览器/WebCaseContext│
  │  ├── 执行前置/后置脚本         │
  │  ├── 循环执行每一步骤           │
  │  └── 调用 Keywords 执行关键字   │
  └────────────┬──────────────────┘
               │
      ┌────────┴─────────┐
      ▼                ▼
  YamlCaseParser    ExcelCaseParser  (用例解析器)
      │                │
      └────────┬─────────┘
               ▼
           g_context (全局变量池)
               │
         ┌─────┴──────┐
         ▼              ▼
     Keywords      VarRender(模板渲染)
    (关键字库)    ({{变量名}} 替换)
         │
         ▼
     WebCaseContext (浏览器管理)
```

---

## 二、目录结构详解

```
day24/
├── main.py                              # 框架入口文件
│
├── HAT/                                 # 框架核心包
│   ├── core/                           # 核心调度模块
│   │   ├── TestRunner.py               # 用例执行引擎（核心）
│   │   ├── CasesPlugin.py              # pytest 自定义插件
│   │   ├── globalContext.py            # 全局变量管理器
│   │   └── __init__.py
│   │
│   ├── parse/                          # 用例解析模块
│   │   ├── YamlCaseParser.py         # YAML 用例解析器
│   │   ├── ExcelCaseParser.py        # Excel 用例解析器
│   │   ├── caseParser.py             # 统一调度入口
│   │   └── __init__.py
│   │
│   ├── keywords/                       # 关键字库模块
│   │   ├── web_keywords.py           # Web 自动化关键字（核心）
│   │   └── __init__.py
│   │
│   ├── context/                       # 上下文管理模块
│   │   ├── WebCaseContext.py        # 浏览器驱动管理器
│   │   └── __init__.py
│   │
│   ├── utils/                         # 工具类模块
│   │   ├── VarRender.py              # Jinja2 变量模板渲染
│   │   ├── allure_step_logger.py      # Allure 步骤+日志收集器
│   │   └── __init__.py
│   │
│   ├── extend/                        # 扩展模块
│   │   └── script/
│   │       └── run_script.py          # 动态执行 Python 脚本
│   │
│   ├── key_dir/                       # 自定义关键字目录
│   │   └── 输入内容.py                # 用户自定义关键字示例
│   │
│   └── logs/                          # 日志目录（自动生成）
│
├── examples/                            # 用例示例目录
│   ├── web-cases-yaml/                 # YAML 格式用例（基础）
│   ├── web-cases-yamlall/              # YAML 全流程用例（读书屋）
│   ├── web-cases-excel/                # Excel 格式用例
│   └── web-cases-ai/                   # AI 视觉驱动用例
│
└── examples_test/                      # 测试辅助代码
```

---

## 三、核心模块详解

### 3.1 入口层：main.py — 启动测试

**文件位置**：`day24/main.py:1-50

**作用**：程序的唯一入口，负责配置日志、启动 pytest、生成 Allure 报告。

**执行流程**：

```
1. 配置日志（loguru）：控制台输出 + 文件输出到 HAT/logs/
   └─ 日志级别由环境变量 HAT_LOG_LEVEL 控制（默认 DEBUG）
2. 启动 pytest 测试：
   ├─ 运行 ./HAT/core/TestRunner.py
   ├─ 传入自定义参数 --type=yaml / --cases=./examples/web-cases-yaml
   └─ 注册自定义插件 CasesPlugin()
3. 生成 Allure HTML 报告
4. combine_allure() → 生成单文件 HTML 报告（可离线查看）
```

**关键代码**：

```python
pytest.main(
    ['-v', '-s', '--capture=sys',
     '--clean-alluredir',
     '--alluredir=allure-results',
     './HAT/core/TestRunner.py',
     '--type=yaml',
     '--cases=./examples/web-cases-yaml'],
    plugins=[CasesPlugin()]
)
```

**关键技术点**：通过 `--type` 和 `--cases` 两个自定义命令行参数，动态控制运行哪一批用例。

---

### 3.2 插件层：CasesPlugin.py — pytest 自定义插件

**文件位置**：`day24/HAT/core/CasesPlugin.py:10-40`

**作用**：扩展 pytest 功能，实现**动态参数化**用例。

**核心方法**：

| 方法 | 作用 |
|------|------|
| `pytest_addoption` | 注册 `--type`、`--cases`、`--key_dir` 三个命令行参数 |
| `pytest_generate_tests` | **核心**：解析用例文件，将数据注入 `TestRunner.test_case_execute` 的参数中 |
| `pytest_collection_modifyitems` | 处理中文显示问题（避免乱码） |

**核心原理**：

```python
def pytest_generate_tests(self, metafunc):
    # 1. 拿到命令行参数（--type 和 --cases）
    case_type = metafunc.config.getoption("type")
    cases_dir = metafunc.config.getoption("cases")

    # 2. 解析 YAML/Excel → 得到所有用例数据列表
    data = case_parser(case_type, cases_dir)

    # 3. 将用例数据注入到测试函数的参数中
    if "caseinfo" in metafunc.fixturenames:
        metafunc.parametrize("caseinfo", data["case_infos"], ids=data["case_names"])
```

**设计效果**：1 个测试函数 → 运行 N 条用例，是数据驱动的关键。

---

### 3.3 核心执行引擎：TestRunner.py — 用例执行器

**文件位置**：`day24/HAT/core/TestRunner.py:24-120

**作用**：这是整个框架的**心脏**，`test_case_execute` 方法接收一条用例数据并完整执行它。

**执行步骤分解**：

```
1. 解析用例的基础配置 → 确定用例类型（WebCase）
   ↓
2. 初始化 WebCaseContext → 启动浏览器，创建 Keywords 对象
   ↓
3. 处理前置脚本 pre_script → 通过 exec() 动态执行 Python 代码
   ↓
4. 遍历【用例步骤】列表 → 对每一步：
   ├─ 4.1 用 VarRender.refresh() 渲染 {{变量名}} 模板
   ├─ 4.2 取 step_value["操作类型"] 作为关键字方法名
   ├─ 4.3 keywords.__getattribute__(key) → 反射找到方法
   └─ 4.4 key_func(**step_value) → 传参执行关键字
   ↓
5. 处理后置脚本（同前置脚本）
   ↓
6. finally: caseContext.release() → 截图轮播 + 关闭浏览器
```

**关键字驱动核心代码**：

```python
# 从 Keywords 类中按名字找方法（反射机制）
key = step_value["操作类型"]               # 例如: "访问网址"
key_func = keywords.__getattribute__(key)        # 找到 Keywords.访问网址 方法
key_func(**step_value)                     # 执行方法并传入所有参数
```

**设计意义**：用例写的是"访问网址"这个关键字名，框架通过反射自动找到对应函数来执行。

---

### 3.4 全局变量池：g_context — 全局数据共享

**文件位置**：`day24/HAT/core/globalContext.py:8-25`

**作用**：像一个共享的字典，让用例的不同步骤、不同用例之间能传递数据。

**核心实现**：

```python
class g_context:
    _dic = {}                              # 类属性：所有实例共享同一个字典

    def set_dict(self, key, value):          # 设置: g_context().set_dict("username", "123")
        self._dic[key] = value

    def get_dict(self, key):                # 获取: g_context().get_dict("username")
        return self._dic.get(key, None)

    def show_dict(self):                    # 获取全部: g_context().show_dict()
        return self._dic
```

**数据流向**：

```
context.yaml ──解析──▶ g_context._dic ◀──保存── 关键字方法(如获取文本)
                        ▲
                        │
                    VarRender 渲染 {{变量名}}
```

---

### 3.5 用例解析层

#### 3.5.1 YamlCaseParser.py — YAML 用例解析

**文件位置**：`day24/HAT/parse/YamlCaseParser.py`

**核心函数**：

| 函数 | 作用 |
|------|------|
| `read_yaml()` | 读取单个 YAML 文件 |
| `load_context_from_yaml()` | 读取 `context.yaml` → 注入 `g_context`（浏览器配置、元素定位、数据库配置等） |
| `load_yaml_files()` | 扫描文件夹，读取所有 `数字_xxx.yaml` 文件（按数字排序执行） |
| `yaml_case_parser()` | **核心**：处理数据驱动（DDT），把 1 个用例模板 + N 组数据 → 生成 N 条用例 |

**文件命名规则**：必须以**数字开头 + 下划线**命名（如 `1_loginsuccess.yaml`），数字决定执行顺序。

**数据驱动原理**：

```yaml
# 用例文件示例
用例步骤: [...]

数据驱动:
  - username: 15574113907
    password: 123456
    描述标题: 正常登陆

  - username: wronguser
    password: wrongpass
    描述标题: 账号错误
```

解析后生成 2 条独立用例，标题分别为"登陆用例-正常登陆"、"登陆用例-账号错误"。

#### 3.5.2 ExcelCaseParser.py — Excel 用例解析

**文件位置**：`day24/HAT/parse/ExcelCaseParser.py`

**作用**：将 Excel 格式的用例转换为**与 YAML 完全相同的数据结构**，这样 `TestRunner` 无需修改即可执行。

**核心函数**：

| 函数 | 作用 |
|------|------|
| `load_context_from_excel()` | 从 Excel 读取浏览器/数据库/元素配置 |
| `group_cases_by_title()` | 按用例标题归并行 → 组装成步骤列表 |
| `safe_convert_value()` | 智能转换字符串为 Python 类型（JSON/字面量） |
| `load_excel_files()` | 扫描文件夹读取符合规则的 Excel 文件 |
| `excel_case_parser()` | 统一入口，返回与 YAML 相同格式的数据 |

**Excel 用例格式**：每行一个步骤，相同用例标题的行归为同一个用例。

---

### 3.6 关键字库：Keywords 类

**文件位置**：`day24/HAT/keywords/web_keywords.py:27-597`

**作用**：这是测试人员最常扩展的地方，每个方法就是一个可在 YAML 中调用的"关键字"。

#### 关键字分类表

| 分类 | 关键字方法 | 功能 |
|------|-----------|------|
| **浏览器操作** | `访问网址` | driver.get(url) 打开网页 |
| | `关闭浏览器` | driver.quit() 关闭浏览器 |
| | `窗口最大化` | driver.maximize_window() 窗口最大化 |
| | `switch_to_latest_handle` | 切换到最新打开的窗口 |
| **元素操作** | `输入内容` | 找到元素并 send_keys 输入 |
| | `点击元素` | 找到元素并 click 点击 |
| | `find_element` | 从 `_WEB页面元素` 中取定位方式，显式等待找元素 |
| **等待** | `强制等待` | time.sleep(n) 强制等待 n 秒 |
| **断言** | `断言文本` | 通用文本断言（支持 8 种比较符） |
| | `断言文本相等/包含/不相等` | 文本断言快捷方式 |
| | `断言数字xxx` | 数字类型的各种比较（大于、小于、等于等） |
| | `断言浏览器路径` | 断言当前 URL 地址 |
| **数据提取** | `获取元素文本` | 获取元素文本并存入 g_context |
| | `提取数据MYSQL` | 执行 SQL 查询并把结果存入 g_context |
| **特殊操作** | `iframe_switch_to` | 切换到指定 iframe |
| | `image_recognition` | ddddocr 图片验证码识别 |
| | `random_six_digit_number` | 生成 6 位随机数 |
| **AI 能力** | `AI操作` | 截图 + 大模型视觉识别定位并点击/输入 |
| | `AI断言` | 截图 + 大模型视觉断言 |

#### 设计亮点 1：元素定位解耦

**文件位置**：`day24/HAT/keywords/web_keywords.py:52-74`

```python
def find_element(self, **kwargs):
    # 从全局变量中获取所有页面元素配置
    all_ele_data = g_context().get_dict("_WEB页面元素")

    # 用例中只写别名，不写具体定位方式
    key = str(kwargs["_页面元素"])          # 用例传 "手机号_输入框"
    ele_data = all_ele_data[key]           # 拿到 {定位方式: id, 目标对象: txtUName}

    # 根据定位方式查找元素（支持 id、name、class、xpath、css selector 等）
    locator_types = loctor_type.get(ele_data["定位方式"], None)
    locator = (locator_types, ele_data["目标对象"])
```

**优势**：用例只写 `_页面元素: 手机号_输入框`，真实定位方式存在 `context.yaml`，元素变更时只需修改配置文件，无需修改用例。

#### 设计亮点 2：扩展关键字机制

**文件位置**：`day24/HAT/keywords/web_keywords.py:590-597`

```python
def ex_invoke(self, **kwargs):
    key = kwargs["key"]                      # 关键字名
    if g_context().get_dict("key_dir") is not None:
        sys.path.append(g_context().get_dict("key_dir"))
        module = __import__(key)           # 动态导入模块
        class_ = getattr(module, key)       # 获取类
        key_func = class_(self.driver).__getattribute__(key)
        key_func(**kwargs["step_value"])
```

**使用方式**：在 `HAT/key_dir/` 目录下新建 Python 文件，类名即关键字名，框架自动加载。

---

### 3.7 浏览器上下文：WebCaseContext

**文件位置**：`day24/HAT/context/WebCaseContext.py:52-289`

**作用**：管理浏览器驱动的生命周期（创建、复用、销毁）。

**核心特性表

| 功能 | 实现方式 |
|------|---------|
| **多浏览器支持** | 通过映射表支持 Chrome、Firefox、IE、Remote (Selenium Grid) |
| **浏览器复用** | `session_reuse=True` 时，所有用例共用一个浏览器实例 |
| **Grid 远程执行** | 配置 `grid_url` 即走 `webdriver.Remote` |
| **自定义启动参数** | 从 context 读取 `options.args`（如 `--headless` 无头模式） |
| **截图轮播** | 每个步骤自动截图，最终在 Allure 报告中以 HTML 轮播形式回放 |

**浏览器配置示例**：

```python
driver_class = {
    "chrome":  {"driver": webdriver.Chrome, "service": Chrome_Service, ...},
    "firefox": {"driver": webdriver.Firefox, ...},
    "ie":      {"driver": webdriver.Ie, ...},
    "remote":  {"driver": webdriver.Remote, ...},
}
```

---

### 3.8 工具层

#### 3.8.1 VarRender.py — 模板变量渲染

**文件位置**：`day24/HAT/utils/VarRender.py:12-20`

**作用**：用 Jinja2 模板引擎替换字符串中的 `{{变量名}}`。

**核心代码**：

```python
def refresh(target, context):
    if target is None:
        return None
    return Template(str(target)).render(context)
```

**使用示例**：

```
模板字符串: "我的账号是,{{aname}}"
context 字典: {'aname': '15574113906'}
渲染结果:   "我的账号是,15574113906"
```

**设计意义**：实现了**步骤间数据传递：步骤 A 把结果存到 g_context，步骤 B 用 `{{变量名}}` 取出使用。

#### 3.8.2 allure_step_logger.py — 步骤+日志收集器

**文件位置**：`day24/HAT/utils/allure_step_logger.py:14-45`

**作用**：在 Allure 报告的每一步骤下显示该步骤的详细日志，方便排查。

**核心实现**：

```python
@contextmanager
def allure_step_with_log(step_name):
    token = _current_step_name.set(step_name)  # 存储当前步骤名称
    with allure.step(step_name):               # 在报告中创建步骤
        with StepLogCollector() as collector:  # 收集此步骤期间的日志
            yield collector                      # 执行测试代码
    _current_step_name.reset(token)             # 清理上下文
```

#### 3.8.3 run_script.py — 动态脚本执行

**文件位置**：`day24/HAT/extend/script/run_script.py:9-11`

**作用**：允许 YAML 用例中通过"前置脚本/后置脚本"字段写入 Python 代码。

**核心代码**：

```python
def exec_script(script, context):
    if script is None:
        return
    exec(script, {"context": context})
```

**使用场景**：设置变量、数据准备、环境清理等。

---

## 四、完整执行链路（从启动到结束）

以运行 `examples/web-cases-yaml/1_loginsuccess.yaml` 为例：

```
[1] main.py 启动
    │
    ▼
[2] pytest.main() 启动测试框架
    │
    ▼
[3] CasesPlugin.pytest_addoption
    └─ 注册 --type、--cases、--key_dir 参数
    │
    ▼
[4] CasesPlugin.pytest_generate_tests
    ├─ 拿到命令行参数 type=yaml, cases=./examples/web-cases-yaml
    ├─ case_parser() → yaml_case_parser()
    ├─ load_yaml_files()
    │   ├─ load_context_from_yaml() → 读取 context.yaml 注入 g_context
    │   └─ 扫描目录读取所有 数字_xxx.yaml 文件
    └─ 处理 DDT 数据驱动 → 生成 case_infos 列表
    │
    ▼
[5] 开始执行 TestRunner.test_case_execute(caseinfo=第一条用例)
    │
    ├─ [5.1] 解析 caseinfo["基础配置"] → 确定 WebCase 类型
    ├─ [5.2] WebCaseContext().init_keywords() → 启动浏览器 → new Keywords(driver)
    ├─ [5.3] eval(pre_script) + exec_script() → 执行前置脚本
    │
    ├─ [5.4] 遍历 caseinfo["用例步骤"]:
    │      步骤 1: "访问网址"
    │        ├─ VarRender.refresh() → 渲染模板变量
    │        ├─ eval() 解析字符串
    │        ├─ allure_step_with_log("访问网址")
    │        ├─ keywords.__getattribute__("访问网址") → 找到方法
    │        └─ 执行 → driver.get("http://novel.hctestedu.com/...")
    │
    │      步骤 2: "输入手机号关键字"
    │        └─ keywords.输入内容(_页面元素="手机号_输入框", 数据内容="15574113907")
    │           └─ find_element → send_keys
    │
    │      步骤 3: "点击登陆按钮" → keywords.点击元素(...)
    │      ...
    │      步骤 N: "断言" → keywords.断言文本(预期结果=..., 实际结果=...)
    │
    ├─ [5.5] 执行后置脚本
    │
    └─ [5.6] finally: caseContext.release() → 截图轮播 + 关闭浏览器
    │
    ▼
[6] 下一条用例 → 回到 [5] 继续
    │
    ▼
[7] 全部执行完毕 → allure generate 生成报告
    │
    ▼
[8] combine_allure() → 生成单文件 HTML 报告
```

---

## 五、用例文件格式详解（YAML）

### 5.1 context.yaml — 全局配置文件

**文件位置**：`day24/examples/web-cases-yaml/context.yaml`

**作用**：所有用例共享的全局配置，用例执行前自动加载到 g_context。

**完整字段说明**：

| 字段 | 说明 | 示例 |
|------|------|------|
| `session_reuse` | 是否复用浏览器（True=所有用例共用一个浏览器实例） | `False` |
| `key_dir` | 自定义关键字目录路径 | `./HAT/key_dir` |
| `_浏览器` | 浏览器驱动配置 | 见下方详情 |
| `_数据库` | 数据库连接配置（可多个） | 见下方详情 |
| `_WEB页面元素` | 页面元素定位配置 | 见下方详情 |
| 其他自定义变量 | 可直接写任意变量，用例中通过 `{{变量名}}` 引用 | `username: '15574113906' |

#### `_浏览器` 配置详解：

```yaml
_浏览器:
  grid_url: "http://192.168.1.102:4444/wd/hub"   # Selenium Grid 地址（可选，用于分布式执行）
  driver_path: "D:\\Python\\Python39\\chromedriver.exe"  # 本地驱动路径（可选）
  capability:
    browserName: "chrome"          # 浏览器名称: chrome/firefox/ie
  options:
    args:
      - "--headless"                 # 无头模式（可选）
      - "--disable-gpu"              # 禁用 GPU（可选）
```

#### `_数据库` 配置详解：

```yaml
_数据库:
  mysql001:                             # 数据库别名（用例中通过此别名引用）
    host: shop-xo.hctestedu.com       # 数据库主机地址
    port: 3306                       # 端口号
    user: api_test                     # 用户名
    password: Aa9999!               # 密码
    db: novel-plus                     # 数据库名
```

#### `_WEB页面元素` 配置详解：

```yaml
_WEB页面元素:
  手机号_输入框:                        # 元素别名（用例中使用）
    定位方式: id                       # 定位方式: id/name/class/xpath/css selector
    目标对象: txtUName                  # 定位值
  密码_输入框:
    定位方式: id
    目标对象: txtPassword
  登陆按钮:
    定位方式: id
    目标对象: btnLogin
```

---

### 5.2 用例文件结构

**通用模板**：

```yaml
基础配置:
  用例类型: WebCase                    # 用例类型（WebCase/AppCase/ApiCase）
  一级模块: 登陆模板                   # 报告中的大章节名称
  二级模块: 登陆功能                   # 报告中的小章节名称
  用例标题: 登陆用例                   # 报告中的用例名称

前置脚本: ""                           # Python 代码字符串（用例执行前运行）

后置脚本: ""                           # Python 代码字符串（用例执行后运行）

用例步骤:                              # 核心：步骤列表（按顺序执行）
  - 步骤描述:                         # 任意文字，仅显示在报告中
      操作类型: 访问网址               # 必须匹配 Keywords 类中的方法名
      网址: http://xxx                 # 方法参数（由关键字方法决定需要哪些参数）

  - 步骤描述:
      操作类型: 输入内容
      _页面元素: 手机号_输入框           # 通过别名查 context 的元素定位
      数据内容: '{{username}}'         # {{变量}} 会从 g_context 渲染

  - 步骤描述:
      操作类型: 点击元素
      _页面元素: 登陆按钮

  - 步骤描述:
      操作类型: 断言文本
      预期结果: '15574113907'
      实际结果: '{{login_success_name}}'

数据驱动:                            # 可选：DDT 数据（有多组时，每条数据生成独立用例）
  - username: 15574113907
    password: 123456
    描述标题: 正常登陆
  - username: wronguser
    password: wrongpass
    描述标题: 账号错误
```

**字段说明表**：

| 字段 | 是否必填 | 说明 |
|------|---------|------|
| `基础配置.用例类型` | 是 | 用例类型，目前支持 WebCase |
| `基础配置.一级模块` | 是 | Allure 报告中的功能模块名称 |
| `基础配置.二级模块` | 是 | Allure 报告中的子功能模块名称 |
| `基础配置.用例标题` | 是 | Allure 报告中显示的用例名称 |
| `前置脚本` | 否 | 用例执行前动态执行的 Python 代码 |
| `后置脚本` | 否 | 用例执行后动态执行的 Python 代码 |
| `用例步骤` | 是 | 步骤列表，按从上到下顺序执行 |
| `用例步骤[].操作类型` | 是 | 关键字方法名（必须与 Keywords 类中的方法名一致） |
| `数据驱动` | 否 | 数据驱动列表，每条数据生成一条独立用例 |
| `数据驱动[].描述标题` | 否 | 该条数据的描述，用于区分不同场景 |

---

## 六、核心技术总结

| 技术点 | 实现方式 | 所在文件 |
|--------|---------|---------|
| **测试框架** | pytest 7.x | main.py |
| **报告生成** | Allure + allure_combine | main.py, allure_step_logger.py |
| **浏览器驱动** | Selenium WebDriver + Grid | WebCaseContext.py |
| **关键字驱动** | `__getattribute__` 动态方法调用 | TestRunner.py:95 |
| **数据驱动** | pytest `parametrize` + YAML/Excel 解析 | CasesPlugin.py:33, YamlCaseParser.py |
| **全局变量** | 类属性字典共享数据 | globalContext.py |
| **模板渲染** | Jinja2 `Template.render` | VarRender.py |
| **动态脚本** | Python `exec()` | run_script.py |
| **动态模块加载** | `sys.path.append` + `__import__` | web_keywords.py:590 |
| **日志收集** | loguru | main.py, allure_step_logger.py |
| **AI 视觉能力** | OpenAI API + 视觉大模型 + PIL + 截图 | web_keywords.py:317-530 |
| **图片识别** | ddddocr | web_keywords.py:538 |
| **数据库操作** | pymysql DictCursor | web_keywords.py:236 |

---

## 七、扩展框架的三种方式

| 方式 | 操作步骤 | 适用场景 |
|------|---------|---------|
| **新增内置关键字** | 在 `Keywords` 类中添加方法 → 方法名即关键字名 | 通用操作，所有项目都可用 |
| **自定义关键字** | 在 `HAT/key_dir/` 下新建 Python 文件（类名=关键字名）→ 配置 `key_dir` 路径 | 项目特定操作，不想污染核心代码 |
| **自定义解析器** | 新增 `XxxCaseParser.py` → 在 `caseParser.py` 中注册新类型 | 支持新的用例文件格式 |

---

## 八、examples 示例目录详解

`examples/` 目录包含 4 种不同风格的用例示例，覆盖从简单到复杂的各种场景。

```
examples/
├── web-cases-yaml/          # 基础 YAML 用例（入门级）
├── web-cases-yamlall/       # 全流程 YAML 用例（读书屋完整业务）
├── web-cases-excel/         # Excel 格式用例
└── web-cases-ai/            # AI 视觉驱动用例
```

---

### 8.1 web-cases-yaml — 基础 YAML 用例

**目录位置**：`day24/examples/web-cases-yaml/`

**包含文件**：

| 文件名 | 作用 | 用例数 |
|--------|------|--------|
| `context.yaml` | 全局配置文件 | - |
| `1_loginsuccess.yaml` | 登录成功 + 数据库断言用例 | 1（DDT: 1 组数据） |
| `2_search.yaml` | 搜索书籍用例 | 1 |
| `loginfail.yaml` | 登录失败用例 | 1 |
| `stu.yaml` | YAML 语法学习示例 | - |

#### 8.1.1 context.yaml — 全局配置

**文件位置**：`day24/examples/web-cases-yaml/context.yaml`

```yaml
session_reuse: False              # 不复用浏览器，每个用例独立启动
key_dir: ./HAT/key_dir            # 自定义关键字目录

_浏览器:
  grid_url: "http://192.168.1.102:4444/wd/hub"
  capability:
    browserName: "chrome"

_数据库:
  mysql001:
    host: shop-xo.hctestedu.com
    port: 3306
    user: api_test
    password: Aa9999!
    db: novel-plus

_WEB页面元素:
  手机号_输入框:
    定位方式: id
    目标对象: txtUName
  密码_输入框:
    定位方式: id
    目标对象: txtPassword
  登陆按钮:
    定位方式: id
    目标对象: btnLogin
  登陆成功_实际结果:
    定位方式: xpath
    目标对象: //*[@id="headerUserInfo"]/span/a[1]
  搜索_输入框:
    定位方式: id
    目标对象: searchKey
  搜索按钮:
    定位方式: id
    目标对象: btnSearch
  获取书名值:
    定位方式: xpath
    目标对象: //*[@id="bookList"]/tr[1]/td[3]/a
```

**配置特点**：
- 浏览器配置了 Grid 远程执行地址（分布式执行）
- 配置了 mysql001 数据库连接
- 定义了登录页面和搜索页面的元素定位

#### 8.1.2 1_loginsuccess.yaml — 登录成功用例

**文件位置**：`day24/examples/web-cases-yaml/1_loginsuccess.yaml`

**用例概览**：访问登录页 → 输入账号密码 → 点击登录 → 获取用户名 → 断言文本 → 查询数据库 → 断言数据库结果

**用例步骤详解**：

| 步骤 | 操作类型 | 关键参数 | 说明 |
|------|---------|----------|------|
| 1 | `访问网址` | 网址: login.html | 打开登录页面 |
| 2 | `输入内容` | _页面元素: 手机号_输入框, 数据内容: `{{username}}` | 输入用户名 |
| 3 | `输入内容` | _页面元素: 密码_输入框, 数据内容: `{{password}}` | 输入密码 |
| 4 | `点击元素` | _页面元素: 登陆按钮 | 点击登录 |
| 5 | `强制等待` | 数据内容: 3 | 等待页面加载 |
| 6 | `获取元素文本` | _页面元素: 登陆成功_实际结果, 变量名: login_success_name | 取页面用户名存入变量 |
| 7 | `断言文本` | 预期结果: `{{expect}}`, 实际结果: `{{login_success_name}}` | 断言页面显示 |
| 8 | `断言文本相等` | 预期结果: `{{expect}}`, 实际结果: `{{login_success_name}}` | 二次断言（严格相等 |
| 9 | `提取数据MYSQL` | _数据库: mysql001, SQL: select... | 查询数据库 |
| 10 | `断言文本相等` | 预期结果: '15574113907', 实际结果: `{{username_1}}` | 断言数据库结果 |

**数据驱动数据**：

```yaml
数据驱动:
  - username: 15574113907
    password: 123456
    描述标题: 正常登陆
    expect: '15574113907'
```

**用例亮点**：
- 演示了 `{{变量名}}` 模板渲染的使用
- 演示了 `获取元素文本` 关键字提取页面数据
- 演示了 `提取数据MYSQL` 关键字查询数据库
- 演示了两种断言方式（断言文本 + 断言文本相等）

#### 8.1.3 2_search.yaml — 搜索书籍用例

**文件位置**：`day24/examples/web-cases-yaml/2_search.yaml`

**用例概览**：访问首页 → 输入搜索关键字 → 点击搜索 → 获取搜索结果 → 断言包含搜索词

**步骤简化版**：

| 步骤 | 操作 |
|------|------|
| 1 | 访问网址 http://novel.hctestedu.com/ |
| 2 | 输入内容「云上夕轮」到搜索框 |
| 3 | 点击搜索按钮 |
| 4 | 获取搜索结果第一本书的标题 → 存入变量 page_name |
| 5 | 断言文本包含「云上夕轮」 |

#### 8.1.4 loginfail.yaml — 登录失败用例

**文件位置**：`day24/examples/web-cases-yaml/loginfail.yaml`

**用例概览**：使用错误密码登录 → 验证登录失败场景

**步骤**：访问登录页 → 输入错误账号（15574110000）→ 输入密码 → 点击登录 → 等待

**注意**：此用例未写完整断言，仅演示输入操作的示例。

#### 8.1.5 stu.yaml — YAML 语法学习

**文件位置**：`day24/examples/web-cases-yaml/stu.yaml`

**作用**：学习 YAML 的基本语法，不执行。

**演示的 YAML 语法**：

```yaml
# 字典数据（键值对）
name: "yang"
age: 18

# 列表数据
- item1
- item2

# 列表嵌套字典
- name: "yang"
  age: 18

# 字典嵌套列表
name: "yang"
age: 18
info:
  - name: "yang"
    age: 18
```

---

### 8.2 web-cases-yamlall — 全流程 YAML 用例（读书屋）

**目录位置**：`day24/examples/web-cases-yamlall/`

**业务背景**：这是一个完整的「读书屋」（novel-plus）网站的端到端测试用例集，覆盖登录、搜索、加入书架、发布反馈、评论书籍、后台登录等完整业务流程。

**包含文件**：

| 文件名 | 业务场景 | 用例标题 |
|--------|---------|---------|
| `context.yaml` | 全局配置（含完整元素定位） | - |
| `0_DSW-登陆.yaml` | 用户登录 | 登陆测试用例 |
| `1_DSW-搜索书籍.yaml` | 搜索书籍功能 | 搜索用例 |
| `2_DSW-加入书架.yaml` | 加入书架功能 | 加入书架用例 |
| `3_DSW-发布我的反馈.yaml` | 用户反馈功能 | 反馈测试用例 |
| `4_DSW-评论书籍.yaml` | 评论书籍功能 | DSW-评论书籍 |
| `5_DSW-后台登陆.yaml` | 后台管理登录 | DSW-后台登录测试用例 |

**执行顺序**：按文件名前缀数字顺序执行（0→1→2→3→4→5），因为所有用例共用一个浏览器实例（`session_reuse: True`），形成完整的业务流程链。

#### 8.2.1 context.yaml — 读书屋全局配置

**文件位置**：`day24/examples/web-cases-yamlall/context.yaml`

**核心配置特点**：

```yaml
session_reuse: True          # 关键：浏览器复用，所有用例共用一个浏览器
_浏览器:
  capability:
    browserName: chrome     # 使用本地 Chrome 浏览器（无 Grid）

_数据库:
  dushuwu_mysql_1:         # 本地数据库（读书屋）
    host: 192.168.1.111
    port: 3306
    user: root
    password: root
    db: novel_plus

# 自定义全局变量（用例中通过 {{变量名}} 引用）
username: '15096268001'      # 测试账号
password: '123456'
feedbackData: 柚一的反馈内容   # 反馈测试数据

# 完整的页面元素定位（覆盖所有业务页面）
_WEB页面元素:
  # 登录页面元素
  手机号_输入框: {定位方式: id, 目标对象: txtUName}
  密码_输入框: {定位方式: id, 目标对象: txtPassword}
  登陆_按钮: {定位方式: id, 目标对象: btnLogin}

  # 搜索页面元素
  书籍搜索框: {定位方式: id, 目标对象: searchKey}
  书籍搜索按钮: {定位方式: xpath, 目标对象: //*[@id="btnSearch"]/i}
  搜索列表书籍-第一本书: {定位方式: xpath, 目标对象: //*[@id="bookList"]/tr[1]/td[3]}

  # 我的书架页面元素
  我的书架: {定位方式: xpath, 目标对象: //*[@id="headerUserInfo"]/a}
  我的书架最新书名: {定位方式: xpath, 目标对象: //*[@id="bookShelfList"]/tr[1]/td[2]/a}
  我的书架最新-继续阅读: {定位方式: xpath, 目标对象: //*[@id="bookShelfList"]/tr[1]/td[5]/a}
  加入书架按钮: {定位方式: xpath, 目标对象: //*[@id="headerUserInfo"]/a}

  # 反馈页面元素
  点击我的书架: {定位方式: xpath, 目标对象: //*[text()='我的书架']}
  点击我的反馈: {定位方式: xpath, 目标对象: //a[text()='我的反馈']}
  点击反馈_按钮: {定位方式: xpath, 目标对象: //a[text()='写反馈']}
  输入反馈内容: {定位方式: id, 目标对象: txtDescription}
  点击反馈提交按钮: {定位方式: id, 目标对象: btnSave}
  检查是否反馈成功: {定位方式: xpath, 目标对象: //*[@id="feedbackList"]/div/ul/li[2]}

  # 评论页面元素
  评价按钮: {定位方式: xpath, 目标对象: //*[@id="showDetail"]/div[1]/div/div[1]/div[1]/ul/li[5]/a/b}
  发布评价: {定位方式: xpath, 目标对象: /html/body/div[2]/div/div[1]/div/div/div/div[1]/a}
  评价文本框: {定位方式: id, 目标对象: txtComment}
  发表按钮: {定位方式: xpath, 目标对象: //*[@id="reply_bar"]/div[2]/span[2]/a}
  评价成功弹窗信息: {定位方式: xpath, 目标对象: //*[@id="layui-layer1"]/div[2]}

  # 后台管理页面元素
  后台用户名: {定位方式: name, 目标对象: username}
  后台密码: {定位方式: name, 目标对象: password}
  后台登陆按钮: {定位方式: id, 目标对象: login}
  后台验证码: {定位方式: id, 目标对象: imgVerify}
  输入验证码: {定位方式: id, 目标对象: verify}
  ...
```

**设计亮点**：
- `session_reuse: True` → 所有 6 个用例在同一个浏览器中顺序执行，模拟真实用户连续操作
- 完整的元素定位命名规范，便于维护
- 自定义变量 `username`、`password`、`feedbackData` 集中管理测试数据

#### 8.2.2 0_DSW-登陆.yaml — 用户登录用例

**文件位置**：`day24/examples/web-cases-yamlall/0_DSW-登陆.yaml`

**测试场景**：验证用户登录功能，并断言登录后跳转到首页。

**用例配置**：

```yaml
基础配置:
  用例类型: WebCase
  一级模块: 我的登陆
  二级模块: 登陆功能
  用例标题: 登陆测试用例
```

**执行步骤详解**：

| 步骤序号 | 操作类型 | 参数 | 作用 |
|--------|---------|------|------|
| 1 | 访问网址 | 网址: login.html | 打开登录页面 |
| 2 | 输入内容 | _页面元素: 手机号_输入框, 数据内容: `{{username}}` | 输入用户名（从 context 取） |
| 3 | 输入内容 | _页面元素: 密码_输入框, 数据内容: `{{password}}` | 输入密码 |
| 4 | 强制等待 | 数据内容: '3' | 等待 3 秒 |
| 5 | 点击元素 | _页面元素: 登陆_按钮 | 点击登录按钮 |
| 6 | 断言浏览器路径 | 数据内容: `{{expect}}` | 断言是否跳转到首页 |
| 7 | 强制等待 | 数据内容: '3' | 等待页面加载完成 |

**数据驱动**：

```yaml
数据驱动:
  - username: 13800138001
    password: 123456
    描述标题: 用户名和密码都正确
    expect: http://novel.hctestedu.com/
```

**用例亮点**：
- 使用 `{{username}}`、`{{password}}` 从 context 读取测试数据
- 使用 `断言浏览器路径` 关键字验证登录跳转

**流程链作用**：此用例执行成功后，浏览器保持登录状态，后续用例（1-5）继续在已登录状态下操作。

#### 8.2.3 1_DSW-搜索书籍.yaml — 搜索书籍用例

**文件位置**：`day24/examples/web-cases-yamlall/1_DSW-搜索书籍.yaml`

**测试场景**：在已登录状态下搜索书籍并验证搜索结果。

**用例配置**：

```yaml
基础配置:
  一级模块: 我的登陆
  二级模块: 登陆功能
  用例标题: 登陆测试用例
```

**执行步骤**：

| 步骤 | 操作类型 | 参数 | 作用 |
|------|---------|------|------|
| 1 | 输入内容 | _页面元素: 书籍搜索框, 数据内容: `{{bookName}}` | 在搜索框输入书名 |
| 2 | 点击元素 | _页面元素: 书籍搜索按钮 | 点击搜索 |
| 3 | 获取元素文本 | _页面元素: 搜索列表书籍-第一本书, 变量名: page_name | 获取第一本书名存入变量 |
| 4 | 断言文本包含 | 预期结果: `{{bookName}}`, 实际结果: `{{page_name}}` | 断言搜索结果包含关键字 |
| 5 | 强制等待 | 数据内容: '3' | 等待 |

**数据驱动**：

```yaml
数据驱动:
  - bookName: 同一天天
```

**用例亮点**：
- 演示了 `断言文本包含` 关键字（模糊匹配断言）
- 演示了 `获取元素文本` + 变量传递的完整流程

#### 8.2.4 2_DSW-加入书架.yaml — 加入书架用例

**文件位置**：`day24/examples/web-cases-yamlall/2_DSW-加入书架.yaml`

**测试场景**：从搜索结果中点击书籍 → 加入书架 → 验证书架中有此书。

**执行步骤**：

| 步骤 | 操作 |
|------|------|
| 1 | 点击搜索结果中的第一本书 |
| 2 | 等待 3 秒 |
| 3 | 点击「加入书架」按钮 |
| 4 | 点击「我的书架」进入书架页面 |
| 5 | 获取书架中最新书名 → 存入变量 page_name |
| 6 | 断言书架中书名包含 `{{bookName}}` |
| 7 | 等待 3 秒 |

**用例亮点**：
- 演示了跨页面数据验证（搜索页 → 详情页 → 书架页）
- 演示了页面跳转后的断言验证

#### 8.2.5 3_DSW-发布我的反馈.yaml — 用户反馈用例

**文件位置**：`day24/examples/web-cases-yamlall/3_DSW-发布我的反馈.yaml`

**测试场景**：用户发布反馈内容并验证。

**执行步骤**：

| 步骤 | 操作 |
|------|------|
| 1 | 点击「我的书架」导航链接 |
| 2 | 等待 3 秒 |
| 3 | 点击「我的反馈」 |
| 4 | 点击「写反馈」按钮 |
| 5 | 等待 3 秒 |
| 6 | 在反馈内容文本框输入 `{{feedbackData}}`（从 context 读取） |
| 7 | 点击「提交」按钮 |
| 8 | 获取反馈列表中最新反馈文本 → 存入变量 page_name |
| 9 | 断言反馈内容包含 `{{feedbackData}}` |
| 10 | 等待 1 秒 |

**用例亮点**：
- 演示了文本输入 + 列表断言的完整业务流程
- 使用 context 中的变量 `{{feedbackData}}` 作为测试数据

#### 8.2.6 4_DSW-评论书籍.yaml — 评论书籍用例

**文件位置**：`day24/examples/web-cases-yamlall/4_DSW-评论书籍.yaml`

**测试场景**：从书架进入书籍详情页 → 评价书籍 → 验证评价成功。

**执行步骤**：

| 步骤 | 操作 |
|------|------|
| 1 | 点击「我的书架」 |
| 2 | 点击「继续阅读」进入书籍详情页 |
| 3 | 点击「评价」按钮 |
| 4 | 点击「发表评价」链接 |
| 5 | 在评价文本框输入「柚一来评价」 |
| 6 | 等待 1 秒 |
| 7 | 点击「发表」按钮 |
| 8 | 获取评价成功弹窗文本 → 存入变量 page_name |
| 9 | 断言弹窗文本包含「已评价过该书籍！」 |
| 10 | 等待 3 秒 |

**用例亮点**：
- 演示了弹窗文本断言（验证操作成功提示

#### 8.2.7 5_DSW-后台登陆.yaml — 后台管理登录用例

**文件位置**：`day24/examples/web-cases-yamlall/5_DSW-后台登陆.yaml`

**测试场景**：登录后台管理系统，包含图片验证码识别。

**执行步骤**：

| 步骤 | 操作类型 | 参数 |
|------|---------|------|
| 1 | 访问网址 | 网址: http://novel-admin.hctestedu.com/login |
| 2 | 输入内容 | _页面元素: 后台用户名, 数据内容: 测试权限账号 |
| 3 | 输入内容 | _页面元素: 后台密码, 数据内容: ceshiquanxianzhanghao |
| 4 | image_recognition | _页面元素: 后台验证码, 引用变量: codeData | **图片验证码识别** → 结果存入 codeData |
| 5 | 输入内容 | _页面元素: 输入验证码, 数据内容: `{{codeData}}` | 输入识别出的验证码 |
| 6 | 点击元素 | _页面元素: 后台登陆按钮 |
| 7 | 强制等待 | 数据内容: '3' |

**用例亮点**：
- 演示了 `image_recognition` 关键字（ddddocr 图片验证码识别）
- 演示了验证码识别结果通过变量 `{{codeData}}` 传递到输入步骤

---

### 8.3 web-cases-excel — Excel 格式用例

**目录位置**：`day24/examples/web-cases-excel/`

**包含文件**：

| 文件名 | 作用 |
|--------|------|
| `context.xlsx` | Excel 格式的全局配置 |
| `1_WEB测试用例.xlsx` | Excel 格式的用例数据 |

**特点说明**：
- Excel 用例通过 `ExcelCaseParser` 解析后，转换为与 YAML 完全相同的数据结构
- 适合不熟悉 YAML 语法的测试人员使用
- 用例格式：每行一个步骤，相同用例标题的行归为同一个用例

**Excel 列结构**（参考 `ExcelCaseParser.group_cases_by_title`）：

| 列名 | 说明 |
|------|------|
| 模块 | 一级模块名称 |
| 功能 | 二级模块名称 |
| 用例标题 | 用例名称（相同标题的行归为同一用例） |
| 测试步骤 | 步骤描述文字 |
| 操作类型 | 关键字方法名 |
| 数据内容 | 操作参数（支持 key=value 格式，如 "网址=http://xxx"） |

---

### 8.4 web-cases-ai — AI 视觉驱动用例

**目录位置**：`day24/examples/web-cases-ai/`

**包含文件**：

| 文件名 | 作用 |
|--------|------|
| `context.yaml` | AI 用例全局配置 |
| `1_loginsuccess.yaml` | AI 登录用例（视觉识别操作） |
| `2_search.yaml` | AI 搜索用例 |

**核心特点**：不依赖元素定位，通过 AI 视觉识别页面元素并执行操作。

#### 8.4.1 context.yaml — AI 用例配置

**文件位置**：`day24/examples/web-cases-ai/context.yaml`

```yaml
session_reuse: False

# AI 大模型配置（通义千问视觉模型）
HAT_LLM_BASE_URL: "https://dashscope.aliyuncs.com/compatible-mode/v1"
HAT_LLM_API_KEY: "sk-95b8edb637a94805814f9b299faa16e1"
HAT_LLM_MODEL_NAME: "qwen-vl-max-latest"

_浏览器:
  driver_path: "D:\\Python\\Python39\\chromedriver.exe"
  capability:
    browserName: "chrome"
  options:
    args:
      - "--high-dpi-support=1"        # 启用高 DPI 支持
      - "--force-device-scale-factor=1"  # 强制设备缩放比为 1
```

**配置说明**：
- 使用通义千问 qwen-vl-max-latest 视觉大模型
- 配置高 DPI 支持，确保截图清晰度，便于 AI 识别
- API Key 需要替换为自己的有效 Key

#### 8.4.2 1_loginsuccess.yaml — AI 登录用例

**文件位置**：`day24/examples/web-cases-ai/1_loginsuccess.yaml`

**核心区别**：所有元素操作不使用 `_页面元素`（无需写元素定位，由 AI 视觉识别完成。

**执行步骤**：

| 步骤 | 操作类型 | 参数 |
|------|---------|------|
| 1 | 访问网址 | 网址: login.html |
| 2 | AI操作 | 操作描述: "在手机号码输入框中输入 `{{username}}`" | **AI 识别输入框位置并输入 |
| 3 | 强制等待 | 数据内容: 1 |
| 4 | AI操作 | 操作描述: "在密码输入框中输入 `{{password}}`" | AI 识别密码框并输入 |
| 5 | 强制等待 | 数据内容: 1 |
| 6 | AI操作 | 操作描述: "点击登陆按钮" | AI 识别按钮位置并点击 |
| 7 | AI断言 | 操作描述: `{{expect}}` | **AI 视觉断言验证结果 |

**数据驱动**：

```yaml
数据驱动:
  - username: 15574113907
    password: 123456
    expect: 检查页面右上角我的书架旁边是否包含 15574113907 的账号
  - username: 15574113907
    password: 223456
    expect: 检查页面登陆读书屋下面的提示框中是否包含"手机号或密码错误！"
```

**AI 操作原理**（`Keywords.AI操作`）：

```
1. 调用 driver.get_screenshot_as_base64() → 获取当前页面截图
2. 截图 + 操作描述文本 → 发送给通义千问视觉大模型
3. 大模型返回识别到的元素坐标 bbox 和动作类型（点击/输入/文本提取）
4. 根据返回结果执行对应操作（坐标点击/输入文本/提取文本）
```

**AI 断言原理**（`Keywords.AI断言`）：

```
1. 截图 + 断言描述 → 发送给大模型
2. 大模型返回判断结果（true/false）+ 判断依据
3. 框架根据返回结果决定用例是否通过
```

**用例亮点**：
- 无需编写任何元素定位代码（无需写 id/xpath 等）
- AI 自动识别页面元素
- 支持自然语言描述操作
- 适用于元素定位困难的场景（如动态页面、canvas、canvas 等）

#### 8.4.3 2_search.yaml — AI 搜索用例

**文件位置**：`day24/examples/web-cases-ai/2_search.yaml`

**执行步骤**：

| 步骤 | 操作类型 | 参数 |
|------|---------|------|
| 1 | 访问网址 | 网址: http://novel.hctestedu.com/ |
| 2 | AI操作 | 操作描述: "在书名输入框中输入'云上夕轮" |
| 3 | 强制等待 | 数据内容: 1 |
| 4 | AI操作 | 操作描述: "点击搜索按钮" |
| 5 | AI断言 | 操作描述: "检查页面全部作品中是否包含"云上夕轮"这本书名" |

---

## 九、HAT/key_dir — 自定义关键字示例

**目录位置**：`day24/HAT/key_dir/`

**作用**：存放自定义关键字，框架会自动加载。

#### 输入内容.py — 自定义关键字示例

**文件位置**：`day24/HAT/key_dir/输入内容.py`

```python
class 输入内容(Keywords):
    @allure.step("输入内容")
    def 输入内容(self, **kwargs):
        self.show_log("输入数据显示出来", kwargs)
        eles_list = self.find_element(**kwargs)
        eles_list.send_keys(kwargs["数据内容"])
        self.get_screenshot()
```

**使用方式**：
1. 在 `context.yaml` 中配置 `key_dir: ./HAT/key_dir`
2. 在 YAML 用例中写 `操作类型: 输入内容`
3. 框架会从 key_dir 目录动态加载此类

**适用场景**：
- 项目特定的操作逻辑
- 不想修改核心 Keywords 类代码
- 团队协作时隔离各自的关键字实现

---

## 十、框架使用快速开始

### 10.1 运行基础 YAML 用例

```bash
# 1. 确保已安装依赖
pip install pytest==7.1.3
pip install allure-pytest==2.13.5
pip install selenium
pip install loguru
pip install pyyaml
pip install jinja2
pip install pymysql
pip install ddddocr
pip install pandas
pip install openai
pip install pillow
pip install qwen-vl-utils

# 2. 运行
cd day24
python main.py

# 3. 查看报告
# 报告生成在 allure-report/ 目录
```

### 10.2 修改 main.py 切换用例类型

修改 `main.py` 中的参数：

```python
# 运行基础 YAML 用例
'--type=yaml',
'--cases=./examples/web-cases-yaml',

# 运行全流程 YAML 用例
'--type=yaml',
'--cases=./examples/web-cases-yamlall',

# 运行 Excel 用例
'--type=excel',
'--cases=./examples/web-cases-excel',

# 运行 AI 用例（需配置 API Key）
'--type=yaml',
'--cases=./examples/web-cases-ai',
```

### 10.3 编写你的第一个用例

1. 在 `examples/web-cases-yaml/` 下新建 `3_我的用例.yaml`
2. 参考 `1_loginsuccess.yaml` 格式编写步骤
3. 修改 `context.yaml` 补充需要的元素定位
4. 运行 `python main.py

---

**总结**：这是一个设计良好的企业级 Web 自动化测试框架，核心优势是**测试与代码完全分离，非开发人员也能通过 YAML/Excel 编写自动化用例，支持关键字驱动、数据驱动、AI 视觉驱动三种自动化方式。
