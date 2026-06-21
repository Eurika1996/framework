# -*- coding: utf-8 -*-
"""
浏览器驱动管理器 (WebCaseContext)

职责:
1. 根据配置启动浏览器驱动（Chrome / Firefox / IE / Remote Grid）
2. 支持浏览器会话复用（session_reuse: True）——所有用例共用一个浏览器实例
3. 支持 Selenium Grid 远程执行
4. 支持自定义启动参数（--headless 无头模式等）
5. 每个步骤自动截图，最终生成 HTML 轮播回放（在 release 时）
6. 异常或结束时安全关闭浏览器

典型配置 (context.yaml):
    _浏览器:
      grid_url: "http://192.168.1.102:4444/wd/hub"   # 可选
      capability:
        browserName: "chrome"
      options:
        args:
          - "--headless"
          - "--disable-gpu"
"""

from __future__ import annotations

import os
import sys
import time
import html
import base64
from datetime import datetime
from typing import Any, Dict, List, Optional

# 确保项目根目录在 sys.path 中
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_CURRENT_DIR))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from HAT.core.globalContext import g_context

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.firefox.service import Service as FirefoxService
    _HAS_SELENIUM = True
except ImportError:
    _HAS_SELENIUM = False

try:
    import allure
    _HAS_ALLURE = True
except ImportError:
    _HAS_ALLURE = False


# 全局共享的浏览器实例（用于 session_reuse）
_shared_driver = None
_shared_screenshots: List[str] = []  # 每步截图的 base64 列表


