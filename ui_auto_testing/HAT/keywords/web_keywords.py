# -*- coding: utf-8 -*-
"""
Web 自动化关键字库 (WebKeywords)

每个 public 方法 = 一个在 YAML 用例中可调用的『操作类型』。
方法名即关键字名，方法参数来自用例的步骤参数字段。

设计亮点:
    1. 元素定位解耦: 步骤传『_页面元素』别名，实际定位方式在 context.yaml
       的『_WEB页面元素』中维护。页面改版时，只需改一处。
    2. 断言文本通用化: 支持多种比较运算符（==, !=, >, <, in, not in, contains 等）
    3. 自定义关键字扩展: 提供 ex_invoke 机制，可从外部目录加载关键字。
"""

from __future__ import annotations

import os
import sys
import time
import json
import random
import base64
from typing import Any, Dict, Optional

# 确保项目根目录在 sys.path
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_CURRENT_DIR))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from HAT.core.globalContext import g_context

try:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.common.exceptions import (
        NoSuchElementException,
        TimeoutException,
        StaleElementReferenceException,
    )
    _HAS_SELENIUM = True
except ImportError:
    _HAS_SELENIUM = False

try:
    import ddddocr  # type: ignore
    _HAS_DDDDOCR = True
except ImportError:
    _HAS_DDDDOCR = False

try:
    import pymysql  # type: ignore
    from pymysql.cursors import DictCursor  # type: ignore
    _HAS_PYMYSQL = True
except ImportError:
    _HAS_PYMYSQL = False

try:
    import allure  # type: ignore
    _HAS_ALLURE = True
except ImportError:
    _HAS_ALLURE = False


# 定位方式映射表（Selenium 的 By.*）
_locator_map = {
    "id": By.ID if _HAS_SELENIUM else "id",
    "name": By.NAME if _HAS_SELENIUM else "name",
    "class": By.CLASS_NAME if _HAS_SELENIUM else "class name",
    "classname": By.CLASS_NAME if _HAS_SELENIUM else "class name",
    "css": By.CSS_SELECTOR if _HAS_SELENIUM else "css selector",
    "cssselector": By.CSS_SELECTOR if _HAS_SELENIUM else "css selector",
    "xpath": By.XPATH if _HAS_SELENIUM else "xpath",
    "link": By.LINK_TEXT if _HAS_SELENIUM else "link text",
    "linktext": By.LINK_TEXT if _HAS_SELENIUM else "link text",
    "partiallink": By.PARTIAL_LINK_TEXT if _HAS_SELENIUM else "partial link text",
    "tag": By.TAG_NAME if _HAS_SELENIUM else "tag name",
    "tagname": By.TAG_NAME if _HAS_SELENIUM else "tag name",
}


