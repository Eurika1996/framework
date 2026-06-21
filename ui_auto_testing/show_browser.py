# -*- coding: utf-8 -*-
"""
非无头模式打开页面 - 用 Selenium Manager 解决版本问题
"""
import os, sys, time, json, subprocess, shutil
os.environ["PYTHONIOENCODING"] = "utf-8"

# ============= 用 selenium-manager 获取正确版本的 driver =============
print("[1/3] 正在用 Selenium Manager 获取匹配的 ChromeDriver...")
binary = None
# 找 selenium-manager.exe
sel_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if False else os.path.dirname(
    os.path.dirname(__import__("selenium").__file__)
)
for root, dirs, files in os.walk(sel_dir):
    if "selenium-manager.exe" in files:
        binary = os.path.join(root, "selenium-manager.exe")
        break

if not binary:
    binary = shutil.which("selenium-manager")

if not binary:
    print(f"   警告: 未找到 selenium-manager，Selenium 目录: {sel_dir}")
    sys.exit(1)

print(f"   selenium-manager: {binary}")

result = subprocess.run(
    [binary, "--browser", "chrome", "--skip-driver-in-path", "--output", "JSON"],
    capture_output=True, text=True
)
print(f"   退出码: {result.returncode}")

driver_path = None
if result.returncode == 0:
    parsed = json.loads(result.stdout)
    driver_path = parsed.get("result", {}).get("driver_path")
    print(f"   匹配的 ChromeDriver: {driver_path}")
else:
    print(f"   stderr: {result.stderr[:500]}")
    # 尝试不带 --skip-driver-in-path
    result2 = subprocess.run([binary, "--browser", "chrome", "--output", "JSON"], capture_output=True, text=True)
    if result2.returncode == 0:
        parsed = json.loads(result2.stdout)
        driver_path = parsed.get("result", {}).get("driver_path")
        print(f"   [备选] ChromeDriver: {driver_path}")

# ============= 启动浏览器 =============
print("\n[2/3] 启动 Chrome 浏览器（可视化模式）...")

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

opts = Options()
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--start-maximized")
opts.add_argument("--disable-popup-blocking")
opts.add_experimental_option("detach", True)  # 脚本退出后保持打开
opts.add_experimental_option("excludeSwitches", ["enable-automation"])

if driver_path and os.path.isfile(driver_path):
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=opts)
else:
    print("   未找到匹配 driver，尝试默认方式...")
    driver = webdriver.Chrome(options=opts)

# ============= 打开页面 =============
print("\n[3/3] 打开测试页面...")
driver.get("http://127.0.0.1:18080/")

print()
print("=" * 60)
print(f"✓ 页面标题: {driver.title}")
print(f"✓ 浏览器已打开，请在窗口中操作")
print("=" * 60)
print()
print("你可以尝试：")
print("  1. 左侧导航点击切换不同模块")
print("  2. 点击列表中的项目 → 查看详情面板")
print("  3. 点击『+ 新建...』按钮 → 创建新条目")
print("  4. 点击列表项右侧『删除』→ 确认删除")
print("  5. 切换到对话模块 → 输入消息并发送")
print()
print("浏览器窗口保持打开，请直接在浏览器中操作。")
print("完成后你可以在浏览器中直接关闭窗口。")
print()
