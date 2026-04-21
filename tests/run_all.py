#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""运行所有测试"""

import sys
import time

def main():
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + "  RAG 系统 - 完整测试套件".center(58) + "║")
    print("╚" + "="*58 + "╝")

    all_passed = True

    # 1. 文档模块测试
    print("\n\n>>> 文档模块测试 <<<")
    from tests.test_file_api import main as file_tests
    if not file_tests():
        all_passed = False
    time.sleep(2)

    # 2. 对话模块测试
    print("\n\n>>> 对话模块测试 <<<")
    from tests.test_chat_api import main as chat_tests
    chat_tests()
    time.sleep(2)

    # 3. 并发测试
    print("\n\n>>> 并发测试 <<<")
    from tests.test_concurrent import main as concurrent_tests
    if not concurrent_tests():
        all_passed = False

    print("\n")
    print("="*60)
    if all_passed:
        print("✓ 所有测试套件通过!")
    else:
        print("⚠ 部分测试失败")
    print("="*60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
