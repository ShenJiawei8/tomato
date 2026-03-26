#!/usr/bin/env python3
# coding=utf-8
"""
Time / calendar utilities for the Tomato timer.

本模块主要提供两大类能力：

- ``Colorama``: 负责带颜色的终端输出以及日历渲染；
- ``Date``: 负责各种时间差计算、番茄时长格式化、可视化数据处理等。

二者之间存在相互调用（例如 ``Colorama`` 在渲染日历时需要
``Date.get_quarter``，而 ``Date.cal_date_interval`` 又会调用
``Colorama.print`` 做高亮），因此放在同一文件中以避免循环依赖。
"""

from __future__ import annotations

import calendar
import datetime
import math
import re
from typing import Dict, List, Tuple

from icalendar import Calendar

from bin.config import tomato_min, nap_seconds, target_nap_rate, work_time_target_hours_one_day

TABLE_WIDTH = 70


class Colorama(object):
    """
    ANSI color / calendar rendering helpers.
    """

    with_color = False

    @classmethod
    def _double_underline(cls, msg: str) -> str:
        return "\033[21m%s\033[0m" % (msg)

    @classmethod
    def _delete_line(cls, msg: str) -> str:
        return "\033[9m%s\033[0m" % (msg)

    @classmethod
    def _red_block(cls, msg: str) -> str:
        return "\033[45m%s\033[0m" % (msg)

    @classmethod
    def _pink_block(cls, msg: str) -> str:
        return "\033[105m%s\033[0m" % (msg)

    @classmethod
    def _deep_red_block(cls, msg: str) -> str:
        return "\033[41m%s\033[0m" % (msg)

    @classmethod
    def _blue_block(cls, msg: str) -> str:
        return "\033[44m%s\033[0m" % (msg)

    @classmethod
    def _red(cls, msg: str) -> str:
        return "\033[35m%s\033[0m" % (msg)

    @classmethod
    def _deep_red(cls, msg: str) -> str:
        return "\033[31m%s\033[0m" % (msg)

    @classmethod
    def _blue(cls, msg: str) -> str:
        return "\033[36m%s\033[0m" % (msg)

    @classmethod
    def _yellow(cls, msg: str) -> str:
        return "\033[33m%s\033[0m" % (msg)

    @classmethod
    def _blink(cls, msg: str) -> str:
        return "\033[5m%s\033[0m" % (msg)

    @classmethod
    def print(cls, msg: str, color: str = None, blink: bool = False, block: bool = False) -> str:
        """
        Wrap ``msg`` with ANSI color codes if ``with_color`` is enabled.
        """
        if not Colorama.with_color:
            return msg
        if color == "deep-red":
            if block:
                msg = cls._deep_red_block(msg)
            else:
                msg = cls._deep_red(msg)
        if color == "red":
            if block:
                msg = cls._red_block(msg)
            else:
                msg = cls._red(msg)
        if color == "blue":
            if block:
                msg = cls._blue_block(msg)
            else:
                msg = cls._blue(msg)
        if color == "yellow":
            msg = cls._yellow(msg)
        if color == "pink":
            msg = cls._pink_block(msg)
        if blink:
            return cls._blink(msg)
        return msg

    @classmethod
    def color_title(
        cls, msg: str, color: str, length: int = 36, delimiter: str = "+", delimiter_color: str = None
    ) -> Tuple[str, str, str]:
        """
        Generate a colored title with symmetric delimiters on both sides.
        """
        length = float(length)
        l = float(len(msg))
        side = (length - l) / 2
        left = math.floor(side)
        right = math.ceil(side)
        return (
            cls.print(delimiter * left, delimiter_color),
            cls.print(msg, color),
            cls.print(delimiter * right, delimiter_color),
        )

    @classmethod
    def _cal(cls, year: int, month: int, day: int, indent: str = "", expand: int = 0, for_note: bool = False, highlight: bool = True) -> str:
        """
        Render a single month calendar, optionally with colors and highlighting.
        """
        _with_color = False if for_note is True else Colorama.with_color
        s = calendar.month(year, month)
        s = re.sub(r"\b", " " * expand, s)
        pre, suf = s.split("Su")
        date = re.sub(r"^0", " ", str(day))
        date = date if day >= 10 else " %s" % date
        if _with_color is False:
            if highlight:
                suf = re.sub(date, "==", suf, count=1)
            cal = pre + "Su" + suf
        else:
            date_lines = suf.split("\n")
            suf_lines: List[str] = []
            for line in date_lines:
                if len(line) > 0:
                    weekend = re.split(" +", line[15:].strip())
                    if len(weekend) == 1 and len(line.strip()) >= 4:
                        sat = weekend[0]
                        sun = ""
                    elif len(weekend) == 1 and len(line.strip()) < 4:
                        sun = weekend[0]
                        sat = ""
                    else:
                        sat, sun = weekend[0], weekend[1]

                    sat = sat if len(sat) > 0 and int(sat) >= 10 else " %s" % sat if len(sat) > 0 else "  "
                    sun = sun if len(sun) > 0 and int(sun) >= 10 else " %s" % sun if len(sun) > 0 else "  "
                    line = (
                        line
                        if len(line) < 17
                        else line[:15] + cls.print(sat, "yellow") + " " + cls.print(sun, "yellow")
                    )
                suf_lines.append(line)
            suf = "\n".join(suf_lines)
            if highlight:
                suf = re.sub(date, cls.print(date, "red", block=True), suf, count=1)
        _with_color_bak = Colorama.with_color
        Colorama.with_color = _with_color
        cal = (
            cls.print(
                "".join(
                    list(
                        cls.color_title(
                            pre.split("\n")[0].strip(), color="yellow", length=20, delimiter="_"
                        )
                    )
                )
            )
            + "\n"
            + cls.print(pre.split("\n")[1], "blue")
            + cls.print("Su", "blue")
            + suf
        )
        cal = re.sub("^", indent, cal)
        cal = re.sub("\n", "\n" + indent, cal)
        Colorama.with_color = _with_color_bak
        return cal

    @classmethod
    def _cal_month_expand(
        cls,
        year: int,
        month: int,
        day: int,
        indent: str = "",
        expand: int = 0,
        quarter: bool = False,
        vertical: bool = False,
        for_note: bool = False,
        highlight: bool = True,
    ) -> str:
        """
        Render a 3‑month calendar block (quarter) or (prev, curr, next) view.
        """

        def _get_quarter_months(month: int) -> Tuple[int, int, int]:
            month = int(month)
            quarter = Date.get_quarter(month)
            quarter_first_month = (quarter - 1) * 3 + 1
            return int(quarter_first_month), int(quarter_first_month + 1), int(quarter_first_month + 2)

        if quarter:
            month_0, month_1, month_2 = _get_quarter_months(month)
            year_0 = year_1 = year_2 = year
        else:
            date_month_first_day_obj = datetime.datetime.strptime(
                "{year}-{month}-01".format(year=year, month=month), "%Y-%m-%d"
            )
            month_obj_0 = date_month_first_day_obj + datetime.timedelta(days=-1)
            month_obj_2 = date_month_first_day_obj + datetime.timedelta(days=32)
            month_0 = month_obj_0.month
            month_2 = month_obj_2.month
            year_0 = month_obj_0.year
            year_2 = month_obj_2.year

            year_1 = year
            month_1 = month

        cal_0 = cls._cal(
            year_0,
            month_0,
            1 if month != month_0 else day,
            indent="",
            expand=expand,
            for_note=for_note,
            highlight=False if month != month_0 or highlight is False else True,
        )
        cal_1 = cls._cal(
            year_1,
            month_1,
            1 if month != month_1 else day,
            indent="",
            expand=expand,
            for_note=for_note,
            highlight=False if month != month_1 or highlight is False else True,
        )
        cal_2 = cls._cal(
            year_2,
            month_2,
            1 if month != month_2 else day,
            indent="",
            expand=expand,
            for_note=for_note,
            highlight=False if month != month_2 or highlight is False else True,
        )

        cal_expand_lines: List[str] = []
        if vertical:
            cal_expand_lines = cal_0.split("\n") + cal_1.split("\n") + cal_2.split("\n")
        else:
            for lines in zip(cal_0.split("\n"), cal_1.split("\n"), cal_2.split("\n")):
                _lines: List[str] = []
                for line in lines:
                    if len(line) < 20:
                        _line = line + (20 - len(line)) * " "
                    else:
                        _line = line
                    _lines.append(_line)
                cal_expand_lines.append(indent + "   ".join(_lines))
        _cal_expand = "\n".join(cal_expand_lines)
        return _cal_expand

    @classmethod
    def _cal_year_expand(cls, year: int, month: int, day: int, indent: str = "", expand: int = 0, for_note: bool = False) -> str:
        """
        Render four quarter calendars for the given year.
        """

        def _get_year_quarters(month: int):
            quarters_month_list = [1, 4, 7, 10]
            month = int(month)
            quarter = Date.get_quarter(month)
            quarter_first_month = (quarter - 1) * 3 + 1
            return [
                (year, m, 1, False) if m != quarter_first_month else (year, month, day, True)
                for m in quarters_month_list
            ]

        year_quarters = _get_year_quarters(month)
        return "\n".join(
            [
                cls._cal_month_expand(
                    q[0],
                    q[1],
                    q[2],
                    indent=indent,
                    expand=expand,
                    quarter=True,
                    vertical=False,
                    for_note=for_note,
                    highlight=q[3],
                )
                for q in year_quarters
            ]
        )

    @classmethod
    def read_calendar(cls):
        """
        Read Chinese mainland public holidays from ``cn_zh.ics``.
        """
        holidays = []
        work_days = []
        with open("cn_zh.ics", "rb") as fin:
            cal = Calendar.from_ical(fin.read())

            for component in cal.walk():
                if component.name == "VEVENT":
                    summary = component.get("SUMMARY")
                    start = component.get("DTSTART").dt
                    end = component.get("DTEND").dt

                    if "班" in summary:
                        work_days.append([start, end])

                    if "休" not in summary:
                        holidays.append([start, end])

                    continue

        return holidays, work_days

    @classmethod
    def is_holiday(cls, date, holidays=None, work_days=None) -> bool:
        if not holidays or not work_days:
            holidays, work_days = cls.read_calendar()
        week_day = Date.weekday(date)
        if week_day <= 5:
            return any([start <= date < end for start, end in holidays])
        else:
            return not any([start <= date < end for start, end in work_days])

    @classmethod
    def is_extra_work_day(cls, date, work_days=None) -> bool:
        if not work_days:
            _, work_days = cls.read_calendar()
        week_day = Date.weekday(date)
        if week_day > 5:
            return any([start <= date < end for start, end in work_days])
        return False


