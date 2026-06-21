"""
API 用例上下文初始化器
管理 HTTP Session 会话，根据 session_reuse 配置决定会话复用策略
"""

import requests

from HAT.core.globalContext import global_context
from HAT.keywords.api_keywords import APIKeywords


class ApiCaseContext:
    """API 用例上下文初始化器"""

    def __init__(self, session_reuse=False, base_url=""):
        """
        Args:
            session_reuse: 是否复用同一个 Session（保持 Cookie）
            base_url: 基础 URL，用于拼接请求地址
        """
        self.session_reuse = session_reuse
        self.base_url = base_url
        self._session = None
        self._keywords = None

    def _get_session(self):
        """获取 Session 实例"""
        if self._session is None:
            if self.session_reuse:
                # 全局单例 session
                global_sess = global_context.get_dict("_api_session")
                if global_sess is None:
                    global_sess = requests.Session()
                    global_context.set_dict("_api_session", global_sess)
                self._session = global_sess
            else:
                # 每次新建 session
                self._session = requests.Session()
        return self._session

    def get_keywords(self):
        """获取关键字实例（懒加载）"""
        if self._keywords is None:
            session = self._get_session()
            self._keywords = APIKeywords(session=session, base_url=self.base_url)
        return self._keywords

    def reset(self):
        """重置 session（当 session_reuse 为 false 时可调用）"""
        self._session = None
        self._keywords = None


def create_api_context(session_reuse=False, base_url=""):
    """工厂方法：创建 ApiCaseContext 并返回关键字实例"""
    ctx = ApiCaseContext(session_reuse=session_reuse, base_url=base_url)
    return ctx.get_keywords()