class WebCaseContext:
    """浏览器驱动管理器"""

    driver: Optional[Any] = None  # webdriver 实例
    keywords: Optional[Any] = None  # 关键字库实例
    _screenshots: List[str] = []  # 当前用例的截图列表

    def __init__(self) -> None:
        # 读取浏览器配置
        browser_cfg: Dict[str, Any] = g_context().get_dict("_浏览器") or {}
        self.config: Dict[str, Any] = browser_cfg

        # 是否复用浏览器
        session_reuse = g_context().get_dict("session_reuse")
        if isinstance(session_reuse, str):
            self.session_reuse: bool = session_reuse.strip().lower() in (
                "true", "1", "yes", "y"
            )
        else:
            self.session_reuse: bool = bool(session_reuse) if session_reuse is not None else False

        # 检测环境变量 HAT_HEADLESS - 优先使用命令行传入的模式
        self._force_headless: bool = (
            os.environ.get("HAT_HEADLESS", "").strip().lower()
            in ("1", "true", "yes", "y", "on")
        )

    # ============================================================
    # 初始化关键字库（同时创建浏览器）
    # ============================================================
    def init_keywords(self) -> Any:
        """创建关键字库实例。

        Returns:
            WebKeywords 实例
        """
        # 1. 决定是否使用共享浏览器
        global _shared_driver
        if self.session_reuse and _shared_driver is not None:
            # 检测 session 是否仍然有效（浏览器窗口可能已关闭）
            session_valid = False
            try:
                _shared_driver.current_url  # 轻量操作：如果 session 有效会返回 URL
                session_valid = True
            except Exception:
                session_valid = False
            if session_valid:
                self.driver = _shared_driver
            else:
                print("  [WebCaseContext] 检测到共享 session 已失效，重新创建浏览器...")
                self.driver = self._create_driver()
                _shared_driver = self.driver
        else:
            self.driver = self._create_driver()
            if self.session_reuse:
                _shared_driver = self.driver

        # 2. 创建关键字库实例
        from HAT.keywords.web_keywords import WebKeywords
        self.keywords = WebKeywords(self.driver)
        return self.keywords

    # ============================================================
    # 创建浏览器驱动
    # ============================================================
    def _create_driver(self) -> Any:
        """根据配置创建 webdriver 实例

        核心改进：
        1. 不传 driver_path，让 Selenium Manager 自动下载匹配版本的驱动
           （Selenium 4.6+ 内置 Selenium Manager 功能）
        2. 支持环境变量 HAT_HEADLESS=1 强制启用 headless 模式
        3. 自动添加一些通用参数避免启动失败
        """
        if not _HAS_SELENIUM:
            raise RuntimeError(
                "缺少 selenium 依赖，请执行: pip install selenium"
            )

        capability: Dict[str, Any] = self.config.get("capability", {}) or {}
        options_cfg: Dict[str, Any] = self.config.get("options", {}) or {}
        grid_url: Optional[str] = self.config.get("grid_url")
        driver_path: Optional[str] = self.config.get("driver_path")

        browser_name = (capability.get("browserName") or "chrome").lower().strip()

        # 从配置或环境变量合并启动参数
        base_args: List[str] = list(options_cfg.get("args", []) or [])
        env_headless = self._force_headless

        # ---- 远程 Grid 模式 ----
        if grid_url:
            from selenium.webdriver.common.options import ArgOptions
            remote_opts = ArgOptions()
            for k, v in capability.items():
                try:
                    setattr(remote_opts, k, v)
                except Exception:
                    remote_opts.set_capability(k, v)
            merged_args = list(base_args)
            if env_headless and not any("headless" in a.lower() for a in merged_args):
                merged_args.append("--headless")
            for arg in merged_args:
                try:
                    remote_opts.add_argument(str(arg))
                except Exception:
                    pass
            try:
                driver = webdriver.Remote(command_executor=grid_url, options=remote_opts)
            except Exception as e:
                raise RuntimeError(f"连接 Selenium Grid 失败 ({grid_url}): {e}") from e
            self._apply_common_driver_settings(driver)
            return driver

        # ---- 本地 Chrome ----
        if browser_name in ("chrome", "googlechrome", "gc"):
            opts = ChromeOptions()
            # 合并配置中的 args 和环境变量指定的参数
            chrome_args: List[str] = list(base_args)
            if env_headless and not any("headless" in a.lower() for a in chrome_args):
                chrome_args.append("--headless=new")
                chrome_args.append("--window-size=1920,1080")
                print(f"  [WebCaseContext] 检测到 HAT_HEADLESS=1，启用 headless 模式")

            # 添加稳定参数（避免部分环境启动失败）
            stability_args = ["--no-sandbox", "--disable-dev-shm-usage"]
            for arg in stability_args:
                if arg not in [a.lower() for a in chrome_args]:
                    chrome_args.append(arg)

            for arg in chrome_args:
                opts.add_argument(str(arg))

            # 默认去掉自动化提示
            opts.add_experimental_option("excludeSwitches", ["enable-automation"])
            opts.add_experimental_option("useAutomationExtension", False)

            # 策略：
            # 1. 如果用户指定了 driver_path，直接使用
            # 2. 否则先尝试 Selenium 自动管理（可能被 PATH 中的旧版驱动干扰）
            # 3. 如果自动管理因版本不兼容失败，用 selenium-manager --skip-driver-in-path
            #    强制跳过 PATH 驱动，获取匹配的驱动版本
            if driver_path:
                service = ChromeService(driver_path)
                driver = webdriver.Chrome(service=service, options=opts)
            else:
                try:
                    driver = webdriver.Chrome(options=opts)
                except Exception as first_err:
                    err_msg = str(first_err)
                    is_version_mismatch = (
                        "version of ChromeDriver" in err_msg
                        or "This version of ChromeDriver" in err_msg
                        or "session not created" in err_msg.lower()
                    )
                    if not is_version_mismatch:
                        raise

                    print(f"  [WebCaseContext] 检测到 ChromeDriver 版本不兼容: {err_msg[:80]}")
                    print(f"  [WebCaseContext] 正在通过 Selenium Manager 重新下载匹配版本...")

                    # 调用 selenium-manager --skip-driver-in-path 跳过 PATH 中的旧驱动
                    driver_path_v2 = None
                    try:
                        from selenium.webdriver.common.selenium_manager import SeleniumManager
                        import subprocess
                        import json

                        mgr = SeleniumManager()
                        binary = mgr._get_binary()
                        mgr_result = subprocess.run(
                            [binary, "--browser", "chrome",
                             "--skip-driver-in-path", "--output", "JSON"],
                            capture_output=True, text=True, timeout=300
                        )
                        if mgr_result.returncode == 0:
                            parsed = json.loads(mgr_result.stdout)
                            driver_path_v2 = (
                                parsed.get("result", {}).get("driver_path")
                            )
                            print(f"  [WebCaseContext] 新驱动路径: {driver_path_v2}")
                    except Exception as mgr_err:
                        print(f"  [WebCaseContext] Selenium Manager 调用失败: {mgr_err}")

                    if not driver_path_v2 or not os.path.exists(driver_path_v2):
                        # 回退：临时从 PATH 中移除 chromedriver 所在目录
                        # 然后让 Selenium Manager 重新下载
                        old_path = os.environ.get("PATH", "")
                        new_path_parts = []
                        for p in old_path.split(os.pathsep):
                            # 跳过可能包含 chromedriver 的目录
                            if not p or not os.path.isdir(p):
                                new_path_parts.append(p)
                                continue
                            try:
                                has_cd = any(
                                    f.lower().startswith("chromedriver")
                                    for f in os.listdir(p)
                                )
                                if has_cd:
                                    print(f"  [WebCaseContext] 跳过 PATH 目录: {p}")
                                    continue
                            except Exception:
                                pass
                            new_path_parts.append(p)
                        os.environ["PATH"] = os.pathsep.join(new_path_parts)

                        try:
                            driver = webdriver.Chrome(options=opts)
                        finally:
                            os.environ["PATH"] = old_path
                    else:
                        service = ChromeService(driver_path_v2)
                        driver = webdriver.Chrome(service=service, options=opts)

            self._apply_common_driver_settings(driver)
            return driver

        # ---- 本地 Firefox ----
        if browser_name in ("firefox", "ff", "mozilla"):
            opts = FirefoxOptions()
            ff_args = list(base_args)
            if env_headless and not any("headless" in a.lower() for a in ff_args):
                ff_args.append("--headless")
            for arg in ff_args:
                opts.add_argument(str(arg))
            if driver_path:
                service = FirefoxService(driver_path)
                driver = webdriver.Firefox(service=service, options=opts)
            else:
                driver = webdriver.Firefox(options=opts)
            self._apply_common_driver_settings(driver)
            return driver

        # ---- IE (不推荐，但保持兼容) ----
        if browser_name in ("ie", "internetexplorer", "internet explorer"):
            driver = webdriver.Ie()
            self._apply_common_driver_settings(driver)
            return driver

        raise ValueError(f"暂不支持的浏览器: {browser_name}")

    def _apply_common_driver_settings(self, driver: Any) -> None:
        """对浏览器应用通用设置（窗口大小、超时等）"""
        try:
            options_cfg = self.config.get("options", {}) or {}
            # 没有显式传入 --window-size 时，最大化窗口（非 headless 模式）
            args_list = [str(a).lower() for a in options_cfg.get("args", []) or []]
            has_size = any("window-size" in a for a in args_list)
            has_headless = any("headless" in a for a in args_list)
            # 同时考虑环境变量强制的 headless 模式
            is_headless = has_headless or self._force_headless
            if not has_size and not is_headless:
                try:
                    driver.maximize_window()
                except Exception:
                    pass
            # 默认超时
            driver.set_page_load_timeout(30)
            driver.implicitly_wait(3)
        except Exception:
            pass  # 某些浏览器可能不支持某些操作

    # ============================================================
    # 截图 / 轮播 HTML
    # ============================================================
    def take_screenshot(self, label: str = "") -> None:
        """对当前页面截图并保存到内存列表

        Args:
            label: 截图标签（显示在报告中）
        """
        if self.driver is None:
            return
        try:
            png = self.driver.get_screenshot_as_base64()
            self._screenshots.append((label, png))
            _shared_screenshots.append((label, png))
            # 如果有 allure，附加截图
            if _HAS_ALLURE:
                try:
                    import allure
                    allure.attach(
                        base64.b64decode(png),
                        name=label or "screenshot",
                        attachment_type=allure.attachment_type.PNG,
                    )
                except Exception:
                    pass
        except Exception as e:
            print(f"    ⚠ 截图失败: {e}")

    def _build_carousel_html(self, items: List[tuple]) -> str:
        """生成简单的 HTML 轮播回放"""
        if not items:
            return ""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        slides_html = []
        for idx, (label, png_b64) in enumerate(items):
            label_html = html.escape(label or f"Step {idx + 1}")
            slides_html.append(
                f"<div class='slide'><h3>{idx + 1}. {label_html}</h3>"
                f"<img src='data:image/png;base64,{png_b64}' /></div>"
            )

        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>测试回放 - {timestamp}</title>
