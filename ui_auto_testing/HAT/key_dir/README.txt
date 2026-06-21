# -*- coding: utf-8 -*-
"""
自定义关键字目录 (key_dir)

如何使用:
    1. 在本目录创建一个 Python 文件，文件名 = 类名 = 方法名（都相同）
    2. 类的 __init__ 接收一个 driver 参数
    3. 类中定义一个与类同名的方法作为关键字的实现
    4. 在 context.yaml 中配置 key_dir: "./HAT/key_dir"
    5. 在测试用例中通过:
        操作类型: ex_invoke
        key: 自定义关键字文件名
       调用，或者直接用文件名作为操作类型（TestRunner 会自动尝试加载）

示例:
    文件: 自定义登录.py
    类:   自定义登录
    方法: 自定义登录(self, **kwargs) -> None
"""
