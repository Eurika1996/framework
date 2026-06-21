"""
动态脚本执行器
执行 YAML 中定义的前置/后置 Python 脚本
"""

import os
import sys
import importlib.util


def exec_script(script, context):
    """
    动态执行字符串代码
    Args:
        script: Python 代码字符串
        context: dict，作为执行环境的全局变量，可被脚本读写
    """
    if not script or not isinstance(script, str):
        return

    local_ns = {"context": context}
    try:
        exec(script, {"__builtins__": __builtins__}, local_ns)
    except Exception as e:
        print(f"[WARN] 脚本执行异常: {e}")
        print(f"       脚本内容: {script[:120]}...")


def load_custom_keyword(keyword_name):
    """
    从 HAT/key_dir/ 动态加载自定义关键字类
    约定：文件名 = 类名 = 关键字名
    """
    # 查找目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    key_dir = os.path.join(current_dir, "..", "..", "key_dir")
    key_dir = os.path.normpath(key_dir)

    if not os.path.isdir(key_dir):
        return None

    # 遍历所有 .py 文件
    for fname in os.listdir(key_dir):
        if not fname.endswith(".py") or fname.startswith("_"):
            continue

        fpath = os.path.join(key_dir, fname)
        module_name = f"custom_keyword_{os.path.splitext(fname)[0]}"

        try:
            spec = importlib.util.spec_from_file_location(module_name, fpath)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # 查找与关键字同名的类，或类名与文件名（不含扩展名）相同
            target_class_name = keyword_name
            file_base_name = os.path.splitext(fname)[0]

            for attr_name in dir(module):
                if attr_name.startswith("_"):
                    continue
                attr = getattr(module, attr_name)
                if isinstance(attr, type):
                    if attr_name == target_class_name or attr_name == file_base_name:
                        return attr
        except Exception as e:
            print(f"[WARN] 加载自定义关键字 {fname} 失败: {e}")

    return None
