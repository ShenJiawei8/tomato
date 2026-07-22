# coding=utf-8
"""
Command line interface for the Tomato timer.

This module is intentionally thin:
- It focuses on parsing arguments, validating user input,
  and orchestrating high level actions.
- All core business logic (time calculations, note creation,
  statistics rendering, etc.) lives in ``tomato_app.core``.

设计原则：
- CLI 只做“翻译”：把命令行参数翻译成对核心类/函数的调用；
- 所有可以复用的逻辑（计时、日历、笔记等）放在 ``core.py``，
  方便之后写测试、做 GUI 或提供二次封装。
"""

import argparse
import datetime
import os
import time

from tomato_app.core import (
    PrintCache,
    Timer,
    Date,
    Colorama,
    create_daily_note,
    archive_notes,
    notice,
)

def convert_input_date(date: str) -> str:
    """
    Normalize date parameters from CLI.

    支持的格式：
    - 绝对日期：``2021-01-01``
    - 相对偏移：整数（例如 ``-1`` 表示今天往前 1 天）
    - 关键字：``now`` 等价于今天
    """
    try:
        date = int(date)
    except Exception:
        pass

    if date is not None and isinstance(date, int):
        _delta_days = int(date)
        _date = datetime.datetime.strptime(Date.today(), "%Y-%m-%d") + datetime.timedelta(days=_delta_days)
        date = _date.strftime("%Y-%m-%d")

    if date == "now":
        date = Date.today()

    # 基础格式校验，出错时直接抛异常，argparse 会给出 traceback
    assert datetime.datetime.strptime(date, "%Y-%m-%d"), "input parameter 'date' format is not valid !"

    return date


def addtional_functions(parameters, printer: PrintCache) -> bool:
    """
    Non-timer features triggered by CLI flags.

    包括：
    - ``--debug``：发送一条测试通知
    - ``--create_note``：生成当日笔记
    - ``--archive_note``：归档旧笔记
    - ``--calendar``：打印日历视图
    - ``--date_calculate``：日期差值计算

    返回：
    - True  表示已经处理了本次命令，主流程无需再继续
    - False 表示没有命中任何“附加功能”，应继续走番茄钟主流程
    """
    if parameters.debug:
        notice("this is a notice")
        return True

    if parameters.create_note:
        create_daily_note(parameters.date, printer=printer)
        return True

    elif parameters.archive_note:
        if parameters.archive_note_path and parameters.archive_note_count:
            archive_list = archive_notes(
                save_count=parameters.archive_note_count,
                archive_path=parameters.archive_note_path,
            )
            import json as _json

            printer.add(_json.dumps(archive_list, indent=4))
        else:
            printer.add("archive_note_path or archive_note_count is invalid !")
        printer.print()
        return True

    elif parameters.calendar:
        DATE = datetime.datetime.strptime(parameters.date, "%Y-%m-%d")
        printer.print()
        # 只要指定了 verbose_* 之一，就强制使用 verbose 日历视图
        verbose = (
            parameters.verbose
            if parameters.verbose_vertical is False
            and parameters.verbose_quarter is False
            and parameters.verbose_year is False
            else True
        )
        if verbose:
            if parameters.verbose_year:
                printer.add(Colorama._cal_year_expand(DATE.year, DATE.month, DATE.day), endl=False)
            else:
                printer.add(
                    Colorama._cal_month_expand(
                        DATE.year,
                        DATE.month,
                        DATE.day,
                        vertical=parameters.verbose_vertical,
                        quarter=parameters.verbose_quarter,
                    ),
                    endl=False,
                )
        else:
            printer.add(Colorama._cal(DATE.year, DATE.month, DATE.day), endl=False)
        printer.print()
        return True

    elif parameters.date_calculate:
        try:
            parameters.date_calculate = int(parameters.date_calculate)
        except Exception:
            pass
        msg = Date.cal_date_interval(parameters.date, parameters.date_calculate)
        printer.add(*Colorama.color_title("Date Calculator", "yellow", length=len(msg)))
        printer.add(msg)
        printer.print()
        return True

    return False


