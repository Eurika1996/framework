# -*- coding: utf-8 -*-
"""
用例执行引擎 (TestRunner)

核心文件！整个 HAT 框架的心脏。

工作流程:
    1. 接收一条 caseinfo 用例数据
    2. 解析用例类型（WebCase / ApiCase / AppCase...）
    3. 初始化对应 Context（浏览器、API Client...）
    4. 执行前置脚本（动态 Python 代码）
    5. 遍历用例步骤:
        - VarRender.refresh() 渲染 {{变量名}} 模板
        - keywords.__getattribute__(操作类型) 反射获取方法
        - 调用关键字方法并传参
    6. 执行后置脚本
    7. finally: 释放资源（截图 + 关闭浏览器）
"""

from __future__ import annotations

import os
import sys
import traceback
from typing import Any, Dict, List

import pytest

# 确保项目根目录在 sys.path 中
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_CURRENT_DIR))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from HAT.core.globalContext import g_context
from HAT.context.WebCaseContext import WebCaseContext
from HAT.utils.VarRender import refresh as var_refresh
from HAT.utils.allure_step_logger import allure_step_with_log
from HAT.extend.script.run_script import exec_script

try:
    import allure
    _HAS_ALLURE = True
except ImportError:
    _HAS_ALLURE = False


def _allure_title(text: str) -> None:
    """安全调用 allure 标题装饰（无 allure 时不报错）"""
    if _HAS_ALLURE:
        try:
            allure.title(text)
        except Exception:
            pass


def _allure_epic(text: str) -> None:
    if _HAS_ALLURE:
        try:
            allure.epic(text)
        except Exception:
            pass


def _allure_feature(text: str) -> None:
    if _HAS_ALLURE:
        try:
            allure.feature(text)
        except Exception:
            pass


def _allure_story(text: str) -> None:
    if _HAS_ALLURE:
        try:
            allure.story(text)
        except Exception:
            pass


# ============================================================
# 用例类型 -> 上下文类 的映射
# 新增用例类型只需在此处添加对应 Context 类即可
# ============================================================
_CASE_TYPE_MAP: Dict[str, Any] = {
    "WebCase": WebCaseContext,
}


def register_case_type(type_name: str, context_cls: Any) -> None:
    """注册新的用例类型

    Args:
        type_name: 用例类型名（如 "ApiCase"）
        context_cls: 对应的 Context 类
    """
    _CASE_TYPE_MAP[type_name] = context_cls


# ============================================================
# pytest 测试函数
# ============================================================
def test_case_execute(caseinfo: Dict[str, Any]) -> None:
    """单条用例的执行入口

    Args:
        caseinfo: 由 CasesPlugin 参数化注入的用例数据字典

    结构示例:
        {
            "基础配置": {"用例类型": "WebCase", "一级模块": "...", "二级模块": "...", "用例标题": "..."},
            "前置脚本": "...",
            "后置脚本": "...",
            "用例步骤": [
                {"步骤描述": "...", "操作类型": "访问网址", "网址": "http://..."},
                ...
            ],
            "数据驱动": {"_数据组标题": "正常场景", ...},  # 可选
        }
    """
    # -------- 1. 解析基础配置 --------
    base_config: Dict[str, Any] = caseinfo.get("基础配置", {})
    case_type: str = base_config.get("用例类型", "WebCase")
    module_lv1: str = base_config.get("一级模块", "未分类")
    module_lv2: str = base_config.get("二级模块", "未分类")
    case_title: str = base_config.get("用例标题", "未命名用例")

    # Allure 报告分层
    _allure_epic(module_lv1)
    _allure_feature(module_lv2)
    _allure_story(case_title)
    _allure_title(f"{module_lv1} - {module_lv2} - {case_title}")

    # 用例步骤
    steps: List[Dict[str, Any]] = caseinfo.get("用例步骤", [])
    if not steps:
        pytest.skip("该用例无步骤，已跳过")

    # 前/后置脚本
    pre_script: str = caseinfo.get("前置脚本", "")
    post_script: str = caseinfo.get("后置脚本", "")

    # 如果当前用例携带数据驱动组，将它也注入全局变量以便步骤引用
    data_group = caseinfo.get("数据驱动")
    if isinstance(data_group, dict):
        for key, value in data_group.items():
            if not key.startswith("_"):  # 下划线开头的是元数据，跳过
                g_context().set_dict(str(key), value)

    # -------- 2. 初始化上下文（浏览器等） --------
    context_cls = _CASE_TYPE_MAP.get(case_type)
    if context_cls is None:
        raise ValueError(
            f"未知的用例类型: {case_type}，支持的类型: {list(_CASE_TYPE_MAP.keys())}"
        )

    case_context = context_cls()
    keywords = None

    try:
        # 初始化关键字库
        keywords = case_context.init_keywords()

        # -------- 3. 执行前置脚本 --------
        if pre_script:
            _safe_exec_script(pre_script, "前置脚本")

        # -------- 4. 逐步骤执行 --------
        for idx, step in enumerate(steps, 1):
            step_desc: str = ""
            action: str = ""

            # 兼容两种结构:
            #   {"步骤描述": { "操作类型": "访问网址", "网址": "..." }}
            #   {"操作类型": "访问网址", "网址": "...", "步骤描述": "xxx"}
            inner = step.get("步骤描述")
            if isinstance(inner, dict):
                step_desc = str(step.get("步骤描述", f"步骤{idx}"))
                params = dict(inner)
                action = str(params.pop("操作类型", ""))
            else:
                params = dict(step)
                action = str(params.pop("操作类型", ""))
                step_desc = str(params.pop("步骤描述", f"步骤{idx}"))

            if not action:
                raise ValueError(f"步骤{idx}缺少『操作类型』字段")

            # 对参数进行模板变量渲染
            params_rendered = _render_params(params)

            # 使用 allure 步骤包装，日志也会被收集
            with allure_step_with_log(f"[{idx:02d}] {action} - {step_desc}"):
                print(f"    ▶ 执行: {action} | {step_desc}")
                print(f"       参数: {_format_params(params_rendered)}")

                # 反射获取关键字方法
                key_func = None

                # 1. 先尝试从内置关键字库取
                try:
                    key_func = getattr(keywords, action)
                except AttributeError:
                    key_func = None

                # 2. 若内置没有，尝试从自定义关键字目录 (key_dir) 动态加载
                if key_func is None:
                    key_func = _try_load_custom_keyword(action, case_context)

                if key_func is None:
                    raise ValueError(
                        f"未知的关键字『{action}』，"
                        f"请在 HAT/keywords/web_keywords.py 添加方法 "
                        f"或在 HAT/key_dir/ 目录下创建 {action}.py 文件"
                    )

                # 3. 执行关键字方法
                try:
                    key_func(**params_rendered)
                except TypeError as te:
                    # 参数不匹配时给出更友好的提示
                    raise TypeError(
                        f"关键字『{action}』参数不匹配: {te}\n"
                        f"传入参数: {params_rendered}"
                    )

        # -------- 5. 执行后置脚本 --------
        if post_script:
            _safe_exec_script(post_script, "后置脚本")

    except Exception as e:
        # 出现异常时，保留截图（WebCaseContext 在 release 中处理）
        error_msg = f"用例执行失败: {case_title}\n异常信息: {str(e)}"
        print(f"\n    ❌ {error_msg}")
        traceback.print_exc()
        raise AssertionError(error_msg) from e

    finally:
        # -------- 6. 释放资源（截图轮播 + 关闭浏览器） --------
        try:
            case_context.release()
        except Exception as release_err:
            print(f"    ⚠ 资源释放警告: {release_err}")


