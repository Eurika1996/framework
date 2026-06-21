# -*- coding: utf-8 -*-
"""
诊断脚本 - 逐步排查测试失败原因
"""
import os
import sys

os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["HAT_HEADLESS"] = "1"

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

import yaml

print("=" * 70)
print("  步骤 1: 读取 context.yaml")
print("=" * 70)

context_file = os.path.join(_CURRENT_DIR, "hat-test-cases", "context.yaml")
try:
    with open(context_file, "r", encoding="utf-8") as f:
        context_data = yaml.safe_load(f)
    print(f"[OK] 读取成功: {context_file}")
    base_url = context_data.get("base_url")
    print(f"     base_url = {base_url}")
    web_elems = context_data.get("_WEB页面元素", {})
    print(f"     页面元素数量: {len(web_elems)}")
    print(f"     元素名: {list(web_elems.keys())}")
except Exception as e:
    print(f"[FAIL] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("  步骤 2: 读取测试用例 YAML")
print("=" * 70)

case_file = os.path.join(_CURRENT_DIR, "hat-test-cases", "0_服务启动与页面加载.yaml")
try:
    with open(case_file, "r", encoding="utf-8") as f:
        case_data = yaml.safe_load(f)
    print(f"[OK] 读取成功: {os.path.basename(case_file)}")
    print(f"     基础配置: {case_data.get('基础配置')}")
    steps = case_data.get("用例步骤", [])
    print(f"     用例步骤数量: {len(steps)}")
    for i, step in enumerate(steps):
        print(f"     [{i}] 操作类型: {step.get('操作类型')}")
        other = {k: v for k, v in step.items() if k not in ("步骤描述", "操作类型")}
        print(f"          参数: {other}")
except Exception as e:
    print(f"[FAIL] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("  步骤 3: 测试 VarRender 变量渲染")
print("=" * 70)

try:
    from HAT.core.globalContext import g_context
    from HAT.utils.VarRender import refresh

    for key, value in context_data.items():
        if isinstance(value, (str, int, float, bool)):
            g_context().set_dict(str(key), value)

    test_url = "{{base_url}}/"
    rendered = refresh(test_url)
    print(f"[OK] 模板渲染: '{test_url}' -> '{rendered}'")
except Exception as e:
    print(f"[FAIL] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("  步骤 4: 初始化 WebCaseContext（浏览器）")
print("=" * 70)

ctx = None
try:
    from HAT.context.WebCaseContext import WebCaseContext

    ctx = WebCaseContext()
    print(f"[OK] WebCaseContext 创建成功")

    keywords = ctx.init_keywords()
    print(f"[OK] WebKeywords 初始化: {keywords is not None}")
    methods = [a for a in dir(keywords) if not a.startswith("_") and callable(getattr(keywords, a))]
    print(f"     方法数: {len(methods)}")
    print(f"     可用方法: {methods}")
except Exception as e:
    print(f"[FAIL] {e}")
    import traceback
    traceback.print_exc()
    if ctx:
        try: ctx.close()
        except: pass
    sys.exit(1)

print("\n" + "=" * 70)
print("  步骤 5: 执行第一步 - 访问网址")
print("=" * 70)

try:
    step1 = steps[0]
    func_name = step1.get("操作类型")
    print(f"     操作类型: {func_name}")

    rendered_params = {}
    for k, v in step1.items():
        if isinstance(v, str):
            rendered_params[k] = refresh(v)
        else:
            rendered_params[k] = v

    print(f"     渲染后参数字典: {rendered_params}")

    method = getattr(keywords, func_name)
    result = method(**rendered_params)
    print(f"[OK] 执行成功, 返回: {result}")
except Exception as e:
    print(f"[FAIL] {e}")
    import traceback
    traceback.print_exc()
    if ctx:
        try: ctx.close()
        except: pass
    sys.exit(1)

print("\n" + "=" * 70)
print("  步骤 6: 执行后续步骤")
print("=" * 70)

try:
    for step in steps[1:]:
        desc = step.get("步骤描述", "?")
        print(f"\n     -> {desc}")
        rendered_params = {}
        for k, v in step.items():
            if isinstance(v, str):
                rendered_params[k] = refresh(v)
            else:
                rendered_params[k] = v

        func_name = rendered_params.get("操作类型")
        print(f"        方法: {func_name}")
        params = {k:v for k,v in rendered_params.items() if k not in ("步骤描述", "操作类型")}
        print(f"        参数: {params}")

        method = getattr(keywords, func_name)
        result = method(**rendered_params)
        print(f"        [OK] 成功, 返回: {result}")

    ctx.close()
    print(f"\n[OK] 所有诊断步骤通过！")
except Exception as e:
    print(f"[FAIL] {e}")
    import traceback
    traceback.print_exc()
    if ctx:
        try: ctx.close()
        except: pass
    sys.exit(1)
