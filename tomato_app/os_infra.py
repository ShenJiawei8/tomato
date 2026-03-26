#!/usr/bin/env python3
# coding=utf-8
"""
Operating-system level helpers for the Tomato timer (macOS focused).

包含：
- ``notice``: 通过 AppleScript 发送 macOS 通知；
- ``get_idle_time``: 读取键鼠空闲时间（秒）；
- ``update_symlink``: 创建/更新符号链接；
- ``chown_to_user``: 根据 ``uid/gid`` 信息修改文件属主。

这些函数与具体操作系统强相关，因此单独放在本模块中，便于
未来扩展到其他平台或在测试中做替换。
"""

from __future__ import annotations

import os
import re
from subprocess import call
from typing import Mapping

from bin.config import use_notice


def notice(content: str, subtitle: str = "") -> None:
    """
    Show a macOS notification using AppleScript, if ``use_notice`` is enabled.

    :param content: 通知正文
    :param subtitle: 通知副标题
    """
    if not use_notice:
        return

    title = "Tomato Timer"
    cmd = '''display notification "{content}"  with title "{title}" subtitle "{subtitle}" '''.format(
        content=content,
        title=title,
        subtitle=subtitle,
    )
    call(["osascript", "-e", cmd])


def get_idle_time() -> float:
    """
    Return the current user idle time in seconds on macOS.

    通过 ``ioreg -c IOHIDSystem | grep HIDIdleTime`` 获取纳秒级空闲时间，
    再换算成秒。
    """
    t = os.popen("ioreg -c IOHIDSystem | grep HIDIdleTime").read()
    return float(re.search(r"= (\d*)", t).group(1)) / float(1000000000)


def update_symlink(src: str, dst: str) -> None:
    """
    Create or update a symbolic link ``dst`` pointing to ``src``.
    """
    if os.path.islink(dst):
        os.remove(dst)
    os.symlink(src, dst)


def chown_to_user(loc: str, user_info: Mapping[str, str]) -> int:
    """
    Change file owner to the given user info dictionary.

    :param loc: 文件路径
    :param user_info: 由 ``dscacheutil -q user`` 解析得到的字典，
                      至少需要包含 ``uid`` 和 ``gid`` 字段。
    :return: ``os.chown`` 的返回值
    """
    gid, uid = int(user_info["gid"]), int(user_info["uid"])
    return os.chown(loc, uid, gid)


