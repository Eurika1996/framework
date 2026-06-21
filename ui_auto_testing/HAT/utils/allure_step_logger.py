# -*- coding: utf-8 -*-
"""
Allure 步骤日志收集装饰器

提供:
    - allure_step_with_log(label): 上下文管理器（with 块）—— 每步
      自动记录到 allure 报告，同时打印到控制台。
    - start_step_logging(): 可选，可用于更灵活的日志开启。
"""

from __future__ import annotations

import sys
import time
from contextlib import contextmanager
from typing import Iterator

try:
    import allure
    _HAS_ALLURE = True
except ImportError:
    _HAS_ALLURE = False


@contextmanager
def allure_step_with_log(label: str) -> Iterator[None]:
    """以步骤形式记录到 allure 报告。

    使用示例:
        with allure_step_with_log("输入用户名"):
            do_something()

    - 有 allure 时，会在报告中形成一个 step
    - 控制台同步输出开始/结束提示
    - 发生异常时，会把异常标记到步骤中
    """
    start = time.time()
    print(f"  🟢 [步骤开始] {label}", flush=True)
    try:
        if _HAS_ALLURE:
            with allure.step(label):
                yield
        else:
            yield
    except Exception as e:
        elapsed = time.time() - start
        print(f"  🔴 [步骤失败] {label} ({elapsed:.2f}s) - {e}", file=sys.stderr, flush=True)
        raise
    else:
        elapsed = time.time() - start
        print(f"  ✅ [步骤完成] {label} ({elapsed:.2f}s)", flush=True)


def step(label: str) -> contextmanager:
    """简易别名，保持接口简洁。"""
    return allure_step_with_log(label)
