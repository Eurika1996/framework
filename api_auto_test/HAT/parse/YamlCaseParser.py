"""
YAML 用例解析器
负责读取和解析 YAML 格式的测试用例，支持数据驱动（DDT）
"""

import os
import re
import yaml

from HAT.core.globalContext import global_context


def read_yaml(file_path):
    """读取单个 YAML 文件，返回解析后的列表数据"""
    if not os.path.isfile(file_path):
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # yaml.safe_load 支持多个文档（--- 分隔），返回列表
    try:
        docs = list(yaml.safe_load_all(content))
    except yaml.YAMLError as e:
        print(f"[WARN] YAML 解析失败: {file_path} -> {e}")
        return []

    # 过滤 None（空文档）
    return [doc for doc in docs if doc is not None]


def load_context_from_yaml(file_path):
    """
    专门读取 context.yaml 配置文件
    将配置加载到全局上下文中
    """
    docs = read_yaml(file_path)
    if not docs:
        return {}

    config = docs[0] if isinstance(docs, list) else docs

    # 保存全部配置到上下文
    for key, value in config.items():
        global_context.set_dict(key, value)

    # 特殊字段处理
    if "URL" in config:
        global_context.set_dict("URL", config["URL"])

    if "session_reuse" in config:
        global_context.set_dict("session_reuse", config["session_reuse"])

    if "key_dir" in config:
        global_context.set_dict("key_dir", config["key_dir"])

    # 数据库配置
    if "_数据库" in config and isinstance(config["_数据库"], dict):
        global_context.set_dict("_数据库", config["_数据库"])
    elif "数据库" in config and isinstance(config["数据库"], dict):
        global_context.set_dict("_数据库", config["数据库"])

    return config


def load_yaml_file(file_path):
    """
    批量读取文件夹下所有用例 YAML 文件
    按文件名数字前缀排序（1-login.yaml -> 2-addcard.yaml）
    只读取数字开头的 yaml 文件
    """
    if os.path.isfile(file_path):
        return [file_path]

    if not os.path.isdir(file_path):
        return []

    yaml_files = []
    for fname in sorted(os.listdir(file_path)):
        if not fname.endswith((".yaml", ".yml")):
            continue
        if fname.startswith("_") or fname.startswith("context"):
            continue
        # 只取数字前缀的用例文件
        base = os.path.splitext(fname)[0]
        if not re.match(r"^\d+", base):
            continue
        yaml_files.append(os.path.join(file_path, fname))

    return yaml_files


def yaml_case_parser(file_path=None, raw_docs=None):
    """
    核心函数：处理数据驱动（DDT）逻辑
    如果没有 DDT：直接返回原始用例
    如果有 DDT：将每组数据与用例模板组合，生成多条独立用例

    返回: {"case_infos": [...], "case_names": [...]}
        case_infos: 每个元素是一条完整用例 dict
        case_names: 对应的用例标题列表（用于 pytest parametrize）
    """
    if raw_docs is None:
        raw_docs = read_yaml(file_path)

    case_infos = []
    case_names = []

    for doc in raw_docs:
        if not isinstance(doc, dict):
            continue

        # 支持 "用例步骤" 或 "steps" 作为步骤列表
        steps = doc.get("用例步骤") or doc.get("steps") or []
        title = doc.get("用例标题") or doc.get("title") or f"用例-{len(case_names)+1}"
        module = doc.get("一级模块") or doc.get("module") or "未分类"
        sub_module = doc.get("二级模块") or doc.get("sub_module") or ""
        case_type = doc.get("用例类型") or doc.get("type") or "ApiCase"
        precondition = doc.get("前置条件") or doc.get("precondition") or []

        # 数据驱动逻辑
        ddt = doc.get("数据驱动") or doc.get("ddt") or []

        if not ddt:
            # 没有 DDT，单条用例
            case_info = {
                "用例类型": case_type,
                "用例标题": title,
                "一级模块": module,
                "二级模块": sub_module,
                "前置条件": precondition if isinstance(precondition, list) else [precondition],
                "用例步骤": steps,
            }
            case_infos.append(case_info)
            case_names.append(f"{module}-{title}")
        else:
            # 有 DDT，每组数据生成一条用例
            for idx, data_row in enumerate(ddt):
                if not isinstance(data_row, dict):
                    continue

                # 生成唯一标题
                desc_suffix = data_row.get("描述标题") or data_row.get("desc") or f"第{idx+1}组数据"
                case_title = f"{title}-{desc_suffix}"

                # 把 DDT 数据合并到全局变量候选区（用例执行时会渲染）
                ddt_vars = {k: v for k, v in data_row.items() if k not in ("描述标题", "desc")}

                case_info = {
                    "用例类型": case_type,
                    "用例标题": case_title,
                    "一级模块": module,
                    "二级模块": sub_module,
                    "前置条件": precondition if isinstance(precondition, list) else [precondition],
                    "用例步骤": steps,
                    "_ddt_vars": ddt_vars,
                }
                case_infos.append(case_info)
                case_names.append(f"{module}-{case_title}")

    return {"case_infos": case_infos, "case_names": case_names}
