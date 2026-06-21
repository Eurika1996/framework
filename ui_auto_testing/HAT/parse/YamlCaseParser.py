# -*- coding: utf-8 -*-
"""
YAML 用例解析器

职责:
1. 读取 context.yaml 注入全局变量池
2. 扫描目录读取所有数字开头的 yaml 用例文件
3. 处理数据驱动（DDT）: 1 个文件 + N 组数据 = N 条用例

文件命名规则:
    {数字}_{描述}.yaml    # 数字决定执行顺序
    context.yaml           # 全局配置（特殊，不含数字前缀）
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Tuple

from HAT.core.globalContext import g_context

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


# ============================================================
# 基础读写
# ============================================================
def read_yaml(file_path: str) -> Dict[str, Any]:
    """读取单个 YAML 文件

    Args:
        file_path: YAML 文件绝对路径

    Returns:
        解析后的字典结构

    Raises:
        RuntimeError: 未安装 PyYAML 或文件解析失败
    """
    if not _HAS_YAML:
        raise RuntimeError("缺少 PyYAML 依赖，请执行: pip install pyyaml")

    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"找不到 YAML 文件: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as ye:
            raise RuntimeError(f"YAML 解析错误 {file_path}: {ye}") from ye

    return data or {}


# ============================================================
# 全局配置 context.yaml 加载
# ============================================================
def load_context_from_yaml(context_file: str) -> None:
    """从 context.yaml 读取配置并注入全局变量池

    规则:
    - _浏览器: 存入 g_context["_浏览器"]
    - _数据库: 存入 g_context["_数据库"]
    - _WEB页面元素: 存入 g_context["_WEB页面元素"]
    - 其他字段: 直接以 key 作为变量名存入

    Args:
        context_file: context.yaml 的路径
    """
    if not os.path.isfile(context_file):
        # 没有 context.yaml 也可以工作（使用默认值或其他来源）
        return

    data = read_yaml(context_file)
    for key, value in data.items():
        g_context().set_dict(key, value)


# ============================================================
# 用例文件扫描
# ============================================================
_NUM_PREFIX_RE = re.compile(r"^(\d+)_.+\.ya?ml$", re.IGNORECASE)


def load_yaml_files(cases_dir: str) -> List[Tuple[str, Dict[str, Any]]]:
    """扫描目录读取所有数字开头的 yaml 用例文件

    Args:
        cases_dir: 用例目录路径

    Returns:
        [(文件名, 解析后字典), ...]，按文件前导数字从小到大排序
    """
    if not os.path.isdir(cases_dir):
        raise NotADirectoryError(f"用例目录不存在: {cases_dir}")

    files: List[Tuple[int, str, Dict[str, Any]]] = []
    for fname in os.listdir(cases_dir):
        match = _NUM_PREFIX_RE.match(fname)
        if not match:
            continue
        fpath = os.path.join(cases_dir, fname)
        try:
            data = read_yaml(fpath)
            order = int(match.group(1))
            files.append((order, fname, data))
        except Exception as e:
            print(f"  ⚠ 跳过有问题的用例文件 {fname}: {e}")

    # 按前缀数字排序
    files.sort(key=lambda x: x[0])
    return [(fname, data) for _, fname, data in files]


# ============================================================
# DDT 数据驱动展开
# ============================================================
def yaml_case_parser(cases_dir: str) -> Dict[str, Any]:
    """核心：解析目录下所有 YAML 用例，处理数据驱动

    Args:
        cases_dir: 用例目录路径

    Returns:
        {"case_infos": [...], "case_names": [...]}
    """
    # 1. 先加载 context.yaml
    context_file = os.path.join(cases_dir, "context.yaml")
    load_context_from_yaml(context_file)

    # 2. 读取所有用例文件
    raw_cases = load_yaml_files(cases_dir)
    if not raw_cases:
        return {"case_infos": [], "case_names": []}

    case_infos: List[Dict[str, Any]] = []
    case_names: List[str] = []

    for fname, case_data in raw_cases:
        # 3. 处理数据驱动
        data_driven = case_data.get("数据驱动")
        if isinstance(data_driven, list) and len(data_driven) > 0:
            # 有多组数据 → 每组数据生成一条独立用例
            base_case = {
                "基础配置": case_data.get("基础配置", {}),
                "前置脚本": case_data.get("前置脚本", ""),
                "后置脚本": case_data.get("后置脚本", ""),
                "用例步骤": case_data.get("用例步骤", []),
            }
            base_title = base_case["基础配置"].get("用例标题", fname)

            for idx, data_group in enumerate(data_driven):
                if not isinstance(data_group, dict):
                    continue
                group_title = data_group.get("description") or \
                              data_group.get("描述标题") or \
                              f"第{idx + 1}组数据"
                # 每条用例附带当前数据组
                one_case = dict(base_case)
                one_case["数据驱动"] = dict(data_group)
                case_title = f"{base_title}-{group_title}"
                case_infos.append(one_case)
                case_names.append(case_title)
        else:
            # 没有数据驱动 → 直接作为一条用例
            case_infos.append(case_data)
            title = case_data.get("基础配置", {}).get("用例标题") or fname
            case_names.append(str(title))

    return {"case_infos": case_infos, "case_names": case_names}
