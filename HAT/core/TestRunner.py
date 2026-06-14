"""
测试运行器 - 整个框架的核心调度引擎
加载 YAML 测试用例 -> 使用 pytest.mark.parametrize 实现数据驱动
-> 解析用例 -> 执行步骤 -> 调用关键字
"""

import os
import pytest

from HAT.core.globalContext import global_context
from HAT.parse.YamlCaseParser import (
    load_context_from_yaml,
    load_yaml_file,
    yaml_case_parser,
)
from HAT.context.ApiCaseContext import create_api_context
from HAT.utils.VarRender import VarRender
from HAT.extend.script.run_script import exec_script


# ── Allure 支持（可选导入，无 allure 环境也能正常运行）───────────
class _AllureDynamic:
    def __getattr__(self, name):
        return lambda *a, **kw: None

class _AllureStepCtx:
    def __init__(self, title): self.title = title
    def __enter__(self): return self
    def __exit__(self, *args): return False

class _DummyAllure:
    dynamic = _AllureDynamic()
    def step(self, title): return _AllureStepCtx(title)
    def __getattr__(self, name):
        def _decorator(*args, **kwargs):
            def _wrap(fn): return fn
            return _wrap
        return _decorator

try:
    import allure as _allure
except ImportError:
    _allure = _DummyAllure()


def _collect_all_cases(case_path):
    """
    收集指定目录/文件下所有 YAML 用例，解析后返回扁平的用例列表
    同时从用例所在目录加载 context.yaml
    """
    if os.path.isfile(case_path):
        base_dir = os.path.dirname(os.path.abspath(case_path))
    elif os.path.isdir(case_path):
        base_dir = os.path.abspath(case_path)
    else:
        base_dir = os.path.abspath(".")

    context_file = os.path.join(base_dir, "context.yaml")
    if os.path.isfile(context_file):
        print(f"[INFO] 加载配置: {context_file}")
        load_context_from_yaml(context_file)
    else:
        print(f"[WARN] 未找到 context.yaml: {context_file}")

    yaml_files = load_yaml_file(case_path)

    all_case_infos = []
    all_case_names = []
    for fpath in yaml_files:
        result = yaml_case_parser(fpath)
        all_case_infos.extend(result["case_infos"])
        all_case_names.extend(result["case_names"])

    return all_case_infos, all_case_names


def _execute_case(case_info):
    """
    执行单条用例的核心逻辑
    """
    case_title = case_info.get("用例标题", "未命名用例")
    module = case_info.get("一级模块", "")
    sub_module = case_info.get("二级模块", "")

    # Allure 动态标签（Feature / Story / Title）
    try:
        _allure.dynamic.feature(module)
        if sub_module:
            _allure.dynamic.story(sub_module)
        _allure.dynamic.title(case_title)
    except Exception:
        pass

    # DDT 数据注入
    ddt_vars = case_info.get("_ddt_vars", {})
    if ddt_vars:
        for k, v in ddt_vars.items():
            global_context.set_dict(k, v)

    base_url = global_context.get_dict("URL") or ""
    session_reuse = global_context.get_dict("session_reuse") or False

    # 执行前置条件
    preconditions = case_info.get("前置条件", [])
    if preconditions:
        for pre in preconditions:
            if pre and isinstance(pre, str) and pre.strip():
                with _allure.step(f"前置条件: {pre[:50]}"):
                    exec_script(pre, global_context.show_dict())

    # 初始化关键字
    keywords = create_api_context(session_reuse=session_reuse, base_url=base_url)

    # 遍历执行用例步骤
    steps = case_info.get("用例步骤", [])
    for step in steps:
        if not isinstance(step, dict):
            continue

        for step_name, step_params in step.items():
            if step_params is None:
                continue
            if not isinstance(step_params, dict):
                continue

            op_type = step_params.get("操作类型") or step_params.get("operator") or step_params.get("action")
            if not op_type:
                if step_params.get("请求地址") or step_params.get("endpoint"):
                    if step_params.get("请求数据") is not None or step_params.get("data") is not None:
                        op_type = "发送请求POST"
                    else:
                        op_type = "发送请求GET"
                else:
                    continue

            rendered_params = VarRender.json_render(step_params, global_context.show_dict())
            if rendered_params is None:
                rendered_params = step_params

            clean_params = {
                k: v for k, v in rendered_params.items()
                if k not in ("操作类型", "operator", "action")
            }

            method = None
            if hasattr(keywords, op_type):
                method = getattr(keywords, op_type)
            else:
                en_aliases = {
                    "POST": "发送请求POST",
                    "GET": "发送请求GET",
                    "PUT": "发送请求PUT",
                    "DELETE": "发送请求DELETE",
                    "PATCH": "发送请求PATCH",
                    "请求": "发送请求POST",
                    "请求GET": "发送请求GET",
                }
                if op_type.upper() in en_aliases:
                    method = getattr(keywords, en_aliases[op_type.upper()])
                else:
                    print(f"[WARN] 未知操作类型: {op_type}")
                    clean_params_for_ex = dict(clean_params)
                    clean_params_for_ex["关键字"] = op_type
                    result = keywords.ex_invoke(**clean_params_for_ex)
                    if result is not None:
                        continue
                    else:
                        raise ValueError(f"未知的操作类型: {op_type}")

            if method is not None:
                with _allure.step(f"{step_name} ({op_type})"):
                    print(f"\n  → 步骤: {step_name} ({op_type})")
                    method(**clean_params)


def build_test_function(case_dir):
    """工厂函数：根据用例目录创建 pytest 的参数化测试函数"""
    case_infos, case_names = _collect_all_cases(case_dir)

    if not case_infos:
        def test_empty():
            pytest.skip(f"目录 {case_dir} 中没有可用的用例文件")
        return test_empty

    @pytest.mark.parametrize("case", case_infos, ids=case_names)
    def test_yaml_case(case):
        _execute_case(case)

    return test_yaml_case


def run_tests_from_dir(case_dir=None, pytest_args=None):
    """从目录执行测试（由 main.py 调用）"""
    if case_dir is None:
        case_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "examples", "api-cases-yaml")
    case_dir = os.path.normpath(case_dir)

    case_infos, case_names = _collect_all_cases(case_dir)

    if not case_infos:
        print(f"[INFO] 目录 {case_dir} 中没有找到用例文件")
        return 0

    tmp_py_content = '''# 自动生成 - 不要修改
import sys, os
sys.path.insert(0, {0!r})

import pytest
from HAT.core.TestRunner import _execute_case

CASES = {1!r}
CASE_NAMES = {2!r}

@pytest.mark.parametrize("case", CASES, ids=CASE_NAMES)
def test_case(case):
    _execute_case(case)
'''.format(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), case_infos, case_names)

    tmp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_auto_generated_tests.py")

    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(tmp_py_content)

    default_args = [tmp_path, "-v", "--tb=short"]
    if pytest_args:
        default_args.extend(pytest_args)

    try:
        result = pytest.main(default_args)
        return result
    finally:
        try:
            if os.path.isfile(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
