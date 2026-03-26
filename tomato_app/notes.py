#!/usr/bin/env python3
# coding=utf-8
"""
Note management for the Tomato timer.

负责：
- 计算每日工作笔记路径（真实文件和快捷链接）；
- 生成每日 Markdown 笔记（自动继承前几天的 TODO）；
- 归档较早的笔记文件并清理 symlink。
"""

from __future__ import annotations

import datetime
import os
import re
import shutil
from typing import List, Dict, Any

from bin.config import (
    daily_work_note_dir,
    copy_daily_work_note_symlink,
    user_name,
)

from utils.user_info import get_user_infos

from tomato_app.os_infra import update_symlink, chown_to_user
from tomato_app.time_calendar import Colorama, Date


def get_note_path(date: str) -> str:
    """Return the absolute path of the note file for ``date``."""
    return os.path.join(daily_work_note_dir, date + ".md")


def get_note_link_path(date: str) -> str:
    """Return the absolute path of the symlink pointing to the note file for ``date``."""
    return os.path.join(copy_daily_work_note_symlink, date + ".md")


def create_daily_note(date: str, printer=None) -> None:
    """
    Create a daily markdown note file for the given date if it does not exist.

    特性：
    - 如果近 30 天内存在更早的笔记，会自动把前一天的 TODO 区块迁移到当前笔记；
    - 在笔记头部会插入一个带高亮的日历视图；
    - 会自动设置文件属主为当前用户，并在需要时创建 symlink。
    """

    def _simplify_today_work(work_lines: List[str]) -> List[str]:
        before_block: List[str] = []
        today_block: List[str] = []
        today_line = None
        in_today_block = False
        for l in work_lines:
            if "#### TODO" in l:
                in_today_block = True
                today_line = l
                continue
            if in_today_block:
                if l.strip() == "* [ ]" or len(l.strip()) == 0:
                    continue
                else:
                    today_block.append(l)

            else:
                before_block.append(l)

        return before_block + [today_line] + today_block if len(today_block) else before_block

    note_path = get_note_path(date)
    DATE = datetime.datetime.strptime(date, "%Y-%m-%d")

    # 如果当天笔记已经存在，直接返回
    if os.path.isfile(note_path):
        if printer:
            printer.add("Note file({note_path}) is already exit, skip create.".format(note_path=note_path))
            printer.print()
        return
    else:
        # 向前最多 30 天寻找最近一份已有的 TODO 列表
        date_obj = DATE
        for _ in range(30):
            date_obj = date_obj + datetime.timedelta(days=-1)
            last_day = date_obj.strftime("%Y-%m-%d")
            last_day_note_path = get_note_path(last_day)
            if os.path.isfile(last_day_note_path):
                _last_todo_list: List[str] = []
                with open(last_day_note_path, encoding="utf-8") as fin:
                    get_record = False
                    while True:
                        line = fin.readline()
                        if "work started, have a nice day ~" in line:
                            get_record = True
                            continue
                        if not get_record:
                            if not line:
                                break
                            continue
                        if line and "#### DONE" not in line:
                            _last_todo_list.append(line)
                            continue
                        break
                _last_todo_list = _simplify_today_work(_last_todo_list)
                last_todo = "".join(_last_todo_list)
                last_todo = re.sub("#### TODO", "#### " + last_day, last_todo)
                last_todo = last_todo.rstrip()
                break
        else:
            if printer:
                printer.add("Cannot find todo of recent 30 days, init with empty todo")
                printer.print()
            last_todo = ""

    with open(note_path, "a+", encoding="utf-8") as fout:
        msg = """{cal}
### {date}'s work started, have a nice day ~
{last_todo}
#### TODO
* [ ]  

#### DONE
* [x]  

### start work record below
""".format(
            date=date,
            cal=Colorama._cal_month_expand(DATE.year, DATE.month, DATE.day, quarter=True, for_note=True),
            last_todo=last_todo,
        )
        fout.write(msg)
    user_infos = get_user_infos(user_name)
    if len(user_infos):
        chown_to_user(note_path, user_infos[0])
    if copy_daily_work_note_symlink is not None:
        symlink = get_note_link_path(date)
        update_symlink(note_path, symlink)
        if len(user_infos):
            chown_to_user(symlink, user_infos[0])


def archive_notes(save_count: int = 10, archive_path: str = "") -> List[Dict[str, Any]]:
    """
    Move old note files into an archive directory and clean up symlinks.

    :param save_count: 保留最近多少天的笔记（按日期差计算）
    :param archive_path: 归档目录路径，不传则直接返回空列表
    :return: 归档操作明细（原路径、目标路径、删除的 symlink 等）
    """
    archive_list: List[Dict[str, Any]] = []
    if not archive_path:
        return archive_list
    for f in os.listdir(daily_work_note_dir):
        f_path = os.path.join(daily_work_note_dir, f)
        f_symlink_path = os.path.join(copy_daily_work_note_symlink, f)
        if os.path.isfile(f_path) and f.endswith(".md"):
            _date = f.split(".")[0]
            if Date.delta(_date, Date.today(), seconds=False) >= save_count:
                f_archive_path = os.path.join(archive_path, f)
                shutil.move(f_path, f_archive_path)
                if os.path.islink(f_symlink_path):
                    os.remove(f_symlink_path)
                archive_list.append(
                    {
                        "mv_note_path": f_path,
                        "archive_to_path": f_archive_path,
                        "rm_symlink": f_symlink_path,
                    }
                )
    return archive_list


