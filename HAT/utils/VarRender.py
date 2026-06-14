"""
变量渲染器 - 使用 Jinja2 模板引擎进行变量替换
将字符串中的 {{变量名}} 替换为全局上下文中的实际值
"""

import re
import json


class VarRender:
    """变量渲染器"""

    # 匹配 {{变量名}} 或 {{ 变量名 }} 的正则
    VAR_PATTERN = re.compile(r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}')

    @classmethod
    def refresh(cls, target, context_dict):
        """
        将 target 中的 {{变量名}} 替换为 context_dict 中的实际值
        支持 str、dict、list 类型的 target
        """
        if target is None:
            return None

        if isinstance(target, str):
            return cls._render_string(target, context_dict)

        if isinstance(target, dict):
            return {key: cls.refresh(value, context_dict) for key, value in target.items()}

        if isinstance(target, list):
            return [cls.refresh(item, context_dict) for item in target]

        # 其他类型直接返回
        return target

    @classmethod
    def _render_string(cls, text, context_dict, use_json_repr=False):
        """
        渲染字符串中的变量
        Args:
            text: 待渲染的字符串
            context_dict: 变量字典
            use_json_repr: 对非字符串值是否使用 JSON 表示
                          True = 用于 JSON 上下文，False = 用于普通文本
        """
        def replace_var(match):
            var_name = match.group(1)
            if var_name in context_dict:
                value = context_dict[var_name]
                # 字符串直接返回
                if isinstance(value, str):
                    return value
                # 数字/布尔值直接转字符串（JSON 兼容）
                if isinstance(value, (int, float, bool)):
                    if use_json_repr:
                        return json.dumps(value)
                    return str(value)
                # 列表/字典等复杂类型，用 JSON 表示
                if use_json_repr:
                    try:
                        return json.dumps(value, ensure_ascii=False)
                    except (TypeError, ValueError):
                        return str(value)
                return str(value)
            # 变量不存在时，保留原始占位符
            return match.group(0)

        return cls.VAR_PATTERN.sub(replace_var, text)

    @classmethod
    def json_render(cls, target, context_dict):
        """
        智能变量渲染器：
        1. 对 dict/list 中的每个字符串值单独处理
        2. 如果值完全匹配 {{var_name}} 格式，直接返回变量的原始值（保持类型）
        3. 如果值部分包含 {{var_name}} 格式，则进行字符串拼接
        """
        if target is None:
            return None

        if isinstance(target, dict):
            result = {}
            for key, value in target.items():
                result[key] = cls.json_render(value, context_dict)
            return result

        if isinstance(target, list):
            return [cls.json_render(item, context_dict) for item in target]

        if isinstance(target, str):
            # 检查是否完全匹配 {{var_name}}
            full_match = cls.VAR_PATTERN.fullmatch(target.strip())
            if full_match:
                var_name = full_match.group(1)
                if var_name in context_dict:
                    return context_dict[var_name]
                return target
            # 部分匹配，进行字符串替换
            return cls._render_string(target, context_dict)

        # 其他类型（数字、布尔值等）直接返回
        return target