def clock_functions(parameters, printer: PrintCache) -> None:
    """
    Main Tomato timer operations.

    对应命令行开关：
    - ``--start`` / ``--stop`` / ``--pause`` / ``--proceed`` / ``--new_tomato``
    - ``--check`` / ``--show`` / ``--records``
    - ``--edit`` / ``--edit_note``
    - ``--clock``：自动根据空闲时间切换工作/休息
    """
    # 初始化 Timer 内部的路径、当前文件等元数据
    Timer.init(printer)
    if Timer.last_file_name is None:
        printer.add("Today's work is not started.")
        printer.print()
        return

    if parameters.debug:
        return

    if parameters.start:
        Timer.start()
    elif parameters.new_tomato:
        Timer.pause()
        Timer.proceed()
        printer.add(Colorama.print("A new tomato started.", "yellow", blink=False))
        printer.print()
    elif parameters.pause:
        Timer.pause()
    elif parameters.proceed:
        Timer.proceed()
    elif parameters.stop:
        Timer.stop()
    elif parameters.check:
        Timer.check(parameters.date)
    elif parameters.show:
        Timer.show(parameters.date, parameters.verbose)
    elif parameters.records:
        Timer.records()
    elif parameters.edit:
        Timer.edit(parameters.date)
    elif parameters.edit_note:
        Timer.edit_note(parameters.date)
    elif parameters.vim_note:
        Timer.vim_note(parameters.date)
    elif parameters.clock:
        # 自动番茄钟循环：根据键盘/鼠标空闲时间自动 pause / proceed
        os.system("clear")
        printer.add(Colorama.print("Tomato Clock is Running...", "yellow", blink=False))
        printer.print()
        while True:
            try:
                time.sleep(1)

                from tomato_app.core import get_idle_time  # 局部导入避免非 macOS 平台的问题

                idle_time = get_idle_time()
                if Timer.is_paused():
                    paused_time = Timer.get_paused_time()
                    # 手动暂停时，给一点缓冲时间，避免误判
                    if paused_time is not None and paused_time < 10:
                        continue
                    if idle_time < 5:
                        print("*", Date.now(), ": Status auto change to Working")
                        Timer.proceed()
                elif idle_time > Date.delta(Date.now(), Date.now()):  # 这里保持原样逻辑，可按需调整
                    from bin.config import nap_seconds
                    from datetime import timedelta

                    if idle_time > nap_seconds:
                        print("*", Date.now(), ": Status auto change to Paused")
                        Timer.pause(timedelta(seconds=-idle_time))

            except KeyboardInterrupt:
                # Ctrl+C 时打印最终统计信息
                printer.add()
                printer.print()
                Timer.show(parameters.date, parameters.verbose)
                break
    else:
        # 默认行为：展示当天统计
        Timer.show(parameters.date, parameters.verbose)


