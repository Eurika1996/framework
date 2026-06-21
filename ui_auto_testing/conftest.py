"""
HAT 框架配置 - pytest conftest.py

作用:
1. 注册 --type / --cases / --key-dir 命令行参数
2. 解析 YAML/Excel 用例文件，动态参数化测试函数
3. 处理中文显示问题
4. 注册 CasesPlugin 插件

⚠ 核心机制: pytest 通过 conftest.py 自动识别以下钩子函数:
   - pytest_addoption: 注册自定义 CLI 参数
   - pytest_generate_tests: 解析用例并注入参数化 fixture
   - pytest_configure: 全局配置钩子
   - pytest_collection_modifyitems: 收集项后处理

用例执行流程:
    python main.py → subprocess 调用 pytest → conftest.py 注册参数
    → pytest_generate_tests 解析 YAML → test_case_execute(caseinfo)
"""
from __future__ import annotations

import sys
import os

# 确保项目根目录在 path 中
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

# 先确保 UTF-8 编码
os.environ["PYTHONIOENCODING"] = "utf-8"
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from HAT.core.CasesPlugin import CasesPlugin  # noqa: F401  保留导入，便于将来扩展
# 注意：钩子直接在 conftest.py 顶层函数实现，不注册 CasesPlugin 实例，
# 否则 CasesPlugin 的同名钩子也会被调用，导致双重参数化。


# ---------------------------------------------------------------------------
# 1. 注册插件实例到 pytest pluginmanager（保留空实现，供将来扩展）
# ---------------------------------------------------------------------------


def pytest_configure(config):
    """pytest 启动钩子，注册 marker 名称"""
    config.addinivalue_line(
        "markers",
        "hat_ui: HAT 框架 UI 自动化测试用例",
    )


# ---------------------------------------------------------------------------
# 2. 注册命令行参数（让 pytest 认识 --type / --cases / --key-dir）
# ---------------------------------------------------------------------------
def pytest_addoption(parser):
    """注册 HAT 框架的自定义命令行参数"""
    group = parser.getgroup("hat", "HAT 框架参数")
    group.addoption(
        "--type",
        action="store",
        default="yaml",
        choices=["yaml", "excel"],
        help="用例文件类型: yaml / excel (默认 yaml)",
    )
    group.addoption(
        "--cases",
        action="store",
        default="./hat-test-cases",
        help="用例文件目录路径 (默认 ./hat-test-cases)",
    )
    group.addoption(
        "--key-dir",
        "--key_dir",
        action="store",
        default=None,
        help="自定义关键字目录路径 (可选)",
    )


# ---------------------------------------------------------------------------
# 3. 解析用例并参数化注入 test_case_execute(caseinfo)
# ---------------------------------------------------------------------------
def pytest_generate_tests(metafunc):
    """核心钩子：解析 YAML/Excel 用例文件，为每条用例生成一个测试

    被测试函数：HAT.core.TestRunner.test_case_execute(caseinfo)
    """
    # 只有参数包含 "caseinfo" fixture 的测试函数才处理
    if "caseinfo" not in metafunc.fixturenames:
        return

    # 1. 获取命令行参数
    case_type = metafunc.config.getoption("type") or "yaml"
    cases_dir = metafunc.config.getoption("cases") or "./hat-test-cases"
    key_dir = metafunc.config.getoption("key_dir")

    # 2. 将配置写入全局变量池（供运行时使用）
    from HAT.core.globalContext import g_context
    g_context().set_dict("case_type", case_type)
    g_context().set_dict("cases_dir", cases_dir)
    if key_dir:
        g_context().set_dict("key_dir", key_dir)

    # 3. 解析用例文件
    from HAT.parse.caseParser import case_parser

    abs_cases_dir = os.path.abspath(cases_dir)
    parsed = case_parser(case_type, abs_cases_dir)

    case_infos = parsed["case_infos"]
    case_names = parsed["case_names"]

    # 4. 注入参数到 pytest（parametrize）
    if not case_infos:
        # 无可用用例时，注入一个占位用例，标记为 skip 避免红
        metafunc.parametrize(
            "caseinfo",
            [{"基础配置": {"用例标题": "无可用用例"},
              "_is_placeholder": True,
              "用例步骤": []}],
            ids=["no_cases_found"],
        )
        return

    metafunc.parametrize("caseinfo", case_infos, ids=case_names)


# ---------------------------------------------------------------------------
# 4. 处理中文显示
# ---------------------------------------------------------------------------
def pytest_collection_modifyitems(items, config):
    """收集项后处理：确保中文名正常显示"""
    for item in items:
        try:
            if isinstance(item._nodeid, bytes):
                item._nodeid = item._nodeid.decode("utf-8", errors="replace")
        except Exception:
            pass
