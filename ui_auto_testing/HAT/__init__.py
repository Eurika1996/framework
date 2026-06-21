# -*- coding: utf-8 -*-
"""
HAT - Hybrid Automation Testing 框架主包

架构：
    main.py ── pytest.main()
        │
        ├── HAT/core/         # 核心调度模块
        ├── HAT/parse/        # 用例解析模块
        ├── HAT/keywords/     # 关键字库模块
        ├── HAT/context/      # 上下文管理模块
        ├── HAT/utils/        # 工具类模块
        ├── HAT/extend/       # 扩展模块
        └── HAT/key_dir/      # 自定义关键字目录
"""
import os
import sys

# 全局设置: 强制使用 UTF-8 输出，避免 Windows 控制台 GBK 编码问题
os.environ["PYTHONIOENCODING"] = "utf-8"
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

__version__ = "1.0.0"
__author__ = "HAT Framework"
