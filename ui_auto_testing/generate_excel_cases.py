# -*- coding: utf-8 -*-
"""
快速生成 Excel 格式测试用例的脚本
====================================
运行后会在 ./hat-test-cases/ 目录下生成一个示例 Excel 用例文件

Excel 用例格式说明:
    - 每行一个步骤，相同用例标题的行归为同一个用例
    - 列名: 一级模块 | 二级模块 | 用例标题 | 步骤描述 | 操作类型 | 元素定位 | 参数内容

运行命令:
    python generate_excel_cases.py
"""

import os
import sys

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill
except ImportError:
    print('[错误] 缺少 openpyxl 依赖，请先安装:')
    print('  pip install openpyxl\n')
    sys.exit(1)


def create_excel_case(output_path):
    """创建示例 Excel 格式测试用例"""

    wb = Workbook()
    ws = wb.active
    ws.title = "CSGClaw测试用例"

    # 设置标题样式
    header_font = Font(bold=True, size=12, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # 写入表头
    headers = [
        "一级模块",
        "二级模块",
        "用例标题",
        "步骤描述",
        "操作类型",
        "元素定位_名称",
        "输入数据/预期值",
        "备注"
    ]
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align

    # 设置列宽
    col_widths = [12, 12, 20, 20, 12, 18, 25, 20]
    for idx, width in enumerate(col_widths, 1):
        ws.column_dimensions[chr(64 + idx)].width = width

    # 写入示例测试用例
    cases = [
        # Case 1: 页面加载
        ("基础功能", "页面加载", "服务启动验证",
         "访问服务首页", "访问网址", "", "http://127.0.0.1:18080/", "基础验证"),
        ("基础功能", "页面加载", "服务启动验证",
         "等待页面加载", "强制等待", "", "3", ""),
        ("基础功能", "页面加载", "服务启动验证",
         "验证URL正确", "断言浏览器路径", "", "http://127.0.0.1:18080", ""),

        # Case 2: Agent 列表
        ("Agent管理", "列表验证", "Agent列表页面",
         "进入Agent页面", "点击元素", "Agent_导航链接", "", ""),
        ("Agent管理", "列表验证", "Agent列表页面",
         "等待加载", "强制等待", "", "2", ""),
        ("Agent管理", "列表验证", "Agent列表页面",
         "获取列表内容", "获取元素文本", "Agent_列表容器", "agent_list", "存入变量"),
        ("Agent管理", "列表验证", "Agent列表页面",
         "验证非空", "断言文本包含", "", "", "{{agent_list}}"),

        # Case 3: 对话功能
        ("对话功能", "消息发送", "对话发送消息验证",
         "进入对话页面", "点击元素", "对话_导航链接", "", ""),
        ("对话功能", "消息发送", "对话发送消息验证",
         "等待页面", "强制等待", "", "2", ""),
        ("对话功能", "消息发送", "对话发送消息验证",
         "输入测试消息", "输入内容", "对话_消息输入框", "你好，请介绍自己", ""),
        ("对话功能", "消息发送", "对话发送消息验证",
         "点击发送", "点击元素", "对话_发送按钮", "", ""),
        ("对话功能", "消息发送", "对话发送消息验证",
         "等待响应", "强制等待", "", "8", "等待AI响应"),
        ("对话功能", "消息发送", "对话发送消息验证",
         "获取消息列表", "获取元素文本", "对话_消息列表", "messages", ""),
        ("对话功能", "消息发送", "对话发送消息验证",
         "验证消息发送成功", "断言文本包含", "", "请介绍自己", "{{messages}}"),
    ]

    for row_idx, case in enumerate(cases, 2):
        for col_idx, value in enumerate(case, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

    # 保存文件
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    wb.save(output_path)
    print(f'[OK] Excel 用例已生成: {output_path}')
    print(f'     共 {len(cases)} 行步骤数据')


if __name__ == '__main__':
    output_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'hat-test-cases',
        'CSGClaw_测试用例示例.xlsx'
    )
    print('\n正在生成 Excel 测试用例示例...')
    create_excel_case(output_file)
    print('\n完成！使用 --type excel 参数运行 Excel 用例。\n')
