"""
HAT 自动化测试框架 - 主入口
用法:
    python main.py                                              # 运行全部用例（同时生成 Allure 结果）
    python main.py --case examples/api-cases-yaml/1-health.yaml # 指定用例目录/文件
    python main.py --alluredir allure-results                  # 指定报告目录（默认 allure-results）
    python main.py --no-allure                                   # 不生成 Allure 结果
    python main.py --open                                       # 运行后自动打开 Allure 报告
"""

import os
import sys
import argparse
import subprocess
import webbrowser
import pytest


def _detect_allure_cli():
    """检测系统是否有 allure 命令行工具"""
    import shutil
    allure_path = shutil.which("allure")
    if not allure_path:
        allure_path = shutil.which("allure.bat")
    if not allure_path:
        return None
    try:
        result = subprocess.run(
            [allure_path, "--version"],
            capture_output=True, text=True, timeout=10,
            shell=(os.name == "nt")
        )
        if result.returncode == 0:
            output = result.stdout.strip() or result.stderr.strip()
            return output or "available"
    except Exception:
        pass
    return "available"


def _generate_allure_report(results_dir, report_dir="allure-report"):
    """根据 allure 结果生成 HTML 报告"""
    import shutil
    results_abs = os.path.abspath(results_dir)
    report_abs = os.path.abspath(report_dir)
    print(f"\n[INFO] 正在生成 Allure 报告: {results_abs} -> {report_abs}")
    allure_cmd = shutil.which("allure") or shutil.which("allure.bat") or "allure"
    try:
        subprocess.run(
            [allure_cmd, "generate", results_abs, "-o", report_abs, "--clean"],
            check=True,
            capture_output=False,
            shell=(os.name == "nt")
        )
        print(f"[INFO] 报告已生成: {report_abs}")
        print(f"       查看方式: allure open {report_abs}")
        return report_abs
    except Exception as e:
        print(f"[WARN] 报告生成失败: {e}")
        print(f"       请确保已安装 Allure 命令行工具")
        return None


def main():
    parser = argparse.ArgumentParser(description="HAT 自动化测试框架", formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--case", "-c",
        default=None,
        help="用例文件或目录路径（默认: examples/api-cases-yaml）"
    )
    parser.add_argument(
        "--alluredir",
        default=None,
        help="Allure 结果目录（默认: allure-results，设置 --no-allure 禁用）"
    )
    parser.add_argument(
        "--no-allure",
        action="store_true",
        help="禁用 Allure 结果收集"
    )
    parser.add_argument(
        "--report",
        default=None,
        help="运行后生成 Allure 报告目录（如 allure-report），若指定会自动调用 allure generate"
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="运行完成后自动在浏览器打开报告（需要与 --report 一起使用）"
    )

    args, extra = parser.parse_known_args()

    # 用例路径
    case_path = args.case or os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "examples", "api-cases-yaml"
    )
    case_path = os.path.normpath(case_path)

    # Allure 目录
    allure_dir = None
    if not args.no_allure:
        allure_dir = os.path.abspath(args.alluredir or "allure-results")

    print("=" * 60)
    print("  HAT 自动化测试框架")
    print(f"  用例路径: {case_path}")
    if allure_dir:
        print(f"  Allure 结果: {allure_dir}")
        allure_version = _detect_allure_cli()
        if allure_version:
            print(f"  Allure CLI: v{allure_version}")
        else:
            print(f"  Allure CLI: 未检测到（将仍然生成 JSON 结果，但无法生成 HTML 报告）")
    else:
        print(f"  Allure: 已禁用")
    print("=" * 60)

    # 确保可以导入 HAT 包
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # 收集用例
    from HAT.core.TestRunner import _collect_all_cases

    case_infos, case_names = _collect_all_cases(case_path)

    if not case_infos:
        print(f"[ERROR] 在 {case_path} 中没有找到用例文件")
        return 1

    print(f"[INFO] 共找到 {len(case_infos)} 条测试用例")
    for i, name in enumerate(case_names[:10], 1):
        print(f"  {i:>3}. {name}")
    if len(case_names) > 10:
        print(f"  ... 及其他 {len(case_names) - 10} 条")
    print()

    # 生成临时 pytest 文件
    tmp_py_content = '''# 自动生成 - 不要修改
import os, sys
sys.path.insert(0, {0!r})

import pytest
from HAT.core.TestRunner import _execute_case

CASES = {1!r}
CASE_NAMES = {2!r}

@pytest.mark.parametrize("case", CASES, ids=CASE_NAMES)
def test_case(case):
    _execute_case(case)
'''.format(project_root, case_infos, case_names)

    tmp_path = os.path.join(project_root, "_auto_generated_tests.py")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(tmp_py_content)

    # 构建 pytest 参数
    pytest_args = [tmp_path, "-v", "--tb=short"]

    if allure_dir:
        pytest_args += ["--alluredir", allure_dir]

    if extra:
        pytest_args.extend(extra)

    # 清理旧的 allure 结果目录（避免老数据干扰）
    if allure_dir and os.path.isdir(allure_dir):
        import shutil
        try:
            shutil.rmtree(allure_dir)
        except Exception:
            pass

    try:
        exit_code = pytest.main(pytest_args)
    finally:
        try:
            if os.path.isfile(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass

    # 生成 HTML 报告
    if allure_dir and args.report:
        report_dir = _generate_allure_report(allure_dir, args.report)
        if report_dir and args.open:
            index_html = os.path.join(report_dir, "index.html")
            if os.path.isfile(index_html):
                print(f"\n[INFO] 在浏览器中打开: file:///{index_html}")
                try:
                    webbrowser.open(f"file:///{index_html}")
                except Exception as e:
                    print(f"[WARN] 打开浏览器失败: {e}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
