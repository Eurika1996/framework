"""
全局上下文管理器 - 单例模式
管理测试过程中所有的全局变量传递
"""


class GlobalContext:
    """单例模式的全局变量存储中心"""

    _instance = None
    _data = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data = {}
        return cls._instance

    def set_dict(self, key, value):
        """设置单个键值对"""
        self._data[key] = value

    def set_by_dict(self, data_dict):
        """批量更新字典"""
        if isinstance(data_dict, dict):
            self._data.update(data_dict)

    def get_dict(self, key):
        """获取指定键的值，不存在则返回 None"""
        return self._data.get(key)

    def show_dict(self):
        """展示所有全局变量"""
        return dict(self._data)

    def clear(self):
        """清空所有全局变量"""
        self._data.clear()


# 全局单例实例
global_context = GlobalContext()