def get_input_parameters():
    """
    Build and parse command line arguments.

    把原来散落在 ``tomato.py`` 里的参数定义集中到这里，方便以后：
    - 扩展新命令；
    - 在 README 中同步使用示例；
    - 给其他前端（如 GUI）参考有哪些可用的操作。
    """
    parser = argparse.ArgumentParser(
        description="""
            [  Tomato  Timer  ] -- author : shenjiawei
    """
    )

    parser.add_argument("-dg", "--debug", dest="debug", action="store_true", help="debug code")
    parser.add_argument("-ed", "--edit", dest="edit", action="store_true", help="edit work time record")
    parser.add_argument("-st", "--start", dest="start", action="store_true", help="start one day's work.")
    parser.add_argument("-sp", "--stop", dest="stop", action="store_true", help="stop one day's work.")
    parser.add_argument(
        "-nt",
        "--new_tomato",
        dest="new_tomato",
        action="store_true",
        help="start a new tomato period by pause and proceed.",
    )
    parser.add_argument("-p", "--pause", dest="pause", action="store_true", help="pause work and have a nap.")
    parser.add_argument(
        "-c", "--proceed", dest="proceed", action="store_true", help="proceed(continue) work and stop nap."
    )
    parser.add_argument("-ck", "--check", dest="check", action="store_true", help="check status of now's work.")
    parser.add_argument(
        "-s", "--show", dest="show", action="store_true", help="show work procedure of the day. [default]"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="store_true",
        help="show procedure verbose, use with --show command.",
    )
    parser.add_argument(
        "-vv",
        "--verbose_vertical",
        dest="verbose_vertical",
        action="store_true",
        help="show calendar verbose with vertical format, use with --calendar command.",
    )
    parser.add_argument(
        "-vq",
        "--verbose_quarter",
        dest="verbose_quarter",
        action="store_true",
        help="show calendar verbose with quarter range, use with --calendar command.",
    )
    parser.add_argument(
        "-vy",
        "--verbose_year",
        dest="verbose_year",
        action="store_true",
        help="show calendar verbose with year range, use with --calendar command.",
    )
    parser.add_argument(
        "-d",
        "--date",
        dest="date",
        type=str,
        default=Date.today(),
        help="""choose specific date. 
        eg : 2021-01-01 and -1 for delta -1 day from today, must use with other commands.""",
    )
    parser.add_argument(
        "-dc",
        "--date_calculate",
        dest="date_calculate",
        type=str,
        default=None,
        help="""Calculate day offset. 
        eg : 2021-01-01 ("now" is short for today) to get interval from the date and  -1 for delta -1 day from the date. """,
    )
    parser.add_argument("-r", "--records", dest="records", action="store_true", help="show workday records.")
    parser.add_argument(
        "-cn",
        "--create_note",
        dest="create_note",
        action="store_true",
        help="create a note file of the day.",
    )
    parser.add_argument(
        "-an",
        "--archive_note",
        dest="archive_note",
        action="store_true",
        help="archive_note note files of the days.",
    )
    parser.add_argument(
        "-anc",
        "--archive_note_count",
        dest="archive_note_count",
        type=int,
        default=None,
        help=""" archive_note note files counts """,
    )
    parser.add_argument(
        "-anp",
        "--archive_note_path",
        dest="archive_note_path",
        type=str,
        default=None,
        help=""" archive_note note files to the path """,
    )
    parser.add_argument(
        "-en",
        "--edit_note",
        dest="edit_note",
        action="store_true",
        help="edit the note file of the day.",
    )
    parser.add_argument(
        "-vn",
        "--vim_note",
        dest="vim_note",
        action="store_true",
        help="open the note file of the day in vim (respects -d).",
    )
    parser.add_argument(
        "-cal", "--calendar", dest="calendar", action="store_true", help="show calendar of the day."
    )
    parser.add_argument(
        "-clk", "--clock", dest="clock", action="store_true", help="run an Auto Tomato clock."
    )
    parser.add_argument(
        "-b",
        "--black_and_white",
        dest="black_and_white",
        action="store_true",
        help="print with black and white.",
    )
    parser.add_argument(
        "-pf",
        "--print_to_file",
        dest="print_to_file",
        type=str,
        default=None,
        help="print output to the local file",
    )

    parameters = parser.parse_args()

    # CLI 层根据用户习惯做一些显示效果的初始化
    if parameters.print_to_file is None and parameters.black_and_white is False:
        Colorama.with_color = True

    parameters.date = convert_input_date(parameters.date)
    # parameters.date_calculate = convert_input_date(parameters.date_calculate)

    return parameters


def main():
    """
    Unified entry point for the CLI.

    - 解析命令行参数；
    - 创建输出缓冲（``PrintCache``）；
    - 先尝试执行“附加功能”（日历 / 记事 / 日期计算等）；
    - 未命中附加功能时，进入番茄钟主流程。
    """
    parameters = get_input_parameters()
    printer = PrintCache(local_file=parameters.print_to_file)
    if addtional_functions(parameters, printer):
        return
    clock_functions(parameters, printer)


if __name__ == "__main__":
    main()