class Date:
    """
    Various date/time utilities used throughout the app.
    """

    @classmethod
    def date(cls) -> str:
        return datetime.datetime.now().strftime("%Y-%m-%d")

    @classmethod
    def now(cls, delta: datetime.timedelta | None = None) -> str:
        now = datetime.datetime.now()
        now = now + delta if delta is not None else now
        return now.strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def today(cls, delta: datetime.timedelta | None = None) -> str:
        now = datetime.datetime.now()
        now = now + delta if delta is not None else now
        return now.strftime("%Y-%m-%d")

    @classmethod
    def delta(cls, d1: str, d2: str, seconds: bool = True) -> int:
        if seconds:
            d1_dt = datetime.datetime.strptime(d1, "%Y-%m-%d %H:%M:%S")
            d2_dt = datetime.datetime.strptime(d2, "%Y-%m-%d %H:%M:%S")
        else:
            d1_dt = datetime.datetime.strptime(d1, "%Y-%m-%d")
            d2_dt = datetime.datetime.strptime(d2, "%Y-%m-%d")
        _seconds = (d2_dt - d1_dt).seconds
        _days = (d2_dt - d1_dt).days
        return _seconds + _days * 86400 if seconds else _days

    @classmethod
    def diff_month(cls, d1: datetime.datetime, d2: datetime.datetime) -> int:
        return (d2.year - d1.year) * 12 + d2.month - d1.month

    @classmethod
    def diff_datetime(cls, d1: datetime.datetime, d2: datetime.datetime) -> Tuple[int, int, int]:
        reverse = False
        if d1 > d2:
            reverse = True
            d1, d2 = d2, d1

        diff_year = (
            (d2.year - d1.year)
            if (d2.month > d1.month) or (d2.month == d1.month and d2.day >= d1.day)
            else (d2.year - d1.year - 1)
        )

        diff_month = (
            (d2.month - d1.month)
            if (d2.month > d1.month) or (d2.month == d1.month and d2.day >= d1.day)
            else (d2.month - d1.month + 12)
        )

        if d2.day >= d1.day:
            diff_day = d2.day - d1.day
        else:
            if diff_month > 0:
                diff_month = diff_month - 1
            else:
                diff_year = diff_year - 1
                diff_month = 12

            first_day_d1 = datetime.datetime.strptime(
                "{year}-{month}-01".format(year=d1.year, month=d1.month), "%Y-%m-%d"
            )
            d1_next_month = first_day_d1 + datetime.timedelta(days=32)

            d1_next_month_first_day = datetime.datetime.strptime(
                "{year}-{month}-01".format(year=d1_next_month.year, month=d1_next_month.month), "%Y-%m-%d"
            )

            diff_day = (d1_next_month_first_day - d1).days - 1 + d2.day
        return (diff_year, diff_month, diff_day) if not reverse else (-diff_year, -diff_month, -diff_day)

    @classmethod
    def _format_delta(cls, delta: int) -> Tuple[str, str, str, str]:
        hour = "%02d" % int(delta / 3600)
        minute = "%02d" % (int((delta % 3600) / 60) if delta >= 0 else int((delta % 3600 - 3600) / 60))
        second = "%02d" % (int(delta % 60) if delta >= 0 else int(delta % 60 - 60))
        tomato = "%.2f" % round(float(delta) / float(tomato_min * 60), 2)
        tomato = tomato.zfill(5)
        return hour, minute, second, tomato

    @classmethod
    def format_delta(cls, delta: int, tomato_mode: bool = True, with_check: bool = False, blink: bool = False, nap_notice: bool = False) -> str:
        """
        Format a time difference (seconds) into a human friendly string.
        """
        hour, minute, second, tomato = cls._format_delta(delta)
        if blink:
            tomato_icon = Colorama.print("x 🍅", blink=True)
            check_icon = Colorama.print("✅ ", blink=True)
        else:
            tomato_icon = "x 🍅"
            check_icon = "✅ "
        if tomato_mode:
            return "{hour}:{minute}  =>  {tomato} {finish}{nap_notice}".format(
                hour=hour,
                minute=minute,
                tomato=tomato,
                finish=tomato_icon if float(tomato) >= 1 and with_check else "    ",
                nap_notice=Colorama.print(
                    "\n [ You need a nap now to relax your eyes ~ ]", "yellow", blink=False
                )
                if nap_notice and float(tomato) >= 1
                else "",
            )
        else:
            return "{hour}:{minute} {enough_break}{nap_notice}".format(
                hour=hour,
                minute=minute,
                enough_break=check_icon if delta > nap_seconds and with_check else "    ",
                nap_notice=Colorama.print(
                    "\n [You have got enough rest, back to work now ~ ]", "yellow", blink=False
                )
                if nap_notice is True
                else "",
            )

    @classmethod
    def weekday(cls, d: str) -> int:
        return datetime.datetime.strptime(d, "%Y-%m-%d").weekday() + 1

    @classmethod
    def day_hour(cls, d: str) -> str:
        return datetime.datetime.strptime(d, "%Y-%m-%d %H:%M:%S").strftime("%Y%m%d/%H")

    @classmethod
    def hour_list(cls, d_start: str, d_end: str) -> List[str]:
        hl: List[str] = []
        dh_end = cls.day_hour(d_end)
        while True:
            dh = cls.day_hour(d_start)
            hl.append(dh)
            if dh == dh_end:
                break
            _d_start = datetime.datetime.strptime(d_start, "%Y-%m-%d %H:%M:%S") + datetime.timedelta(hours=1)
            d_start = _d_start.strftime("%Y-%m-%d %H:%M:%S")
        return hl

    @classmethod
    def merge_visualize(cls, map_start: List[int], map_end: List[int]) -> List[int]:
        hour_map = [int(i) for i in ("0" * 60)]
        for i in range(60):
            hour_map[i] = map_start[i] | map_end[i]
        return hour_map

    @classmethod
    def timing_seg_distribute(cls, timing_seg: List[str]) -> Dict[str, Dict[str, object]]:
        def _visualize_hour(start: datetime.datetime, end: datetime.datetime) -> List[int]:
            hour_map = [int(i) for i in ("0" * 60)]
            start_min = int(start.strftime("%M"))
            start_hour = int(start.strftime("%H"))
            end_min = int(end.strftime("%M"))
            end_hour = int(end.strftime("%H"))
            end_second = int(end.strftime("%S"))
            if end_min == 0 and start_hour != end_hour:  # cross hour, endtime is 59:59
                end_min = 59
                end_second = 59
            for i in range(start_min, end_min + 1 if end_second > 30 else end_min):
                hour_map[i] = 1
            return hour_map

        st_obj = datetime.datetime.strptime(timing_seg[0], "%Y-%m-%d %H:%M:%S")
        et_obj = datetime.datetime.strptime(timing_seg[1], "%Y-%m-%d %H:%M:%S")
        sh = cls.day_hour(timing_seg[0])
        eh = cls.day_hour(timing_seg[1])
        hl = cls.hour_list(timing_seg[0], timing_seg[1])
        if len(hl) == 1:
            return {
                sh: {
                    "sum": cls.delta(timing_seg[0], timing_seg[1]),
                    "map": _visualize_hour(st_obj, et_obj),
                }
            }
        else:
            result: Dict[str, Dict[str, object]] = dict()
            first_inter = datetime.datetime.strptime(hl[1], "%Y%m%d/%H")
            first_sum = (first_inter - datetime.datetime.strptime(timing_seg[0], "%Y-%m-%d %H:%M:%S")).seconds
            first_map = _visualize_hour(st_obj, datetime.datetime.strptime(hl[1], "%Y%m%d/%H"))
            last_inter = datetime.datetime.strptime(hl[-1], "%Y%m%d/%H")
            last_sum = (datetime.datetime.strptime(timing_seg[1], "%Y-%m-%d %H:%M:%S") - last_inter).seconds
            last_map = _visualize_hour(datetime.datetime.strptime(hl[-1], "%Y%m%d/%H"), et_obj)
            for h in hl:
                if h == sh:
                    result[h] = {"sum": first_sum, "map": first_map}
                elif h == eh:
                    result[h] = {"sum": last_sum, "map": last_map}
                else:
                    result[h] = {"sum": 3600, "map": [int(i) for i in ("1" * 60)]}
            return result

    @classmethod
    def visualize_map(cls, map_dict: Dict[str, Dict[str, object]]) -> Dict[str, str]:
        def _visualize(_map: List[int], _sum: int) -> str:
            _sum = int(float(_sum) / float(60))
            _count = 0
            m = ""
            for i in _map:
                if _count <= int(_sum):
                    m += Colorama.print("▓", "blue") if i else Colorama.print("▓", "red")
                else:
                    m += Colorama.print("░", "blue") if i else Colorama.print("░", "red")
                _count += 1
            return m

        def _cut_last_map(_map: List[int]) -> List[int]:
            _new_map: List[int] = []
            _got_cut = False
            for i in range(len(_map)):
                _minute_state = _map[len(_map) - 1 - i]
                if _minute_state == 0 and not _got_cut:
                    continue
                else:
                    _got_cut = True
                _new_map.append(_minute_state)
            _new_map = list(reversed(_new_map))
            return _new_map

        result: Dict[str, str] = dict()
        count = 0
        for h, d in map_dict.items():
            count += 1
            if count == len(map_dict):  # last item
                result[h] = _visualize(_cut_last_map(d["map"]), d["sum"])  # type: ignore[index]
            else:
                result[h] = _visualize(d["map"], d["sum"])  # type: ignore[index]
        return result

    @classmethod
    def get_quarter(cls, month: int) -> int:
        return int((month + 2) / 3)

    @classmethod
    def cal_date_interval(cls, date: str, date_calculate):
        """
        High level description of the date interval between ``date``
        and another date or day offset.
        """
        if isinstance(date_calculate, int):
            _delta_days_for_calculate = int(date_calculate)
            _date_for_calculate = datetime.datetime.strptime(date, "%Y-%m-%d") + datetime.timedelta(
                days=_delta_days_for_calculate
            )
            date_calculate_for_print = Colorama.print(_date_for_calculate.strftime("%Y-%m-%d"), color="blue")
            _delta_days_for_calculate_for_print = str(_delta_days_for_calculate)
            _delta_months = Date.diff_month(
                datetime.datetime.strptime(date, "%Y-%m-%d"), _date_for_calculate
            )
            _delta_year, _delta_month, _delta_day = Date.diff_datetime(
                datetime.datetime.strptime(date, "%Y-%m-%d"), _date_for_calculate
            )

        else:
            if date_calculate is None or date_calculate == "now":
                date_calculate = Date.today()

            _delta_days = datetime.datetime.strptime(
                date_calculate, "%Y-%m-%d"
            ) - datetime.datetime.strptime(date, "%Y-%m-%d")
            _delta_days_for_calculate = _delta_days.days
            date_calculate_for_print = date_calculate
            _delta_days_for_calculate_for_print = Colorama.print(_delta_days.days, color="blue")
            _delta_months = Date.diff_month(
                datetime.datetime.strptime(date, "%Y-%m-%d"),
                datetime.datetime.strptime(date_calculate, "%Y-%m-%d"),
            )
            _delta_year, _delta_month, _delta_day = Date.diff_datetime(
                datetime.datetime.strptime(date, "%Y-%m-%d"),
                datetime.datetime.strptime(date_calculate, "%Y-%m-%d"),
            )

        _delta_years = "%.2f" % round(float(_delta_days_for_calculate) / float(365), 2)
        _delta_years = _delta_years.zfill(5)

        return "* {_delta_year} Years / {_delta_month} Months / {_delta_day} Days ({_delta_days_for_calculate_for_print} days) between {date} ~ {date_calculate_for_print}".format(
            _delta_days_for_calculate_for_print=_delta_days_for_calculate_for_print,
            _delta_year=_delta_year,
            _delta_month=_delta_month,
            _delta_day=_delta_day,
            date=date,
            date_calculate_for_print=date_calculate_for_print,
        )


