# -*- coding: utf-8 -*-
"""
全局变量池 (Global Context)

所有用例之间共享数据的唯一载体。
- 存储浏览器配置
- 存储页面元素定位
- 存储自定义变量
- 存储运行时动态提取的数据

使用方式:
    g_context().set_dict("username", "123")
    g_context().get_dict("username")
    g_context().show_dict()
"""

from __future__ import annotations
from typing import Any, Dict, Optional


class _GlobalContext:
    """全局单例变量池"""

    _dic: Dict[str, Any] = {}  # 类属性：所有实例共享同一个字典

    def set_dict(self, key: str, value: Any) -> None:
        """设置一个变量

        Args:
            key: 变量名
            value: 变量值
        """
        self._dic[key] = value

    def get_dict(self, key: str) -> Optional[Any]:
        """获取一个变量

        Args:
            key: 变量名

        Returns:
            变量值；不存在时返回 None
        """
        return self._dic.get(key, None)

    def show_dict(self) -> Dict[str, Any]:
        """返回当前全部变量

        Returns:
            完整的变量字典
        """
        return self._dic

    def clear(self) -> None:
        """清空全部变量（慎用）"""
        self._dic.clear()


# 对外统一入口：返回同一个实例
def g_context() -> _GlobalContext:
    """获取全局变量池单例"""
    return _GlobalContext()
