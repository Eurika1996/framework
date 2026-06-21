"""
API 测试关键字库
封装所有通用的 API 测试操作：发送请求、提取响应、断言等
"""

import json
import re
import requests

try:
    import jsonpath
    HAS_JSONPATH = True
except ImportError:
    HAS_JSONPATH = False

from HAT.core.globalContext import global_context


class APIKeywords:
    """API 测试关键字库"""

    def __init__(self, session=None, base_url="", timeout=30):
        """
        Args:
            session: requests Session 实例
            base_url: 基础 URL，拼接在请求地址前
            timeout: 请求超时时间（秒）
        """
        self.session = session or requests.Session()
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.timeout = timeout

    # ──────────────────────────────────────
    # 辅助方法
    # ──────────────────────────────────────

    def _build_url(self, endpoint):
        """拼接完整 URL"""
        if not endpoint:
            return self.base_url or ""
        if endpoint.startswith(("http://", "https://")):
            return endpoint
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        return self.base_url + endpoint

    def _save_response(self, response, name="response", stream=False):
        """保存响应到全局上下文"""
        global_context.set_dict(name, response)
        status = response.status_code
        global_context.set_dict(name + "_status", status)
        
        if stream:
            try:
                first_chunk = ""
                for i, chunk in enumerate(response.iter_content(chunk_size=1024, decode_unicode=True)):
                    if chunk:
                        first_chunk += chunk
                    if i > 20 or len(first_chunk) > 4096:
                        break
                global_context.set_dict(name + "_text", first_chunk[:500])
            except Exception:
                global_context.set_dict(name + "_text", "")
            global_context.set_dict(name + "_json", None)
        else:
            try:
                global_context.set_dict(name + "_json", response.json())
            except Exception:
                global_context.set_dict(name + "_json", None)
            try:
                global_context.set_dict(name + "_text", response.text)
            except Exception:
                global_context.set_dict(name + "_text", "")

    def show_log(self, data_name, data):
        """记录调试日志"""
        print(f"[LOG] {data_name}: {data}")

    # ──────────────────────────────────────
    # 发送请求关键字
    # ──────────────────────────────────────

    def 发送请求POST(self, **kwargs):
        url = self._build_url(kwargs.get("请求地址") or kwargs.get("endpoint") or "")
        params = kwargs.get("URL参数") or kwargs.get("params") or None
        data = kwargs.get("请求数据") or kwargs.get("data") or None
        headers = kwargs.get("请求头") or kwargs.get("headers") or None
        files = kwargs.get("上传文件") or kwargs.get("files") or None
        stream = kwargs.get("流式") or kwargs.get("stream") or False
        json_body = None
        if isinstance(data, dict) and (not headers or "application/json" in str(headers).lower() or not headers.get("Content-Type")):
            json_body = data
            data = None
        response = self.session.post(
            url, params=params, json=json_body, data=data,
            headers=headers, files=files, stream=stream, timeout=self.timeout,
        )
        self._save_response(response, stream=stream)
        print(f"[POST] {url} -> status={response.status_code}")
        return response

    def 发送请求GET(self, **kwargs):
        url = self._build_url(kwargs.get("请求地址") or kwargs.get("endpoint") or "")
        params = kwargs.get("URL参数") or kwargs.get("params") or None
        headers = kwargs.get("请求头") or kwargs.get("headers") or None
        stream = kwargs.get("流式") or kwargs.get("stream") or False
        response = self.session.get(
            url, params=params, headers=headers, stream=stream, timeout=self.timeout
        )
        self._save_response(response, stream=stream)
        print(f"[GET]  {url} -> status={response.status_code}")
        return response

    def 发送请求PUT(self, **kwargs):
        """发送 PUT 请求"""
        url = self._build_url(kwargs.get("请求地址") or kwargs.get("endpoint") or "")
        data = kwargs.get("请求数据") or kwargs.get("data") or None
        params = kwargs.get("URL参数") or kwargs.get("params") or None
        headers = kwargs.get("请求头") or kwargs.get("headers") or None

        json_body = None
        if isinstance(data, dict):
            json_body = data
            data = None

        response = self.session.put(
            url, params=params, json=json_body, data=data, headers=headers, timeout=self.timeout
        )
        self._save_response(response)
        print(f"[PUT]  {url} -> status={response.status_code}")
        return response

    def 发送请求DELETE(self, **kwargs):
        """发送 DELETE 请求"""
        url = self._build_url(kwargs.get("请求地址") or kwargs.get("endpoint") or "")
        params = kwargs.get("URL参数") or kwargs.get("params") or None
        headers = kwargs.get("请求头") or kwargs.get("headers") or None

        response = self.session.delete(
            url, params=params, headers=headers, timeout=self.timeout
        )
        self._save_response(response)
        print(f"[DEL]  {url} -> status={response.status_code}")
        return response

    def 发送请求PATCH(self, **kwargs):
        """发送 PATCH 请求"""
        url = self._build_url(kwargs.get("请求地址") or kwargs.get("endpoint") or "")
        data = kwargs.get("请求数据") or kwargs.get("data") or None
        params = kwargs.get("URL参数") or kwargs.get("params") or None
        headers = kwargs.get("请求头") or kwargs.get("headers") or None

        json_body = None
        if isinstance(data, dict):
            json_body = data
            data = None

        response = self.session.patch(
            url, params=params, json=json_body, data=data, headers=headers, timeout=self.timeout
        )
        self._save_response(response)
        print(f"[PATCH] {url} -> status={response.status_code}")
        return response

    # ──────────────────────────────────────
    # 提取关键字
    # ──────────────────────────────────────

    def 提取JSON(self, **kwargs):
        """
        使用 JSONPath 从响应中提取数据，并保存到全局上下文
        参数:
            表达式: "$.data.token" 或 "$.data.id"
            变量名: "token"
            响应来源: "response"（可选，默认取最近一次响应）
            下标: 0（可选，当提取结果为数组时取第几个）
        """
        expr = kwargs.get("表达式") or kwargs.get("expr") or ""
        var_name = kwargs.get("变量名") or kwargs.get("var") or "extracted"
        source_name = kwargs.get("响应来源") or kwargs.get("from") or "response"
        index = kwargs.get("下标") or kwargs.get("index")

        # 获取响应 JSON
        response_json = global_context.get_dict(source_name + "_json")
        if response_json is None:
            response_obj = global_context.get_dict(source_name)
            if response_obj is not None and hasattr(response_obj, "json"):
                try:
                    response_json = response_obj.json()
                except Exception:
                    response_json = None

        if response_json is None:
            print(f"[WARN] 提取失败：没有可用的响应 JSON（{source_name}）")
            return None

        # 使用 JSONPath 提取
        value = None
        if HAS_JSONPATH:
            try:
                matches = jsonpath.jsonpath(response_json, expr)
                if matches:
                    if index is not None and isinstance(matches, list):
                        value = matches[index] if index < len(matches) else None
                    else:
                        value = matches[0] if len(matches) == 1 else matches
            except Exception:
                value = None
        else:
            # 简易 fallback：手动解析点号路径，如 "data.token"
            value = self._simple_json_extract(response_json, expr)

        # 保存到全局上下文
        global_context.set_dict(var_name, value)
        print(f"[提取] {expr} => {var_name} = {value}")
        return value

    def _simple_json_extract(self, data, expr):
        """简易的 JSON 路径提取（不依赖 jsonpath）"""
        # 清理 "$." 前缀
        path = expr.replace("$.", "").strip()
        if not path:
            return data
        # 支持 "data.token.0" 这种点号分隔
        parts = []
        for part in path.split("."):
            if part == "$":
                continue
            if part.isdigit():
                parts.append(int(part))
            else:
                parts.append(part)

        current = data
        for key in parts:
            try:
                if isinstance(current, list) and isinstance(key, int):
                    current = current[key]
                elif isinstance(current, dict):
                    current = current.get(key)
                else:
                    return None
            except (IndexError, TypeError):
                return None
        return current

    # ──────────────────────────────────────
    # 断言关键字
    # ──────────────────────────────────────

    def 断言文本(self, **kwargs):
        """
        文本/数值断言
        参数:
            预期结果: "success" 或 200 或 True
            实际结果: "{{token_status}}"
            比较符: "==" / "!=" / ">" / "<" / ">=" / "<=" / "in" / "contains"
        """
        expected = kwargs.get("预期结果") or kwargs.get("expected")
        actual = kwargs.get("实际结果") or kwargs.get("actual")
        operator = kwargs.get("比较符") or kwargs.get("operator") or "=="

        # 自动类型转换
        if isinstance(expected, str) and isinstance(actual, (int, float)):
            try:
                expected_num = type(actual)(expected)
                expected = expected_num
            except (ValueError, TypeError):
                pass
        elif isinstance(actual, str) and isinstance(expected, (int, float)):
            try:
                actual_num = type(expected)(actual)
                actual = actual_num
            except (ValueError, TypeError):
                pass

        result = False
        if operator == "==":
            result = str(expected) == str(actual) if isinstance(expected, bool) or isinstance(actual, bool) else expected == actual
        elif operator == "!=":
            result = expected != actual
        elif operator == ">":
            result = actual > expected
        elif operator == "<":
            result = actual < expected
        elif operator == ">=":
            result = actual >= expected
        elif operator == "<=":
            result = actual <= expected
        elif operator in ("in", "contains"):
            result = str(expected) in str(actual)
        else:
            raise ValueError(f"不支持的比较符: {operator}")

        print(f"[断言] {actual} {operator} {expected} -> {'PASS' if result else 'FAIL'}")

        if not result:
            raise AssertionError(f"断言失败: 预期 {expected} {operator} 实际 {actual}")

        return result

    def 断言状态码(self, **kwargs):
        """断言 HTTP 状态码"""
        expected = kwargs.get("预期结果") or kwargs.get("expected") or 200
        source = kwargs.get("响应来源") or "response"
        actual = global_context.get_dict(source + "_status")

        if actual is None:
            raise AssertionError(f"没有找到响应状态码（{source}_status）")

        print(f"[断言状态码] 预期 {expected} 实际 {actual}")

        if expected == "2xx":
            result = 200 <= actual < 300
        elif isinstance(expected, (list, tuple)):
            result = actual in expected
        else:
            result = actual == int(expected)

        if not result:
            raise AssertionError(f"状态码断言失败: 预期 {expected} 实际 {actual}")

        return result

    def 断言JSON包含(self, **kwargs):
        """断言响应 JSON 中包含指定字段"""
        field = kwargs.get("字段") or kwargs.get("field")
        source = kwargs.get("响应来源") or "response"
        response_json = global_context.get_dict(source + "_json")

        if response_json is None:
            raise AssertionError("没有可用的响应 JSON")

        # 简易字段查找
        value = self._simple_json_extract(response_json, field)
        print(f"[断言字段] {field} = {value}")

        if value is None:
            raise AssertionError(f"响应中不存在字段: {field}")

        return value

    # ──────────────────────────────────────
    # 数据库关键字
    # ──────────────────────────────────────

    def 提取数据库MYSQL(self, **kwargs):
        """
        连接 MySQL 数据库并执行查询，将结果保存到全局上下文
        参数:
            数据库: "电商数据库"（对应 context.yaml 中的配置名）
            sql: "select id, username from user where ..."
            变量名: ["uid", "uname"] 或 "result"
        """
        db_name = kwargs.get("数据库") or kwargs.get("db")
        sql = kwargs.get("sql") or kwargs.get("SQL")
        var_names = kwargs.get("变量名") or kwargs.get("var")

        # 从全局上下文读取数据库配置
        db_configs = global_context.get_dict("_数据库") or {}
        cfg = db_configs.get(db_name) if isinstance(db_configs, dict) else None

        if not cfg:
            print(f"[WARN] 数据库配置未找到: {db_name}，跳过数据库断言")
            return None

        try:
            import pymysql
        except ImportError:
            print("[WARN] 未安装 pymysql，跳过数据库查询")
            return None

        try:
            conn = pymysql.connect(
                host=cfg.get("host"),
                port=int(cfg.get("port", 3306)),
                user=cfg.get("user"),
                password=cfg.get("password"),
                db=cfg.get("db"),
                charset="utf8mb4",
            )
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            cursor.close()
            conn.close()

            if not rows:
                print(f"[DB] 查询无结果: {sql}")
                return None

            first_row = rows[0]

            if isinstance(var_names, list):
                # 多变量提取
                for i, vname in enumerate(var_names):
                    if i < len(first_row):
                        global_context.set_dict(vname, first_row[i])
                        print(f"[DB] {vname}_{i+1} = {first_row[i]}")
                    else:
                        global_context.set_dict(vname, None)
            else:
                # 单变量保存整个结果
                global_context.set_dict(var_names, rows)
                print(f"[DB] {var_names} = {rows}")

            return first_row
        except Exception as e:
            print(f"[DB] 数据库查询异常: {e}")
            return None

    # ──────────────────────────────────────
    # 扩展关键字（动态加载 key_dir 中的自定义关键字）
    # ──────────────────────────────────────

    def ex_invoke(self, **kwargs):
        """
        动态调用自定义关键字
        参数:
            关键字: "发送请求POST" 或 "自定义操作"
            ...其他参数传递给目标关键字
        """
        from HAT.extend.script.run_script import load_custom_keyword

        keyword_name = kwargs.get("关键字") or kwargs.get("keyword")
        if not keyword_name:
            raise ValueError("未指定要调用的自定义关键字")

        # 尝试从 key_dir 加载
        custom_cls = load_custom_keyword(keyword_name)
        if custom_cls is not None:
            instance = custom_cls(session=self.session, base_url=self.base_url)
            # 查找并执行方法
            method = getattr(instance, keyword_name, None)
            if method is None:
                # 尝试匹配第一个非私有方法
                for attr_name in dir(instance):
                    if not attr_name.startswith("_") and callable(getattr(instance, attr_name)):
                        method = getattr(instance, attr_name)
                        break
            if method:
                clean_kwargs = {k: v for k, v in kwargs.items() if k not in ("关键字", "keyword")}
                return method(**clean_kwargs)

        print(f"[WARN] 自定义关键字未找到: {keyword_name}")
        return None
