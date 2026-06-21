# -*- coding: utf-8 -*-
"""
动态脚本执行器 (run_script)

用于执行用例中『前置脚本 / 后置脚本』字段的 Python 代码。

安全说明:
    该功能默认启用。在不可信环境中，你可以通过设置环境变量
    HAT_DISABLE_SCRIPT=1 来禁用动态脚本执行。
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict


def exec_script(script: str, variables: Dict[str, Any]) -> Any:
    """执行 Python 脚本字符串。

    Args:
        script: Python 代码（可多行）
        variables: 可供脚本使用的变量字典，脚本修改后会回写

    Returns:
        脚本最后一个表达式的值（若有）

    脚本内可用:
        - 所有传入的变量（如 username, token 等）
        - 特殊变量 g_context (当前全局变量池)
        - 标准库 (通过 import 使用)

    脚本中可以直接:
        g_context["new_var"] = "some value"
        # 或
        result = calculate_something()
    """
    if os.environ.get("HAT_DISABLE_SCRIPT"):
        raise RuntimeError(
            "动态脚本执行已被禁用 (HAT_DISABLE_SCRIPT=1)"
        )

    if not script or not script.strip():
        return None

    # 准备执行环境
    from HAT.core.globalContext import g_context as _gc
    namespace: Dict[str, Any] = dict(variables)
    namespace["g_context"] = _gc
    namespace["__builtins__"] = __builtins__

    try:
        # 尝试作为表达式执行（支持 return value 语法）
        compiled = compile(script, "<dynamic_script>", "exec")
        exec(compiled, namespace)
    except SyntaxError as se:
        # 也可能是单行表达式
        try:
            compiled = compile(script, "<dynamic_script>", "eval")
            result = eval(compiled, namespace)
            return result
        except Exception:
            raise se

    # 把脚本执行过程中产生的新变量回写到 variables
    # (不覆盖原始 dict，只回写新增 / 修改过的变量)
    for key, value in namespace.items():
        if key.startswith("__"):
            continue
        if key in ("g_context",):
            continue
        variables[key] = value

    return None
