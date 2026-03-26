#!/usr/bin/env python3
# coding=utf-8
# Author: shenjiawei
"""
Legacy entry script for the Tomato timer.

原始的大部分实现（计时、日历、笔记、CLI 参数解析等）
已经被重构到了 ``tomato_app`` 包中：

- 核心逻辑：``tomato_app.core``
- 命令行入口：``tomato_app.cli.main``

保留本文件的原因：
- 兼容老用户直接执行 ``python tomato.py`` 的习惯；
- 作为示例，告诉读者推荐的入口是 ``tomato_app.cli``。
"""
from tomato_app.cli import main


if __name__ == "__main__":
    main()