<style>
body {{ font-family: sans-serif; background:#1e1e1e; color:#eee; margin:0; padding:20px; }}
h1 {{ color:#4ec9b0; }} .slide {{ margin-bottom:30px; padding:10px; background:#252526; border-radius:8px; }}
.slide img {{ max-width:100%; border:1px solid #333; border-radius:4px; }}
.slide h3 {{ color:#9cdcfe; margin: 10px 0; }}
</style></head><body>
<h1>测试步骤回放 ({len(items)} 张截图)</h1>
<p>生成时间: {timestamp}</p><hr/>
{''.join(slides_html)}
</body></html>"""

    # ============================================================
    # 释放资源
    # ============================================================
    def release(self) -> None:
        """释放资源（截图轮播 + 关闭浏览器）"""
        # 1. 生成本次用例的 HTML 回放
        if self._screenshots:
            try:
                log_dir = os.path.join(_PROJECT_ROOT, "HAT", "logs")
                os.makedirs(log_dir, exist_ok=True)
                fname = f"replay_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.html"
                fpath = os.path.join(log_dir, fname)
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(self._build_carousel_html(self._screenshots))
                print(f"    📷 回放HTML: {fpath}")
            except Exception as e:
                print(f"    ⚠ 生成回放HTML失败: {e}")
            self._screenshots = []

        # 2. 关闭浏览器
        global _shared_driver
        if self.session_reuse:
            # 复用模式下，只在全部用例结束时才关闭
            # 这里选择暂时不关闭，由进程退出时自动清理，
            # 或提供手动关闭接口 close_shared_driver()
            return

        if self.driver is not None:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None


def close_shared_driver() -> None:
    """手动关闭共享浏览器（用于脚本结束时清理）"""
    global _shared_driver
    if _shared_driver is not None:
        try:
            _shared_driver.quit()
        except Exception:
            pass
        _shared_driver = None