# ============================================================
# 辅助函数
# ============================================================
def _render_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """递归遍历参数字典，对字符串值做 Jinja2 模板渲染"""
    rendered: Dict[str, Any] = {}
    for key, value in params.items():
        if isinstance(value, str):
            rendered[key] = var_refresh(value, g_context().show_dict())
        elif isinstance(value, dict):
            rendered[key] = _render_params(value)
        elif isinstance(value, list):
            rendered[key] = [
                var_refresh(str(v), g_context().show_dict())
                if isinstance(v, str)
                else v
                for v in value
            ]
        else:
            rendered[key] = value
    return rendered


def _format_params(params: Dict[str, Any]) -> str:
    """格式化参数显示（截断过长内容）"""
    if not params:
        return "(无)"
    parts = []
    for k, v in params.items():
        v_str = str(v)
        if len(v_str) > 80:
            v_str = v_str[:80] + "..."
        parts.append(f"{k}={v_str}")
    return "; ".join(parts)


def _safe_exec_script(script: str, stage: str) -> None:
    """安全执行 Python 脚本字符串

    Args:
        script: Python 代码字符串
        stage: 当前阶段描述（如 "前置脚本"），用于日志
    """
    if not script or not script.strip():
        return

    print(f"    📜 [{stage}] 开始执行自定义脚本...")
    try:
        exec_script(script, g_context().show_dict())
        print(f"    ✅ [{stage}] 脚本执行完成")
    except Exception as e:
        print(f"    ❌ [{stage}] 脚本执行失败: {e}")
        raise


def _try_load_custom_keyword(action: str, case_context) -> Any:
    """尝试从自定义关键字目录加载关键字

    规则:
        1. key_dir 目录下存在 {action}.py 文件
        2. 文件中定义了与文件同名的类
        3. 类的 __init__ 接收 driver 参数
        4. 类中存在与 action 同名的方法
    """
    key_dir = g_context().get_dict("key_dir")
    if not key_dir or not os.path.isdir(key_dir):
        return None

    abs_key_dir = os.path.abspath(key_dir)
    if abs_key_dir not in sys.path:
        sys.path.insert(0, abs_key_dir)

    module_file = os.path.join(abs_key_dir, f"{action}.py")
    if not os.path.isfile(module_file):
        return None

    try:
        # 动态导入
        import importlib.util
        spec = importlib.util.spec_from_file_location(action, module_file)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # 获取类
        cls = getattr(module, action, None)
        if cls is None:
            return None

        # 实例化（如果 case_context 有 driver 则传入）
        driver = getattr(case_context, "driver", None)
        instance = cls(driver)

        # 取方法
        method = getattr(instance, action, None)
        return method
    except Exception as e:
        print(f"    ⚠ 加载自定义关键字 '{action}' 失败: {e}")
        return None
