#!/usr/bin/env python3
# coding=utf-8
"""
Core domain facade for the Tomato timer application.

为了便于维护，我们将不同职责拆分到了多个模块：

- ``printer``:  ``PrintCache`` 缓冲打印工具；
- ``os_infra``: 与操作系统相关的能力（通知、空闲时间、symlink 等）；
- ``time_calendar``: 时间与日历相关工具（``Date`` / ``Colorama`` 等）；
- ``notes``: 笔记路径、每日笔记生成、归档等；
- ``timer``: 番茄钟业务核心。

本模块仅作为一个“门面”（facade）：
- 对外统一暴露这些常用类/函数；
- 保持向后兼容：老代码如果还在 ``tomato_app.core`` 上 import，
  依然可以正常工作。
"""

from tomato_app.printer import PrintCache
from tomato_app.os_infra import notice, get_idle_time, update_symlink, chown_to_user
from tomato_app.time_calendar import Colorama, Date, TABLE_WIDTH  # noqa: F401
from tomato_app.notes import (
    get_note_path,
    get_note_link_path,
    create_daily_note,
    archive_notes,
)
from tomato_app.timer import Timer

__all__ = [
    "PrintCache",
    "notice",
    "get_idle_time",
    "update_symlink",
    "chown_to_user",
    "Colorama",
    "Date",
    "TABLE_WIDTH",
    "get_note_path",
    "get_note_link_path",
    "create_daily_note",
    "archive_notes",
    "Timer",
]
