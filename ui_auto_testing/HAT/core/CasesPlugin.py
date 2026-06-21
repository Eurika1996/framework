# -*- coding: utf-8 -*-
"""
pytest 自定义插件 (CasesPlugin)

职责:
1. 注册 --type / --cases / --key_dir 三个命令行参数
2. 解析 YAML/Excel 用例文件，动态参数化注入测试函数
3. 处理中文显示问题（避免乱码）

在 pytest 运行时，会自动从 conftest.py 或 main.py 中被注册。
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

# 确保项目根目录在 sys.path 中
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_CURRENT_DIR))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from HAT.core.globalContext import g_context
from HAT.parse.caseParser import case_parser


class CasesPlugin:
    """pytest 自定义插件：动态参数化用例"""

    def pytest_addoption(self, parser):
        """注册命令行参数"""
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
            "--key_dir",
            action="store",
            default=None,
            help="自定义关键字目录路径 (可选)",
        )

    def pytest_generate_tests(self, metafunc):
        """核心：解析用例文件并动态参数化

        将解析出的 case_infos 注入 test_case_execute(caseinfo) 参数中。
        """
        if "caseinfo" not in metafunc.fixturenames:
            return  # 不是我们要处理的测试函数

        # 1. 获取命令行参数
        case_type = metafunc.config.getoption("type") or "yaml"
        cases_dir = metafunc.config.getoption("cases") or "./hat-test-cases"
        key_dir = metafunc.config.getoption("key_dir")

        # 2. 将配置注入全局变量池
        g_context().set_dict("case_type", case_type)
        g_context().set_dict("cases_dir", cases_dir)
        if key_dir:
            g_context().set_dict("key_dir", key_dir)

        # 3. 解析用例文件
        cases_dir = os.path.abspath(cases_dir)
        parsed = case_parser(case_type, cases_dir)

        # 4. 注入参数到 pytest
        case_infos: List[Dict[str, Any]] = parsed["case_infos"]
        case_names: List[str] = parsed["case_names"]

        if not case_infos:
            # 无可用用例时，仍注入一个空用例以避免 pytest 报错
            metafunc.parametrize(
                "caseinfo",
                [{"基础配置": {"用例标题": "无可用用例"}, "用例步骤": []}],
                ids=["no_cases_found"],
            )
            return

        metafunc.parametrize("caseinfo", case_infos, ids=case_names)

    def pytest_collection_modifyitems(self, items, config):
        """处理中文显示（避免 pytest 输出乱码）"""
        # Windows 控制台可能需要特殊处理
        for item in items:
            # 确保 nodeid 中的中文名能正常显示
            item._nodeid = item.nodeid.encode("utf-8", errors="replace").decode("utf-8")

    def pytest_configure(self, config):
        """pytest 配置钩子 - 在报告中注册自定义标记"""
        config.addinivalue_line(
            "markers",
            "hat_ui: HAT 框架 UI 自动化测试用例",
        )
