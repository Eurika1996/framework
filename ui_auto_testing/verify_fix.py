# -*- coding: utf-8 -*-
"""快速验证: Agent/房间/Hub 列表项点击 + 删除流程"""
import os, sys, json
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["HAT_HEADLESS"] = "1"

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-gpu")
opts.add_argument("--window-size=1920,1080")

# 使用 selenium-manager --skip-driver-in-path
import subprocess, shutil
binary = shutil.which("selenium-manager") or None
if not binary:
    import selenium
    sel_dir = os.path.dirname(selenium.__file__)
    for f in ["selenium-manager.exe", "selenium-manager"]:
        c = os.path.join(sel_dir, "webdriver", "common", "windows", f)
        if os.path.isfile(c): binary = c; break

driver_path = None
if binary:
    r = subprocess.run([binary, "--browser", "chrome", "--skip-driver-in-path", "--output", "JSON"], capture_output=True, text=True)
    if r.returncode == 0:
        driver_path = json.loads(r.stdout).get("result", {}).get("driver_path")
print(f"ChromeDriver: {driver_path}")

if driver_path and os.path.exists(driver_path):
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=opts)
else:
    driver = webdriver.Chrome(options=opts)

passed = 0
failed = 0

try:
    # ===== 测试 1: Agent 列表项点击查看详情 =====
    print("\n[1] Agent列表项点击 → 详情显示")
    driver.get("http://127.0.0.1:18080/")
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#panel-agents .agent-item")))
    agent_item = driver.find_element(By.CSS_SELECTOR, "#panel-agents .agent-item")
    agent_item.click()
    # 等待详情面板可见
    detail = WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#panel-agents .detail-pane")))
    if detail and len(detail.text) > 5:
        print(f"  ✅ 通过 - 详情: {detail.text[:50]}")
        passed += 1
    else:
        print("  ❌ 失败 - 详情面板内容为空")
        failed += 1

    # ===== 测试 2: 切换到房间列表 =====
    print("\n[2] 切换到房间 - 房间列表项点击 → 详情显示")
    driver.find_element(By.CSS_SELECTOR, "a[data-panel='rooms']").click()
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#panel-rooms .room-item")))
    room_item = driver.find_element(By.CSS_SELECTOR, "#panel-rooms .room-item")
    room_item.click()
    detail = WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#panel-rooms .detail-pane")))
    if detail and len(detail.text) > 5:
        print(f"  ✅ 通过 - 详情: {detail.text[:50]}")
        passed += 1
    else:
        print("  ❌ 失败 - 房间详情面板未显示")
        failed += 1

    # ===== 测试 3: 切换到 Hub 列表 =====
    print("\n[3] 切换到 Hub - Hub列表项点击 → 详情显示")
    driver.find_element(By.CSS_SELECTOR, "a[data-panel='hubs']").click()
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#panel-hubs .hub-item")))
    hub_item = driver.find_element(By.CSS_SELECTOR, "#panel-hubs .hub-item")
    hub_item.click()
    detail = WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#panel-hubs .detail-pane")))
    if detail and len(detail.text) > 5:
        print(f"  ✅ 通过 - 详情: {detail.text[:50]}")
        passed += 1
    else:
        print("  ❌ 失败 - Hub详情面板未显示")
        failed += 1

    # ===== 测试 4: Agent 删除流程 =====
    print("\n[4] Agent删除流程 - 点击删除按钮 → 确认删除")
    driver.find_element(By.CSS_SELECTOR, "a[data-panel='agents']").click()
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#panel-agents .agent-item")))
    delete_btn = driver.find_element(By.CSS_SELECTOR, "#panel-agents .agent-item .action-btn.delete")
    delete_btn.click()
    print("  - 已点击删除按钮")
    WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.ID, "delete-modal")))
    print("  - 删除确认对话框已显示")
    driver.find_element(By.CSS_SELECTOR, "#delete-modal .btn-danger").click()
    print("  - 已点击确认删除")
    WebDriverWait(driver, 5).until(EC.invisibility_of_element_located((By.ID, "delete-modal")))
    print("  - 对话框已关闭")
    # 检查列表容器仍可见
    list_container = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#panel-agents .agent-list")))
    print(f"  ✅ 通过 - 列表容器仍可见 (文本长度: {len(list_container.text)})")
    passed += 1

    # ===== 测试 5: 创建新 Agent =====
    print("\n[5] 创建新 Agent")
    # 先重新加载页面获取一个新的 agent
    driver.get("http://127.0.0.1:18080/")
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#panel-agents .agent-item")))
    driver.find_element(By.CSS_SELECTOR, "#panel-agents .btn-create").click()
    WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.ID, "agent-create-form")))
    name_input = driver.find_element(By.CSS_SELECTOR, "#agent-create-form input[name='name']")
    name_input.click()
    name_input.clear()
    name_input.send_keys("测试智能体")
    desc_input = driver.find_element(By.CSS_SELECTOR, "#agent-create-form textarea[name='description']")
    desc_input.click()
    desc_input.clear()
    desc_input.send_keys("测试用描述")
    driver.find_element(By.CSS_SELECTOR, "#agent-create-form .btn-primary").click()
    print("  - 已提交创建表单")
    WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.ID, "agent-detail")))
    print(f"  ✅ 通过 - 新 Agent 创建成功，详情显示: {driver.find_element(By.ID, 'agent-detail').text[:40]}")
    passed += 1

    print(f"\n{'='*50}")
    print(f"  汇总: {passed} 通过 / {failed} 失败")
    if failed == 0:
        print("  ✅ 全部验证通过！")
    print(f"{'='*50}\n")
    sys.exit(0 if failed == 0 else 1)

except Exception as e:
    print(f"\n❌ 异常: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    try: driver.quit()
    except: pass
