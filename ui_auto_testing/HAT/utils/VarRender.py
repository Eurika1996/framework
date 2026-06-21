# -*- coding: utf-8 -*-
"""
变量模板渲染器 (VarRender)

支持两种语法（都可使用，选择其一即可）:
    1. Jinja2: {{ variable }} / {{ variable | upper }} / {{ 1 + 1 }}
    2. Python f-string 简易模式（作为兜底，不依赖 Jinja2）

使用:
    from HAT.utils.VarRender import refresh
    result = refresh("用户名是 {{ username }}", {"username": "Alice"})
"""

from __future__ import annotations

import re
from typing import Any, Dict

try:
    from jinja2 import Template
    _HAS_JINJA2 = True
except ImportError:
    _HAS_JINJA2 = False

# 简易 f-string 风格的正则: {{ variable_name }}
_simple_pattern = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*\}\}")


def refresh(template: str, variables: Dict[str, Any]) -> str:
    """渲染模板字符串。

    Args:
        template: 含 {{xxx}} 语法的字符串
        variables: 变量字典

    Returns:
        渲染后的字符串
    """
    if not isinstance(template, str):
        return template
    if not template:
        return template
    if "{{" not in template:
        return template

    # 方案 1: 使用 Jinja2
    if _HAS_JINJA2:
        try:
            tpl = Template(template)
            return tpl.render(**variables)
        except Exception:
            pass

    # 方案 2: 简易正则替换（作为兜底）
    def replace(match: re.Match) -> str:
        key = match.group(1).strip()
        # 支持 . 访问，如 user.name
        value: Any = variables
        for part in key.split("."):
            if isinstance(value, dict) and part in value:
                value = value[part]
            elif hasattr(value, part):
                value = getattr(value, part)
            else:
                # 找不到时原样保留，方便调试
                return match.group(0)
        return "" if value is None else str(value)

    return _simple_pattern.sub(replace, template)
