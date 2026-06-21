# -*- coding: utf-8 -*-
"""
元素定位准确性验证
逐个检查 context.yaml 中的所有 CSS 选择器是否能在实际页面中找到元素
"""
import os, sys, json
os.environ["PYTHONIOENCODING"] = "utf-8"

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ============= 元素定位表（从 context.yaml 提取） =============
ELEMENTS = {
    # ---- 导航与全局 ----
    "页面标题": ".panel.active h1",
    "侧边栏导航": "nav[role='navigation']",
    "新建按钮": ".panel.active .btn-create",
    "删除确认按钮": "#delete-modal .btn-danger",
    "取消按钮": ".panel.active .btn-secondary",

    # ---- Agent ----
    "Agent_导航链接": "a[data-panel='agents']",
    "Agent_列表容器": "#panel-agents .agent-list",
    "Agent_列表项": "#panel-agents .agent-item",
    "Agent_名称输入框": "#panel-agents input[name='name']",
    "Agent_描述输入框": "#panel-agents textarea[name='description']",
    "Agent_保存按钮": "#panel-agents .btn-primary",
    "Agent_删除按钮": "#panel-agents .agent-item .action-btn.delete",
    "Agent_编辑按钮": "#panel-agents .agent-item .action-btn.edit-btn",
    "Agent_详情面板": "#panel-agents .detail-pane",

    # ---- Chat ----
    "对话_导航链接": "a[data-panel='chat']",
    "对话_消息列表": "#panel-chat .message-list",
    "对话_消息项": "#panel-chat .message-item",
    "对话_消息输入框": "#panel-chat textarea[name='message']",
    "对话_发送按钮": "#panel-chat .send-btn",
    "对话_用户消息": "#panel-chat .user-message",
    "对话_AI消息": "#panel-chat .agent-message",
    "对话_新房间按钮": "#panel-chat .btn-create",
    "对话_正在输入提示": "#panel-chat .typing-indicator",

    # ---- Room ----
    "房间_导航链接": "a[data-panel='rooms']",
    "房间_列表容器": "#panel-rooms .room-list",
    "房间_列表项": "#panel-rooms .room-item",
    "房间_名称输入框": "#panel-rooms input[name='roomName']",
    "房间_保存按钮": "#panel-rooms .btn-primary",
    "房间_详情面板": "#panel-rooms .detail-pane",

    # ---- Hub ----
    "Hub_导航链接": "a[data-panel='hubs']",
    "Hub_列表容器": "#panel-hubs .hub-list",
    "Hub_列表项": "#panel-hubs .hub-item",
    "Hub_名称输入框": "#panel-hubs input[name='hubName']",
    "Hub_保存按钮": "#panel-hubs .btn-primary",
    "Hub_详情面板": "#panel-hubs .detail-pane",

    # ---- Computer ----
    "计算机_导航链接": "a[data-panel='computer']",
    "计算机_工作区信息": "#panel-computer .detail-pane",
    "计算机_工作区路径": "#panel-computer .workspace-path",
    "计算机_状态指示": "#panel-computer .status-pill",

    # ---- Human ----
    "用户_导航链接": "a[data-panel='humans']",
    "用户_列表容器": "#panel-humans .human-list",
    "用户_列表项": "#panel-humans .list-item",
    "用户_名称输入框": "#panel-humans input[name='userName']",
    "用户_保存按钮": "#panel-humans .btn-primary",
}

# ============= 导航映射 =============
NAV_PANEL_MAP = {
    "Agent": "a[data-panel='agents']",
    "对话": "a[data-panel='chat']",
    "房间": "a[data-panel='rooms']",
    "Hub": "a[data-panel='hubs']",
    "计算机": "a[data-panel='computer']",
    "用户": "a[data-panel='humans']",
}

# ============= 启动浏览器 =============
opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-gpu")

driver = webdriver.Chrome(options=opts)

results = []  # (name, selector, count, visible_count, issue)

