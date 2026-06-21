# -*- coding: utf-8 -*-
import os, sys, time
os.environ['HAT_HEADLESS'] = '1'
os.environ['PYTHONIOENCODING'] = 'utf-8'

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from HAT.context.WebCaseContext import WebCaseContext

print('=' * 60)
print('  测试: 创建 Chrome 驱动 (headless)')
print('=' * 60)
ctx = WebCaseContext()
keywords = ctx.init_keywords()
print('  驱动创建成功')
print(f'  Chrome 版本: {keywords.driver.capabilities.get("browserVersion", "unknown")}')

# 访问一个简单的网站
print()
print('  测试: 访问 https://example.com')
keywords.访问网址(网址='https://example.com')
time.sleep(2)
print(f'  当前 URL: {keywords.driver.current_url}')
print(f'  标题: {keywords.driver.title}')

# 查找页面元素
h1_elements = keywords.driver.find_elements('tag name', 'h1')
print(f'  页面标题元素数量: {len(h1_elements)}')
if h1_elements:
    print(f'  第一个 h1 文本: {h1_elements[0].text}')

# 清理
ctx.release()
print()
print('=' * 60)
print('  全部测试通过')
print('=' * 60)
