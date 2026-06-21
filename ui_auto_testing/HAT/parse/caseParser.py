# -*- coding: utf-8 -*-
"""
用例解析器统一入口

根据用例文件类型（yaml / excel），分发到对应的解析器，
输出统一的数据结构:

    {
        "case_infos": [ {...}, {...}, ... ],
        "case_names": [ "用例1", "用例2", ... ]
    }

新增用例文件格式时，只需新增 {Xxx}CaseParser.py 并在此处注册。
"""

from __future__ import annotations

import os
from typing import Any, Dict

from HAT.parse.YamlCaseParser import yaml_case_parser
from HAT.parse.ExcelCaseParser import excel_case_parser


def case_parser(case_type: str, cases_dir: str) -> Dict[str, Any]:
    """根据类型调用对应解析器

    Args:
        case_type: "yaml" 或 "excel"
        cases_dir: 用例文件所在目录

    Returns:
        {"case_infos": [...], "case_names": [...]}

    Raises:
        ValueError: case_type 不受支持
    """
    case_type = (case_type or "").lower().strip()

    if case_type == "yaml":
        result = yaml_case_parser(cases_dir)
    elif case_type == "excel":
        result = excel_case_parser(cases_dir)
    else:
        raise ValueError(
            f"未知的用例类型: {case_type}，当前支持: yaml, excel"
        )

    case_count = len(result.get("case_infos", []))
    print(f"\n[HAT] 解析用例目录: {os.path.basename(cases_dir) or cases_dir}")
    print(f"[HAT] 类型: {case_type} | 共解析出 {case_count} 条用例\n")
    return result
