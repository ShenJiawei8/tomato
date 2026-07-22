#!/usr/bin/env python3
# coding=utf-8
"""
Timer implementation for the Tomato application.

``Timer`` 是番茄钟的核心：
- 负责读写每日 JSON 记录文件；
- 提供 start / pause / proceed / stop / check / show / records 等操作；
- 生成按小时聚合的可视化工作分布；
- 结合配置计算目标工作时长、午休比例等统计。
"""

from __future__ import annotations

import datetime
import json
import os
from typing import Any, Dict, List, Tuple

from bin.config import (
    auto_cut_cross_day,
    auto_cut_cross_day_interval_hours,
    daily_work_time_records_dir,
    note_archive_count,
    note_archive_path,
    work_time_target_hours_one_day,
    pay_time_target_hours_one_day,
)

from tomato_app.notes import create_daily_note, get_note_path, archive_notes
from tomato_app.os_infra import update_symlink, notice
from tomato_app.time_calendar import Colorama, Date, TABLE_WIDTH, target_nap_rate  # type: ignore[attr-defined]


class Timer:
    """
    Main work session recorder.

    记录的数据结构（JSON 文件）类似于::

        [
            ["2024-01-01 09:00:00", "2024-01-01 09:25:00"],
            ["2024-01-01 09:35:00", "2024-01-01 10:00:00"],
            ["2024-01-01 10:10:00"]  # 只有开始时间，表示正在进行中的工作段
        ]

    每个子列表代表一段工作区间：
    - 长度为 1: 仅有开始时间，尚未结束；
    - 长度为 2: ``[start, end]``。
    """

    # 运行时填充的“类属性”（相当于单例状态）
    record_path: str = ""
    last_files: List[str] = []
    today_file_name: str = ""
    last_file_name: str = ""
    today_symlink: str = ""
    today: str = ""
    last_day: str = ""
    tmp_detail_data: str = ""
    printer: Any = None

    @classmethod
    def init(cls, printer=None) -> None:
        """
        Initialize Timer's global state.

        - 计算记录目录、今天文件名、最近一次工作日文件等信息；
        - 创建 ``bin/today`` 的 symlink 指向最新的记录文件；
        - 自动生成最新日期对应的笔记文件；
        - 根据配置归档较早的笔记。
        """
        (
            record_path,
            last_files,
            today_file_name,
            last_file_name,
            today_symlink,
            today,
            last_day,
            tmp_detail_data,
        ) = cls.get_file_name()
        cls.record_path = record_path
        cls.last_files = last_files
        cls.today_file_name = today_file_name
        cls.last_file_name = last_file_name
        cls.today_symlink = today_symlink
        cls.today = today
        cls.last_day = last_day
        cls.tmp_detail_data = tmp_detail_data
        if printer is not None:
            cls.printer = printer
        update_symlink(cls.last_file_name, cls.today_symlink)
        create_daily_note(cls.last_file_name.split("/")[-1])
        archive_notes(save_count=note_archive_count, archive_path=note_archive_path)

    @classmethod
    def get_file_name(cls) -> Tuple[str, List[str], str, str, str, str, str, str]:
        """
        Compute key paths and filenames for today's and the latest work record.

        last_day: “最近” 一天的工作。
        - 如果最近一次记录文件的最后一段仍在进行中，则 last_day 为该日期；
        - 否则 last_day 为今天。
        """
        # Keep old behavior: symlink lives in <repo>/bin/today, not tomato_app/bin/today.
        path_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        path = daily_work_time_records_dir
        tmp_detail_data = os.path.join(path_root, "bin/tmp/detail_data")
        today_file_name = os.path.join(path, Date.date())
        today_symlink = os.path.join(path_root, "bin/today")
        today = Date.date()
        last_file_name = today_file_name
        last_day = today
        last_files = os.listdir(path)
        last_files.sort()
        if len(last_files) >= 1:
            _last_file_name = os.path.join(path, last_files[-1])
            _last_day = last_files[-1]

            with open(_last_file_name, encoding="utf-8") as fin:
                items = json.loads(fin.read())

            if len(items[-1]) == 1:
                last_file_name = _last_file_name
                last_day = _last_day

        return path, last_files, today_file_name, last_file_name, today_symlink, today, last_day, tmp_detail_data

    @classmethod
    def start(cls) -> None:
        """Start today's work if not already started."""
        if not os.path.isfile(cls.last_file_name):
            with open(cls.last_file_name, "w", encoding="utf-8") as fout:
                item = json.dumps([[Date.now()]], indent=4)
                fout.write(item)
            update_symlink(cls.last_file_name, cls.today_symlink)
            msg = "{today}'s work started...".format(today=cls.today)
        else:
            msg = "{today}'s work is already started.".format(today=cls.today)
        cls.printer.add(msg)
        cls.printer.print()

    @classmethod
    def is_paused(cls) -> bool:
        """
        Return True if the current day is considered "paused".

        规则：
        - 当天没有记录文件：视为“未开始”，这里返回 True（相当于暂停状态）；
        - 最近一条记录为 ``[start]``：正在工作，返回 False；
        - 最近一条记录为 ``[start, end]``：已暂停，返回 True。
        """
        if not os.path.isfile(cls.last_file_name):
            # work is not started.
            return True
        with open(cls.last_file_name, encoding="utf-8") as fin:
            items = json.loads(fin.read())
            return False if len(items[-1]) == 1 else True

    @classmethod
    def get_paused_time(cls) -> int | None:
        """
        If currently paused, return how long it has been paused (seconds).
        """
        if not os.path.isfile(cls.last_file_name):
            # work is not started.
            return None

        with open(cls.last_file_name, encoding="utf-8") as fin:
            items = json.loads(fin.read())
            if len(items[-1]) == 2:
                return Date.delta(items[-1][1], Date.now())
            else:
                return None

    @classmethod
    def _append_pause_timestamp(cls, delta: datetime.timedelta | None = None) -> bool:
        """
        Append pause timestamp to the latest open interval, if any.

        :return: True if a pause timestamp was appended, False otherwise.
        """
        with open(cls.last_file_name, encoding="utf-8") as fin:
            items = json.loads(fin.read())

        got_pauser_point = False

        for i in range(len(items)):
            index = len(items) - 1 - i
            if len(items[index]) != 2:
                got_pauser_point = True
                items[index].append(Date.now(delta))
                break

        if got_pauser_point:
            with open(cls.last_file_name, "w", encoding="utf-8") as fout:
                fout.write(json.dumps(items, indent=4))

        return got_pauser_point

    @classmethod
    def pause(cls, delta: datetime.timedelta | None = None) -> None:
        """
        Pause current work session by closing the latest open interval.
        """
        got_pauser_point = cls._append_pause_timestamp(delta)

        if got_pauser_point:
            msg = "{last_day}'s work paused... ".format(last_day=cls.last_day)
            notice(msg, "Action: Pause work")
            cls.printer.add(msg)
        else:
            cls.printer.add("Already paused")

        cls.printer.print()

    @classmethod
    def auto_cut_cross_day(cls) -> None:
        """
        Automatically cut into a new day if idle for long after midnight.
        """
        if auto_cut_cross_day is True:
            from tomato_app.os_infra import get_idle_time

            (
                record_path,
                last_files,
                today_file_name,
                last_file_name,
                today_symlink,
                today,
                last_day,
                tmp_detail_data,
            ) = cls.get_file_name()
            if not os.path.isfile(today_file_name) and get_idle_time() > auto_cut_cross_day_interval_hours * 3600:
                cls.init(cls.printer)
                cls.start()

    @classmethod
    def proceed(cls) -> None:
        """
        Resume work by starting a new interval from now.
        """
        cls.auto_cut_cross_day()

        if not cls.is_paused():
            msg = "Already in working status.".format(last_day=cls.last_day)
            notice(msg, "Action: Proceed work")
            cls.printer.add(msg)
            return

        with open(cls.last_file_name, encoding="utf-8") as fin:
            items = json.loads(fin.read())

        with open(cls.last_file_name, "w", encoding="utf-8") as fout:
            items.append([Date.now()])
            fout.write(json.dumps(items, indent=4))
            msg = "proceed {last_day}'s work ...".format(last_day=cls.last_day)
            notice(msg, "Action: Proceed work")
            cls.printer.add(msg)

        cls.printer.print()

    @classmethod
    def stop(cls) -> None:
        """
        Stop the whole day's work and print summary.
        """
        Timer.pause()

        work_time = 0

        with open(cls.last_file_name, encoding="utf-8") as fin:
            items = json.loads(fin.read())
            for item in items:
                if len(item) == 2:
                    work_time += Date.delta(item[0], item[1])

        cls.printer.add("{last_day}'s work stoped".format(last_day=cls.last_day))
        cls.printer.add(Date.format_delta(work_time))
        cls.printer.print()

    @classmethod
    def check(cls, specific_date: str) -> None:
        """
        Check current day's status (working / paused) and show current tomato.
        """
        specific_path = (
            cls.last_file_name
            if specific_date == Date.today()
            else os.path.join(cls.record_path, specific_date)
        )
        with open(specific_path, encoding="utf-8") as fin:
            cls.printer.add(*Colorama.color_title("Tomato", "yellow"))
            items = json.loads(fin.read())

            work_time = 0

            for item in items:
                if len(item) == 2:
                    work_time += Date.delta(item[0], item[1])

            last_item = items[len(items) - 1]
            if len(last_item) == 1:
                tomato = Date.delta(last_item[0], Date.now())
                work_time += tomato
                msg = "*" + " Now Status: " + "Working "
                cls.printer.add(msg)
                cls.printer.add(
                    "*",
                    "Current:",
                    Colorama.print(
                        Date.format_delta(tomato, with_check=True, blink=True, nap_notice=True), "yellow"
                    ),
                )
            else:
                msg = "*" + " Work Status: " + "paused"
                cls.printer.add(msg)

            notice(msg, "Action: Check work status")
        cls.printer.print()

    @classmethod
    def records(cls, count: int = 7) -> None:
        """Print how many days have records and list the latest ``count`` days."""
        cls.printer.add(
            """Already record {days} days' work, recent {count} days are below:""".format(
                days=Colorama.print(str(len(cls.last_files)), "red"), count=count
            )
        )
        cls.printer.add()
        recent_days = cls.last_files[-count:]
        recent_days.reverse()
        for d in recent_days:
            cls.printer.add(d)
        cls.printer.print()

    @classmethod
    def show(cls, specific_date: str | None = None, verbose: bool = False, output: Any = None) -> None:
        """
        Show detailed history for a specific date.
        """
        specific_path = (
            cls.last_file_name
            if specific_date == Date.today()
            else os.path.join(cls.record_path, specific_date)
        )
        _date = specific_path.split("/")[-1]
        if not os.path.isfile(specific_path):
            cls.printer.add(Colorama.print("No record.", "red"))
            cls.printer.print()
            return
        cls.printer.add(
            *Colorama.color_title(
                "Tomato History : {_date}, Weekday {weekday}".format(
                    _date=_date, weekday=Date.weekday(_date)
                ),
                "yellow",
                TABLE_WIDTH,
            )
        )
        cls.printer.add()
        cls.printer.add("   Num   |  Work Time Interval |        Tomato         |  Nap (5min)")
        cls.printer.add("-" * 70)
        previous_item = None
        with open(specific_path, encoding="utf-8") as fin:
            items = json.loads(fin.read())
            hl_sum: Dict[str, Dict[str, Any]] = dict()
            work_time = 0
            for item in items:
                if previous_item and (items.index(item) > len(items) - 9 or verbose):
                    cls.printer.add(
                        Date.format_delta(
                            Date.delta(previous_item[1], item[0]), tomato_mode=False, with_check=False
                        )
                    )

                previous_item = item

                if len(item) == 2:
                    if item[1] <= item[0]:
                        previous_item = None
                        continue
                    if items.index(item) > len(items) - 10 or verbose:
                        cls.printer.add(
                            "*  %03d:    " % items.index(item),
                            item[0][10:16],
                            " ~",
                            item[1][10:16],
                            "   ",
                            Date.format_delta(Date.delta(item[0], item[1]), with_check=True),
                            "    ",
                            endl=False,
                        )
                    for seg, t in Date.timing_seg_distribute(item).items():
                        if seg not in hl_sum:
                            hl_sum[seg] = t
                        else:
                            hl_sum[seg]["sum"] += t["sum"]
                            hl_sum[seg]["map"] = Date.merge_visualize(
                                hl_sum[seg]["map"], t["map"]
                            )
                    work_time += Date.delta(item[0], item[1])
                elif items.index(item) == len(items) - 1:
                    for seg, t in Date.timing_seg_distribute([item[0], Date.now()]).items():
                        if seg not in hl_sum:
                            hl_sum[seg] = t
                        else:
                            hl_sum[seg]["sum"] += t["sum"]
                            hl_sum[seg]["map"] = Date.merge_visualize(
                                hl_sum[seg]["map"], t["map"]
                            )
                    work_time += Date.delta(item[0], Date.now())

            last_item = items[-1]
            if len(last_item) == 1:
                end_time = Date.now()
                cls.printer.add(
                    "*  %03d:    " % (len(items) - 1),
                    last_item[0][10:16],
                    " ~",
                    "  ... ",
                    "   ",
                    Date.format_delta(Date.delta(last_item[0], Date.now()), with_check=True),
                    "   ",
                    endl=False,
                )
            else:
                end_time = last_item[1]

            cls.printer.add("\n")
            cls.printer.add(*Colorama.color_title("Hour History (unit: Minute)", "yellow", TABLE_WIDTH))
            cls.printer.add()
            cls.printer.add("   00        10        20        30        40        50        60")
            hl_sum_visual = Date.visualize_map(hl_sum)
            for h in Date.hour_list(items[0][0], end_time):
                cls.printer.add(h[9:] + ": ", endl=False)
                if h in hl_sum_visual:
                    cls.printer.add(
                        hl_sum_visual[h],
                        "%.2f" % round(float(hl_sum[h]["sum"]) / 60, 2),
                    )
                else:
                    cls.printer.add(Colorama.print("░", "red") * 60, "00.00")

            cls.printer.print()

            start_time = items[0][0]
            wt = Date.delta(start_time, end_time)
            sit_time = Date.delta(start_time, Date.now())
            target_time = Date.now(
                datetime.timedelta(seconds=work_time_target_hours_one_day * 3600 - work_time)
            )
            target_pay_time = Date.now(
                datetime.timedelta(seconds=pay_time_target_hours_one_day * 3600 - sit_time)
            )
            cls.printer.add(*Colorama.color_title("Summary", "yellow", TABLE_WIDTH))
            cls.printer.add()
            target_finish_rate = round(
                float(work_time) / float(work_time_target_hours_one_day * 3600) * 100
            )
            target_finish_rate_str = Colorama.print(
                str(target_finish_rate) + " %",
                "blue" if target_finish_rate > 90 else "yellow",
                blink=False,
            )
            cls.printer.add(
                "*",
                "Start Time: ",
                start_time[:16],
                "     * Target Finish Rate: ",
                target_finish_rate_str,
            )
            if specific_date == Date.today():
                cls.printer.add(
                    "* Target Time:",
                    target_time[:16],
                    "✅  " if target_time <= Date.now() else "    ",
                    "* Work Rate Target:   ",
                    Colorama.print(
                        str(
                            round(
                                float(work_time_target_hours_one_day * 3600)
                                / float(work_time_target_hours_one_day * 3600 + wt - work_time)
                                * 100
                            )
                        )
                        + " %",
                        "blue",
                    ),
                )
            else:
                cls.printer.add(
                    "*",
                    "Stop Time:  ",
                    last_item[1][:16] if len(last_item) > 1 else last_item[0][:16],
                )
            nap_rate = round(float(wt - work_time) / float(wt) * 100)
            nap_rate_str = str(nap_rate) + " %"
            cls.printer.add(
                "*",
                "All Time:   ",
                Date.format_delta(wt, with_check=False, blink=False, tomato_mode=True),
                "* Work Rate:",
                Colorama.print(str(round(float(work_time) / float(wt) * 100)) + " %", "blue"),
                "; Nap Rate:",
                Colorama.print(nap_rate_str, "blue")
                if nap_rate <= target_nap_rate
                else Colorama.print(nap_rate_str, "red", blink=False),
            )

            cls.printer.add(
                "*",
                "Work Time:  ",
                Date.format_delta(work_time, with_check=False, blink=False),
                "* CountDown:",
                Date.format_delta(Date.delta(Date.now(), target_time)),
            )
            cls.printer.add(
                "*",
                "Nap Time:   ",
                Date.format_delta((wt - work_time), with_check=False, blink=False, tomato_mode=True),
                "*",
                "Pay Time: ",
                target_pay_time[:16],
                "✅" if target_pay_time <= end_time else "    ",
            )
            cls.printer.add()
            note_path = get_note_path(_date)
            note_info = note_path if os.path.exists(note_path) else "note file is not exist."
            cls.printer.add("* Note: {note_path}".format(note_path=note_info))
            cls.printer.add()
            DATE = datetime.datetime.strptime(_date, "%Y-%m-%d")
            cls.printer.add(
                *Colorama.color_title(
                    "Calendar - {} / Q{}".format(_date, Date.get_quarter(DATE.month)),
                    "yellow",
                    TABLE_WIDTH,
                )
            )
            cls.printer.add()
            cls.printer.add(
                Colorama._cal_month_expand(
                    DATE.year, DATE.month, DATE.day, indent="  ", quarter=True
                )
            )
            cls.printer.add(*Colorama.color_title("NowTime: " + Date.now(), "yellow", TABLE_WIDTH))
            cls.printer.print()

    @classmethod
    def edit(cls, specific_date: str | None = None) -> None:
        """
        Open the raw record file in ``vi`` for manual correction.
        """
        _specific_date = (
            cls.last_file_name
            if specific_date == Date.today()
            else os.path.join(cls.record_path, specific_date)
        )
        os.system("vi {}".format(_specific_date))

    @classmethod
    def edit_note(cls, specific_date: str | None = None) -> None:
        """
        Open the daily note markdown file in ``vi``.
        """
        note_path = get_note_path(specific_date)
        os.system("vi {}".format(note_path))

    @classmethod
    def vim_note(cls, specific_date: str | None = None) -> None:
        """
        Open the daily note markdown file in ``vim``.
        """
        note_path = get_note_path(specific_date)
        os.system("vim {}".format(note_path))