class WebKeywords:
    """Web 自动化关键字库

    用例中的『操作类型』字段值必须与本类的某个方法名完全一致（含中文）。
    """

    # ============================================================
    # 构造
    # ============================================================
    def __init__(self, driver: Any) -> None:
        self.driver = driver
        self._default_timeout = 15  # 显式等待默认秒数

    # ============================================================
    # 内部工具: 元素定位
    # ============================================================
    def _resolve_locator(self, element_alias: str) -> tuple:
        """从 context 的『_WEB页面元素』中解析元素定位信息

        Args:
            element_alias: 元素别名，如 "手机号_输入框"

        Returns:
            (By.xxx, "定位字符串")
        """
        elements = g_context().get_dict("_WEB页面元素") or {}
        ele_data = elements.get(element_alias)

        if ele_data is None:
            raise ValueError(
                f"找不到元素别名『{element_alias}』，"
                f"请在 context.yaml 的『_WEB页面元素』中定义"
            )

        if isinstance(ele_data, str):
            # 简写：字符串形式可能是 "id:username"
            if ":" in ele_data:
                loc_type, loc_value = ele_data.split(":", 1)
                loc_type = loc_type.strip().lower()
                loc_value = loc_value.strip()
            else:
                raise ValueError(
                    f"元素『{element_alias}』配置格式不正确，"
                    f"应为 {{定位方式: ..., 目标对象: ...}} 或 'id:xxx'"
                )
        elif isinstance(ele_data, dict):
            loc_type = str(ele_data.get("定位方式", "")).strip().lower()
            loc_value = str(ele_data.get("目标对象", "")).strip()
        else:
            raise ValueError(
                f"元素『{element_alias}』的配置必须是字符串或字典，"
                f"当前是 {type(ele_data).__name__}"
            )

        if not loc_type or not loc_value:
            raise ValueError(
                f"元素『{element_alias}』缺少『定位方式』或『目标对象』"
            )

        by_type = _locator_map.get(loc_type)
        if by_type is None:
            # 作为最后的兜底：直接使用字符串形式（Selenium 4+ 某些版本也接受字符串）
            by_type = loc_type

        return (by_type, loc_value)

    def find_element(self, **kwargs: Any) -> Any:
        """查找单个元素（显式等待）。

        参数:
            _页面元素: 元素别名
            _超时:     可选，等待秒数（默认 15）
        """
        element_alias = str(kwargs.get("_页面元素", ""))
        timeout = int(kwargs.get("_超时", self._default_timeout))

        if not element_alias:
            raise ValueError("必须指定『_页面元素』参数")

        locator = self._resolve_locator(element_alias)
        try:
            wait = WebDriverWait(self.driver, timeout)
            ele = wait.until(EC.presence_of_element_located(locator))
            wait.until(EC.visibility_of(ele))
            return ele
        except TimeoutException:
            raise TimeoutError(
                f"在 {timeout} 秒内未找到元素『{element_alias}』 "
                f"(定位: {locator[0]}={locator[1]})"
            )

    def _take_screenshot(self, label: str) -> None:
        """调用上下文的截图方法（若可用）"""
        try:
            from HAT.context.WebCaseContext import WebCaseContext as _Ctx
            # 找到当前上下文实例，通过在 WebCaseContext.__init__ 中留下引用
            # 这里简化为直接截图
            pass
        except Exception:
            pass

        # 简单方案：每次关键字执行后拍一张图
        if self.driver is None:
            return
        try:
            png = self.driver.get_screenshot_as_base64()
            if _HAS_ALLURE:
                try:
                    allure.attach(
                        base64.b64decode(png),
                        name=label,
                        attachment_type=allure.attachment_type.PNG,
                    )
                except Exception:
                    pass
        except Exception:
            pass

    # ============================================================
    # 关键字 1: 访问网址
    # ============================================================
    def 访问网址(self, **kwargs: Any) -> None:
        """打开一个 URL 页面。

        参数: 网址 或 url
        """
        url = str(kwargs.get("网址") or kwargs.get("url") or "").strip()
        if not url:
            raise ValueError("『访问网址』关键字必须提供『网址』参数")
        self.driver.get(url)
        self._take_screenshot(f"访问 {url[:60]}")

    def open_url(self, **kwargs: Any) -> None:
        """访问网址 的英文别名。"""
        self.访问网址(**kwargs)

    # ============================================================
    # 关键字 2: 输入内容
    # ============================================================
    def 输入内容(self, **kwargs: Any) -> None:
        """向输入框发送文本。

        参数:
            _页面元素: 元素别名
            数据内容: 要输入的文本
            _清空:     True/False（默认 True，输入前清空）
        """
        element = self.find_element(**kwargs)
        data = str(kwargs.get("数据内容", kwargs.get("value", "")) or "")
        clear_first = kwargs.get("_清空", True)
        if str(clear_first).lower() in ("false", "0", "no", "n"):
            clear_first = False

        if clear_first:
            try:
                element.clear()
            except Exception:
                # 有些控件不支持 clear()，退而用 CTRL+A + DELETE
                try:
                    element.send_keys(Keys.CONTROL, "a")
                    element.send_keys(Keys.DELETE)
                except Exception:
                    pass
        element.send_keys(data)
        self._take_screenshot(f"输入: {data[:30]}")

    def input_text(self, **kwargs: Any) -> None:
        self.输入内容(**kwargs)

    # ============================================================
    # 关键字 3: 点击元素
    # ============================================================
    def 点击元素(self, **kwargs: Any) -> None:
        """点击页面元素。"""
        element = self.find_element(**kwargs)
        try:
            element.click()
        except Exception:
            # 普通点击失败时，用 JavaScript 兜底点击
            try:
                self.driver.execute_script("arguments[0].click();", element)
            except Exception:
                raise
        self._take_screenshot("点击后")

    def click(self, **kwargs: Any) -> None:
        self.点击元素(**kwargs)

    # ============================================================
    # 关键字 4: 强制等待
    # ============================================================
    def 强制等待(self, **kwargs: Any) -> None:
        """固定等待若干秒。

        参数: 数据内容 / 秒数（数字或数字字符串）
        """
        val = kwargs.get("数据内容", kwargs.get("秒数", "2"))
        try:
            seconds = float(val)
        except (TypeError, ValueError):
            seconds = 2.0
        time.sleep(max(0.0, seconds))

    def sleep(self, **kwargs: Any) -> None:
        self.强制等待(**kwargs)

    # ============================================================
    # 关键字 5: 获取元素文本 -> 存入变量
    # ============================================================
    def 获取元素文本(self, **kwargs: Any) -> str:
        """获取元素文本，并按『变量名』字段存入全局变量池。

        参数:
            _页面元素: 元素别名
            变量名:     存入 g_context 的 key
        """
        element = self.find_element(**kwargs)
        text = (element.text or "").strip()
        var_name = str(kwargs.get("变量名", kwargs.get("var", ""))).strip()
        if var_name:
            g_context().set_dict(var_name, text)
            print(f"       ✅ 变量 {var_name} = {text[:60]}")
        self._take_screenshot(f"获取文本 {var_name or ''}")
        return text

    def get_text(self, **kwargs: Any) -> str:
        return self.获取元素文本(**kwargs)

    # ============================================================
    # 关键字 6: 断言文本（通用）
    # ============================================================
    def _do_assert(self, actual: Any, expected: Any, operator: str) -> None:
        """通用断言逻辑。"""
        actual_str = str(actual)
        expected_str = str(expected)

        op = (operator or "==").strip().lower()

        if op in ("==", "=", "eq", "equals", "相等", "等于"):
            assert actual_str == expected_str, (
                f"断言失败: {actual_str!r} == {expected_str!r}"
            )
        elif op in ("!=", "<>", "ne", "notequals", "不等于", "不相等"):
            assert actual_str != expected_str, (
                f"断言失败: {actual_str!r} != {expected_str!r}"
            )
        elif op in ("in", "包含于"):
            assert actual_str in expected_str, (
                f"断言失败: {actual_str!r} in {expected_str!r}"
            )
        elif op in ("contains", "包含", "含有"):
            assert expected_str in actual_str, (
                f"断言失败: {expected_str!r} 不包含于 {actual_str!r}"
            )
        elif op in ("not in", "!in", "不包含", "不含"):
            assert expected_str not in actual_str, (
                f"断言失败: {expected_str!r} 不应包含于 {actual_str!r}"
            )
        elif op in ("startswith", "开头是", "以...开头"):
            assert actual_str.startswith(expected_str), (
                f"断言失败: {actual_str!r} 不以 {expected_str!r} 开头"
            )
        elif op in ("endswith", "结尾是", "以...结尾"):
            assert actual_str.endswith(expected_str), (
                f"断言失败: {actual_str!r} 不以 {expected_str!r} 结尾"
            )
        elif op in (">", "gt", "大于"):
            assert float(actual_str) > float(expected_str), (
                f"断言失败: {actual_str} > {expected_str}"
            )
        elif op in (">=", "ge", "大于等于"):
            assert float(actual_str) >= float(expected_str), (
                f"断言失败: {actual_str} >= {expected_str}"
            )
        elif op in ("<", "lt", "小于"):
            assert float(actual_str) < float(expected_str), (
                f"断言失败: {actual_str} < {expected_str}"
            )
        elif op in ("<=", "le", "小于等于"):
            assert float(actual_str) <= float(expected_str), (
                f"断言失败: {actual_str} <= {expected_str}"
            )
        elif op in ("regex", "match", "正则"):
            import re
            assert re.search(expected_str, actual_str), (
                f"断言失败: {actual_str!r} 不匹配正则 {expected_str!r}"
            )
        else:
            # 默认按 == 处理
            assert actual_str == expected_str, (
                f"断言失败: {actual_str!r} == {expected_str!r} (运算符: {operator})"
            )

    def 断言文本(self, **kwargs: Any) -> None:
        """通用断言。

        参数:
            预期结果 / expected: 期望值
            实际结果 / actual:   实际值（可引用 {{变量名}}）
            比较符:             默认 ==
        """
        expected = kwargs.get("预期结果", kwargs.get("expected", ""))
        actual = kwargs.get("实际结果", kwargs.get("actual", ""))
        operator = str(kwargs.get("比较符", kwargs.get("operator", "==")) or "==")
        self._do_assert(actual, expected, operator)

    def assert_text(self, **kwargs: Any) -> None:
        self.断言文本(**kwargs)

    # ============================================================
    # 关键字 7: 断言文本相等
    # ============================================================
    def 断言文本相等(self, **kwargs: Any) -> None:
        kwargs["比较符"] = "=="
        self.断言文本(**kwargs)

    def 断言文本不相等(self, **kwargs: Any) -> None:
        kwargs["比较符"] = "!="
        self.断言文本(**kwargs)

    def 断言文本包含(self, **kwargs: Any) -> None:
        kwargs["比较符"] = "contains"
        self.断言文本(**kwargs)

    def 断言文本不包含(self, **kwargs: Any) -> None:
        kwargs["比较符"] = "not in"
        self.断言文本(**kwargs)

    # ============================================================
    # 关键字 8: 数字断言
    # ============================================================
    def 断言数字大于(self, **kwargs: Any) -> None:
        kwargs["比较符"] = ">"
        self.断言文本(**kwargs)

    def 断言数字小于(self, **kwargs: Any) -> None:
        kwargs["比较符"] = "<"
        self.断言文本(**kwargs)

    def 断言数字相等(self, **kwargs: Any) -> None:
        kwargs["比较符"] = "=="
        self.断言文本(**kwargs)

    # ============================================================
    # 关键字 9: 断言当前 URL
    # ============================================================
    def 断言浏览器路径(self, **kwargs: Any) -> None:
        """断言当前页面 URL。

        参数:
            数据内容: 期望的 URL 或部分路径
            比较符:   默认 contains
        """
        expected = str(kwargs.get("数据内容", kwargs.get("url", ""))).strip()
        operator = str(kwargs.get("比较符", "contains") or "contains")
        actual_url = self.driver.current_url or ""
        self._do_assert(actual_url, expected, operator)
        self._take_screenshot("URL断言")

    def assert_url(self, **kwargs: Any) -> None:
        self.断言浏览器路径(**kwargs)

    # ============================================================
    # 关键字 10: iframe 切换
    # ============================================================
    def iframe_switch_to(self, **kwargs: Any) -> None:
        """切换到指定 iframe（也支持通过别名定位）。

        参数:
            _页面元素: iframe 元素别名
            _索引:     数字索引（从 0 开始）—— 传这个时按索引切换
            _默认:     True/False —— 切回主文档
        """
        if kwargs.get("_默认"):
            self.driver.switch_to.default_content()
            return

        index_val = kwargs.get("_索引")
        if index_val is not None:
            try:
                idx = int(index_val)
                self.driver.switch_to.frame(idx)
                return
            except (TypeError, ValueError):
                pass

        element = self.find_element(**kwargs)
        self.driver.switch_to.frame(element)

    def 切换iframe(self, **kwargs: Any) -> None:
        self.iframe_switch_to(**kwargs)

    # ============================================================
    # 关键字 11: 图片验证码识别 (ddddocr)
    # ============================================================
    def image_recognition(self, **kwargs: Any) -> str:
        """对验证码图片进行 OCR 识别，并把结果存入变量。

        参数:
            _页面元素: 验证码 <img> 元素别名
            引用变量 / 变量名: 存入 g_context 的 key
        """
        if not _HAS_DDDDOCR:
            raise RuntimeError("缺少 ddddocr 依赖，请执行: pip install ddddocr")

        element = self.find_element(**kwargs)
        img_bytes = element.screenshot_as_png

        ocr = ddddocr.DdddOcr(show_ad=False)
        result = ocr.classification(img_bytes) or ""
        var_name = str(kwargs.get("引用变量", kwargs.get("变量名", "") or "")).strip()
        if var_name:
            g_context().set_dict(var_name, result)
            print(f"       ✅ 验证码变量 {var_name} = {result!r}")
        self._take_screenshot(f"验证码识别: {result}")
        return result

    def 识别验证码(self, **kwargs: Any) -> str:
        return self.image_recognition(**kwargs)

    # ============================================================
    # 关键字 12: 生成随机数
    # ============================================================
    def random_six_digit_number(self, **kwargs: Any) -> str:
        """生成 6 位随机数字字符串（可扩展到任意位数）。

        参数:
            位数 / n: 随机数位数（默认 6）
            变量名:   存入 g_context 的 key
        """
        try:
            n = int(kwargs.get("位数", kwargs.get("n", 6)))
        except (TypeError, ValueError):
            n = 6
        n = max(1, n)
        value = "".join(random.choices("0123456789", k=n))
        var_name = str(kwargs.get("变量名", "") or "").strip()
        if var_name:
            g_context().set_dict(var_name, value)
        return value

    def 生成随机数(self, **kwargs: Any) -> str:
        return self.random_six_digit_number(**kwargs)

    # ============================================================
    # 关键字 13: MySQL 数据提取
    # ============================================================
    def 提取数据MYSQL(self, **kwargs: Any) -> Dict[str, Any]:
        """执行一条 SQL 查询，把第一条结果作为字典存入变量。

        参数:
            _数据库: 数据库别名（在 context.yaml 的『_数据库』中配置）
            SQL / sql: 要执行的 SELECT 语句
            变量名:   存入 g_context 的 key（整个结果字典）

        context.yaml 数据库配置示例:
            _数据库:
              mysql001:
                host: 127.0.0.1
                port: 3306
                user: root
                password: 123456
                db: example_db
                charset: utf8mb4  # 可选
        """
        if not _HAS_PYMYSQL:
            raise RuntimeError("缺少 pymysql 依赖，请执行: pip install pymysql")

        db_alias = str(kwargs.get("_数据库", "") or "").strip()
        sql = str(kwargs.get("SQL", kwargs.get("sql", "")) or "").strip()
        if not db_alias:
            raise ValueError("『提取数据MYSQL』必须提供『_数据库』参数")
        if not sql:
            raise ValueError("『提取数据MYSQL』必须提供『SQL』参数")

        all_dbs = g_context().get_dict("_数据库") or {}
        db_cfg = all_dbs.get(db_alias)
        if not db_cfg:
            raise ValueError(f"找不到数据库别名『{db_alias}』的配置")

        host = str(db_cfg.get("host", ""))
        port = int(db_cfg.get("port", 3306))
        user = str(db_cfg.get("user", ""))
        password = str(db_cfg.get("password", ""))
        database = str(db_cfg.get("db", ""))
        charset = str(db_cfg.get("charset", "utf8mb4"))

        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset=charset,
            cursorclass=DictCursor,
        )
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                result = cursor.fetchone() or {}
        finally:
            conn.close()

        # 把结果拆成 key=value 也存入全局变量，方便在后续步骤中用 {{key}} 引用
        var_name = str(kwargs.get("变量名", "") or "").strip()
        if var_name:
            g_context().set_dict(var_name, result)
        if isinstance(result, dict):
            for k, v in result.items():
                g_context().set_dict(str(k), v)
            print(f"       ✅ 数据库查询结果: {list(result.keys())[:5]}...")

        return result

    def query_mysql(self, **kwargs: Any) -> Dict[str, Any]:
        return self.提取数据MYSQL(**kwargs)

    # ============================================================
    # 关键字 14: 切换到最新打开的窗口
    # ============================================================
    def switch_to_latest_handle(self, **kwargs: Any) -> None:
        """切换到最新打开的浏览器窗口。"""
        time.sleep(1)  # 等新窗口出现
        handles = self.driver.window_handles
        if not handles:
            raise RuntimeError("没有可用的浏览器窗口")
        self.driver.switch_to.window(handles[-1])
        self._take_screenshot("切换到新窗口")

    def 切换到最新窗口(self, **kwargs: Any) -> None:
        self.switch_to_latest_handle(**kwargs)

    # ============================================================
    # 关键字 15: 关闭浏览器
    # ============================================================
    def 关闭浏览器(self, **kwargs: Any) -> None:
        """关闭当前浏览器实例（通常在测试末尾调用）。"""
        try:
            self.driver.quit()
        except Exception:
            pass

    # ============================================================
    # 关键字 16: 元素可见/存在断言
    # ============================================================
    def 断言元素存在(self, **kwargs: Any) -> None:
        """断言元素存在于 DOM 中。"""
        self.find_element(**kwargs)  # 找不到会抛异常

    def 断言元素可见(self, **kwargs: Any) -> None:
        """断言元素可见。"""
        ele = self.find_element(**kwargs)
        assert ele.is_displayed(), "元素存在但不可见"

    def 断言元素不可见(self, **kwargs: Any) -> None:
        """断言元素不存在或不可见（常用于"隐藏某区域"的断言）。"""
        try:
            locator = self._resolve_locator(str(kwargs.get("_页面元素", "")))
            eles = self.driver.find_elements(*locator)
            if not eles:
                return  # 不存在 → OK
            for e in eles:
                if e.is_displayed():
                    raise AssertionError("元素仍然可见")
        except (TimeoutError, NoSuchElementException):
            pass

    # ============================================================
    # 关键字 17: 滚动到元素
    # ============================================================
    def 滚动到元素(self, **kwargs: Any) -> None:
        """把页面滚动到指定元素可见位置。"""
        element = self.find_element(**kwargs)
        self.driver.execute_script(
            "arguments[0].scrollIntoView({behavior:'smooth', block:'center'});",
            element,
        )
        time.sleep(0.5)

    # ============================================================
    # 关键字 18: JS 执行
    # ============================================================
    def 执行脚本(self, **kwargs: Any) -> Any:
        """在浏览器中执行 JavaScript 代码。

        参数:
            代码 / script: JS 代码字符串
            变量名:         把返回值存入 g_context
        """
        script = str(kwargs.get("代码", kwargs.get("script", ""))).strip()
        if not script:
            raise ValueError("『执行脚本』必须提供『代码』参数")
        result = self.driver.execute_script(script)
        var_name = str(kwargs.get("变量名", "") or "").strip()
        if var_name:
            g_context().set_dict(var_name, result)
        return result

    # ============================================================
    # 关键字 19: 下拉框选择
    # ============================================================
    def 选择下拉框(self, **kwargs: Any) -> None:
        """在 <select> 下拉框中选择一项。

        参数:
            _页面元素: select 元素别名
            文本 / text: 按可见文本选择
            值 / value:  按 value 属性选择
            索引 / index: 按数字索引选择（0 开始）
        """
        element = self.find_element(**kwargs)
        try:
            from selenium.webdriver.support.ui import Select  # type: ignore
            select = Select(element)
            by_text = str(kwargs.get("文本", kwargs.get("text", "")) or "")
            by_value = str(kwargs.get("值", kwargs.get("value", "")) or "")
            by_index = kwargs.get("索引", kwargs.get("index", None))
            if by_text:
                select.select_by_visible_text(by_text)
            elif by_value:
                select.select_by_value(by_value)
            elif by_index is not None:
                select.select_by_index(int(by_index))
            else:
                raise ValueError("『选择下拉框』至少指定『文本』/『值』/『索引』之一")
        except Exception:
            raise

    # ============================================================
    # 关键字 20: 键盘回车
    # ============================================================
    def 按回车(self, **kwargs: Any) -> None:
        """在指定元素或当前焦点处按下 Enter 键。"""
        element_alias = str(kwargs.get("_页面元素", "") or "").strip()
        if element_alias:
            self.find_element(**kwargs).send_keys(Keys.ENTER)
        else:
            ActionChains(self.driver).send_keys(Keys.ENTER).perform()

    # ============================================================
    # 扩展机制: 动态加载自定义关键字
    # ============================================================
    def ex_invoke(self, **kwargs: Any) -> Any:
        """从自定义关键字目录加载并执行关键字。

        参数:
            key:       关键字名（同时也是 Python 文件名 + 类名）
            其他字段:  转发给目标类方法

        目录: 由 context.yaml 的 key_dir 指定（如 ./HAT/key_dir）
        文件: {key}.py  类: {key}  方法: {key}
        """
        key = str(kwargs.get("key", "") or "").strip()
        key_dir = g_context().get_dict("key_dir")
        if not key:
            raise ValueError("ex_invoke 必须指定『key』参数")
        if not key_dir or not os.path.isdir(key_dir):
            raise ValueError(f"未配置合法的自定义关键字目录: key_dir={key_dir}")

        abs_dir = os.path.abspath(key_dir)
        if abs_dir not in sys.path:
            sys.path.insert(0, abs_dir)
        module_file = os.path.join(abs_dir, f"{key}.py")
        if not os.path.isfile(module_file):
            raise FileNotFoundError(f"自定义关键字文件不存在: {module_file}")

        import importlib.util
        spec = importlib.util.spec_from_file_location(key, module_file)
        if spec is None or spec.loader is None:
            raise ImportError(f"无法加载模块: {module_file}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls = getattr(module, key, None)
        if cls is None:
            raise AttributeError(f"模块 {key} 中未找到同名类 {key}")
        instance = cls(self.driver)
        method = getattr(instance, key, None)
        if method is None:
            raise AttributeError(f"类 {key} 中没有同名方法 {key}")
        return method(**kwargs)
