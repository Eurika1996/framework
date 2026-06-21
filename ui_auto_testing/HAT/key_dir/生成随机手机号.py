# -*- coding: utf-8 -*-
"""
示例自定义关键字: 生成随机手机号

使用方式（二选一）:
    A. 直接作为操作类型:
        操作类型: 生成随机手机号
        变量名: phone

    B. 通过 ex_invoke 调用:
        操作类型: ex_invoke
        key: 生成随机手机号
        变量名: phone
"""

from __future__ import annotations

import random

try:
    from HAT.core.globalContext import g_context
    _HAS_CONTEXT = True
except Exception:
    _HAS_CONTEXT = False


# 常见手机号前缀（中国）
_MOBILE_PREFIXES = [
    "133", "149", "153", "173", "177", "180", "181", "189", "191", "199",  # 电信
    "130", "131", "132", "145", "155", "156", "166", "171", "175", "176",
    "185", "186", "196",  # 联通
    "134", "135", "136", "137", "138", "139", "147", "150", "151", "152",
    "157", "158", "159", "172", "178", "182", "183", "184", "187", "188",
    "195", "197", "198",  # 移动
]


class 生成随机手机号:
    """示例自定义关键字：生成一个合法的中国手机号。"""

    def __init__(self, driver=None) -> None:
        self.driver = driver  # 虽未用到，但保留接口兼容性

    def 生成随机手机号(self, **kwargs) -> str:
        prefix = random.choice(_MOBILE_PREFIXES)
        suffix = "".join(random.choices("0123456789", k=8))
        phone = prefix + suffix

        var_name = str(kwargs.get("变量名", "") or "").strip()
        if var_name and _HAS_CONTEXT:
            g_context().set_dict(var_name, phone)
        return phone