def check_element(name, selector, driver):
    """检查单个元素是否存在且可见"""
    try:
        els = driver.find_elements(By.CSS_SELECTOR, selector)
        count = len(els)
        visible_count = sum(1 for e in els if e.is_displayed())

        issue = ""
        if count == 0:
            issue = "⚠ 找不到元素"
        elif visible_count == 0:
            issue = "⚠ 找到元素但都不可见"
        return (name, selector, count, visible_count, issue)
    except Exception as e:
        return (name, selector, 0, 0, f"❌ 错误: {e}")

try:
    print("=" * 70)
    print("  元素定位验证 - 开始")
    print(f"  访问: http://127.0.0.1:18080/")
    print("=" * 70)
    driver.get("http://127.0.0.1:18080/")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".panel.active")))

    # 先验证 Agent 模块下的元素（默认显示）
    print("\n【默认页面 - Agent 管理】")
    for name, sel in ELEMENTS.items():
        if "Agent" in name or name in ["页面标题", "侧边栏导航", "新建按钮"]:
            results.append(check_element(name, sel, driver))

    # 切换到对话模块
    print("\n【切换到 对话 模块】")
    driver.find_element(By.CSS_SELECTOR, "a[data-panel='chat']").click()
    import time; time.sleep(0.3)
    for name, sel in ELEMENTS.items():
        if name.startswith("对话") or name == "新建按钮":
            results.append(check_element(name, sel, driver))

    # 切换到房间模块
    print("\n【切换到 房间 模块】")
    driver.find_element(By.CSS_SELECTOR, "a[data-panel='rooms']").click()
    time.sleep(0.3)
    for name, sel in ELEMENTS.items():
        if name.startswith("房间") or name == "新建按钮":
            results.append(check_element(name, sel, driver))

    # 切换到 Hub 模块
    print("\n【切换到 Hub 模块】")
    driver.find_element(By.CSS_SELECTOR, "a[data-panel='hubs']").click()
    time.sleep(0.3)
    for name, sel in ELEMENTS.items():
        if name.startswith("Hub") or name == "新建按钮":
            results.append(check_element(name, sel, driver))

    # 切换到计算机模块
    print("\n【切换到 计算机 模块】")
    driver.find_element(By.CSS_SELECTOR, "a[data-panel='computer']").click()
    time.sleep(0.3)
    for name, sel in ELEMENTS.items():
        if name.startswith("计算机") or name == "新建按钮":
            results.append(check_element(name, sel, driver))

    # 切换到用户模块
    print("\n【切换到 用户 模块】")
    driver.find_element(By.CSS_SELECTOR, "a[data-panel='humans']").click()
    time.sleep(0.3)
    for name, sel in ELEMENTS.items():
        if name.startswith("用户") or name == "新建按钮":
            results.append(check_element(name, sel, driver))

    # ============= 总结 =============
    print("\n" + "=" * 70)
    print("  验证结果汇总")
    print("=" * 70)

    # 去重显示
    seen = set()
    ok_count = 0
    warn_count = 0
    error_count = 0

    for name, selector, count, visible, issue in results:
        if name in seen:
            continue
        seen.add(name)

        if issue == "":
            status = f"✓  OK (找到 {count} 个, 可见 {visible} 个)"
            ok_count += 1
        elif "找不到元素" in issue:
            status = f"✗  {issue}"
            error_count += 1
        else:
            status = f"!  {issue}"
            warn_count += 1

        print(f"  {status:<40s} [{name}]")
        if issue != "":
            print(f"    → {selector}")

    print()
    print(f"  总计: {ok_count} 通过 / {warn_count} 警告 / {error_count} 失败")
    print("=" * 70)

    # 潜在问题提示
    print("\n【需要注意的问题】")
    print("  1. 列表项的点击事件: 静态列表项需要 JS 处理才能触发详情")
    print("  2. 表单区域: 输入框默认 display:none，需要先点击『新建』才显示")
    print("  3. 详情面板: 默认 display:none，需要点击列表项后才显示")
    print("  4. 删除对话框: 默认隐藏，需要先点击『删除』按钮才显示")
    print()

finally:
    driver.quit()
