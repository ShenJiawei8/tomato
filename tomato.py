# coding=utf-8
# Author: shenjiawei

import json
from subprocess import call, check_output
import os
import sys
import re
import datetime
import time
import argparse
import math
import calendar
import shutil
from bin.config import nap_seconds, auto_cut_cross_day, \
    auto_cut_cross_day_interval_hours, work_time_target_hours_one_day, \
    daily_work_note_dir, target_nap_rate, copy_daily_work_note_symlink, \
    user_name, daily_work_time_records_dir, use_notice, note_archive_count, note_archive_path
from utils.user_info import get_user_infos
from utils.install import install

TABLE_WIDTH = 70

class PrintCache():
    def __init__(self, local_file=None):
        self.cache = ''
        self.local_file = local_file

    def add(self, *segs, endl=True):
        output = ' '.join(segs)
        if endl is True:
            output += '\n'
        self.cache += output

    def get_cache(self):
        return self.cache

    def clear_cache(self):
        self.cache = ''

    def print(self):
        if self.local_file is None:
            print(self.cache, flush=True)
        else:
            with open(self.local_file, 'a') as fout:
                fout.write(self.cache + '\n')
        self.clear_cache()


def notice(content, subtitle=""):
    if use_notice:
        title = "Tomato Timer"
        cmd = '''display notification "{content}"  with title "{title}" subtitle "{subtitle}" '''.format(
            content=content,
            title=title,
            subtitle=subtitle
        )
        call(["osascript", "-e", cmd])


def get_idle_time():
    t = os.popen('ioreg -c IOHIDSystem | grep HIDIdleTime').read()
    return float(re.search("= (\d*)", t).group(1)) / float(1000000000)


def update_symlink(src, dst):
    if os.path.islink(dst):
        os.remove(dst)
    os.symlink(src, dst)


def chown_to_user(loc, user_info):
    gid, uid = int(user_info['gid']), int(user_info['uid'])
    return os.chown(loc, uid, gid)


def get_note_path(date):
    return os.path.join(daily_work_note_dir, date + '.md')


def get_note_link_path(date):
    return os.path.join(copy_daily_work_note_symlink, date + '.md')


def create_daily_note(date, printer=None):
    def _simplify_today_work(work_lines):
        before_block = []
        today_block = []
        today_line = None
        in_today_block = False
        for l in work_lines:
            if "# TODAY:" in l:
                in_today_block = True
                today_line = l
                continue
            if in_today_block:
                if l.strip() == "[ ]" or len(l.strip()) == 0:
                    continue
                else:
                    today_block.append(l)

            else:
                before_block.append(l)

        return before_block + [today_line] + today_block if len(today_block) else before_block

    note_path = get_note_path(date)
    DATE = datetime.datetime.strptime(date, "%Y-%m-%d")

    if os.path.isfile(note_path):
        if printer:
            printer.add('Note file({note_path}) is already exit, skip create.'.format(note_path=note_path))
            printer.print()
        return
    else:
        date_obj = DATE
        for i in range(30):
            date_obj = date_obj + datetime.timedelta(days=-1)
            last_day = date_obj.strftime("%Y-%m-%d")
            last_day_note_path = get_note_path(last_day)
            if os.path.isfile(last_day_note_path):
                _last_todo_list = []
                with open(last_day_note_path) as fin:
                    get_record = False
                    while True:
                        line = fin.readline()
                        if 'work started, have a nice day ~' in line:
                            get_record = True
                            continue
                        if not get_record:
                            continue
                        if line and '# DONE:' not in line:
                            _last_todo_list.append(line)
                            continue
                        break
                _last_todo_list = _simplify_today_work(_last_todo_list)
                last_todo = ''.join(_last_todo_list)
                last_todo = re.sub('# TODAY', '# ' + last_day, last_todo)
                last_todo = last_todo.rstrip()
                break
        else:
            if printer:
                printer.add('Cannot find todo of recent 30 days, init with empty todo')
                printer.print()
            last_todo = ''

    with open(note_path, 'a+') as fout:
        msg = '''{cal}

{date}'s work started, have a nice day ~
{last_todo}

        # TODAY:
            [ ] 

        # DONE:
            [x] 

@ start work record below


'''.format(
            date=date,
            cal=Colorama._cal_month_expand(DATE.year, DATE.month, DATE.day, quarter=True, for_note=True),
            last_todo=last_todo)
        fout.write(msg)
    user_infos = get_user_infos(user_name)
    if len(user_infos):
        chown_to_user(note_path, user_infos[0])
    if copy_daily_work_note_symlink is not None:
        symlink = get_note_link_path(date)
        update_symlink(note_path, symlink)
        if len(user_infos):
            chown_to_user(symlink, user_infos[0])


def archive_notes(save_count=10, archive_path=""):
    archive_list = []
    if not archive_path:
        return archive_list
    for f in os.listdir(daily_work_note_dir):
        f_path = os.path.join(daily_work_note_dir, f)
        f_symlink_path = os.path.join(copy_daily_work_note_symlink, f)
        if os.path.isfile(f_path) and f.endswith('.md'):
            _date = f.split('.')[0]
            if Date.delta(_date, Date.today(), seconds=False) >= save_count:
                f_archive_path = os.path.join(archive_path, f)
                shutil.move(f_path, f_archive_path)
                os.remove(f_symlink_path)
                archive_list.append({
                    'mv_note_path': f_path,
                    'archive_to_path': f_archive_path,
                    'rm_symlink': f_symlink_path
                })
    return archive_list


class Colorama(object):
    with_color = False

    @classmethod
    def _red(cls, msg):
        return "\033[31m%s\033[0m" % (msg)

    @classmethod
    def _blue(cls, msg):
        return "\033[36m%s\033[0m" % (msg)

    @classmethod
    def _yellow(cls, msg):
        return "\033[33m%s\033[0m" % (msg)

    @classmethod
    def _blink(cls, msg):
        return "\033[5m%s\033[0m" % (msg)

    @classmethod
    def print(cls, msg, color=None, blink=False):
        if not Colorama.with_color:
            return msg
        if color == 'red':
            msg = cls._red(msg)
        if color == 'blue':
            msg = cls._blue(msg)
        if color == 'yellow':
            msg = cls._yellow(msg)
        if blink:
            return cls._blink(msg)
        return msg

    @classmethod
    def color_title(cls, msg, color, length=36, delimiter='+', delimiter_color=None):
        length = float(length)
        l = float(len(msg))
        side = (length - l) / 2
        left = math.floor(side)
        right = math.ceil(side)
        return cls.print(delimiter * left, delimiter_color), \
            cls.print(msg, color), cls.print(delimiter * right, delimiter_color)

    @classmethod
    def _cal(cls, year, month, day, indent='', expand=0, for_note=False, highlight=True):
        _with_color = False if for_note is True else Colorama.with_color
        s = calendar.month(year, month)
        s = re.sub(r'\b', ' ' * expand, s)
        pre, suf = s.split('Su')
        date = re.sub('^0', ' ', str(day))
        date = date if day >= 10 else ' %s' % date
        if _with_color is False:
            if highlight:
                suf = re.sub(date, '==', suf, count=1)
            cal = pre + 'Su' + suf
        else:
            date_lines = suf.split('\n')
            suf_lines = list()
            for line in date_lines:
                if len(line) > 0:
                    weekend = re.split(' +', line[15:].strip())
                    if len(weekend) == 1 and len(line.strip()) >= 4:
                        sat = weekend[0]
                        sun = ''
                    elif len(weekend) == 1 and len(line.strip()) < 4:
                        sun = weekend[0]
                        sat = ''
                    else:
                        sat, sun = weekend[0], weekend[1]

                    sat = sat if len(sat) > 0 and int(sat) >= 10 else ' %s' % sat if len(sat) > 0 else '  '
                    sun = sun if len(sun) > 0 and int(sun) >= 10 else ' %s' % sun
                    line = line if len(line) < 17 else line[:15] + cls.print(sat, 'yellow') + ' ' + cls.print(sun,
                                                                                                              'yellow')
                suf_lines.append(line)
            suf = '\n'.join(suf_lines)
            if highlight:
                suf = re.sub(date, cls.print(date, 'red'), suf, count=1)
            cal = cls.print(pre.split('\n')[0], 'yellow') + '\n' + cls.print(pre.split('\n')[1], 'blue') + cls.print(
                'Su', 'blue') + suf
        cal = re.sub('^', indent, cal)
        cal = re.sub('\n', '\n' + indent, cal)
        return cal

    @classmethod
    def _cal_month_expand(cls, year, month, day, indent='', expand=0, quarter=False, for_note=False):
        def _get_quarter_months(month):
            month = int(month)
            quarter = int((month + 2) / 3)
            quarter_first_month = (quarter -1) * 3 + 1
            return int(quarter_first_month), int(quarter_first_month+ 1), int(quarter_first_month+ 2)

        if quarter:
            month_0, month_1, month_2 = _get_quarter_months(month)
            year_0 = year_1 = year_2 = year
        else:
            date_month_first_day_obj = datetime.datetime.strptime("{year}-{month}-01".format(year=year, month=month),
                                                                  "%Y-%m-%d")
            month_obj_0 = date_month_first_day_obj + datetime.timedelta(days=-1)
            month_obj_2 = date_month_first_day_obj + datetime.timedelta(days=32)
            month_0 = month_obj_0.month
            month_2 = month_obj_2.month
            year_0 = month_obj_0.year
            year_2 = month_obj_2.year

            year_1 = year
            month_1 = month

        cal_0 = cls._cal(year_0, month_0, 1 if month != month_0 else day, indent='', expand=expand, for_note=True, highlight=False if month != month_0 else True)
        cal_1 = cls._cal(year_1, month_1, 1 if month != month_1 else day, indent='', expand=expand, for_note=True, highlight=False if month != month_1 else True)
        cal_2 = cls._cal(year_2, month_2, 1 if month != month_2 else day, indent='', expand=expand, for_note=True, highlight=False if month != month_2 else True)

        cal_expand_lines = []
        for lines in zip(cal_0.split('\n'), cal_1.split('\n'), cal_2.split('\n')):
            _lines = []
            for line in lines:
                if len(line) < 20:
                    _line = line + (20 - len(line)) * ' '
                else:
                    _line = line
                _lines.append(_line)
            cal_expand_lines.append(indent + '   '.join(_lines))
        _cal_expand = '\n'.join(cal_expand_lines)
        if Colorama.with_color and for_note is False:
            date = str(day) if day >= 10 else ' %s' % str(day)
            _cal_expand = re.sub("==", cls.print(date, 'red'), _cal_expand, count=1)
        return _cal_expand

    @classmethod
    def _cal_date_interval(cls, date, date_calculate):
        if isinstance(date_calculate, int):
            _delta_days_for_calculate = int(date_calculate)
            _date_for_calculate = datetime.datetime.strptime(date, "%Y-%m-%d") + datetime.timedelta(
                days=_delta_days_for_calculate)
            date_calculate_for_print = Colorama.print(_date_for_calculate.strftime("%Y-%m-%d"), color='blue')
            _delta_days_for_calculate_for_print = str(_delta_days_for_calculate)
            _delta_months = Date.diff_month(datetime.datetime.strptime(date, "%Y-%m-%d"), _date_for_calculate)
        else:
            if date_calculate is None or date_calculate == "now":
                date_calculate = Date.today()
            _delta_days = datetime.datetime.strptime(date_calculate, "%Y-%m-%d") - datetime.datetime.strptime(date,
                                                                                                              "%Y-%m-%d")
            _delta_days_for_calculate = _delta_days.days
            date_calculate_for_print = date_calculate
            _delta_days_for_calculate_for_print = Colorama.print(_delta_days.days, color='blue')
            _delta_months = Date.diff_month(datetime.datetime.strptime(date, "%Y-%m-%d"),
                                            datetime.datetime.strptime(date_calculate, "%Y-%m-%d"))

        _delta_years = '%.2f' % round(float(_delta_days_for_calculate) / float(365), 2)
        _delta_years = _delta_years.zfill(5)

        return "* {_delta_days_for_calculate_for_print} days ({_delta_years} years, {_delta_months} months) between {date} ~ {date_calculate_for_print} ". \
            format(_delta_days_for_calculate_for_print=_delta_days_for_calculate_for_print,
                   _delta_years=_delta_years,
                   _delta_months=_delta_months,
                   date=date,
                   date_calculate_for_print=date_calculate_for_print)


class Date():
    '''
    时间格式化工具类
    '''

    @classmethod
    def date(cls):
        return datetime.datetime.now().strftime("%Y-%m-%d")

    @classmethod
    def now(cls, delta=None):
        now = datetime.datetime.now()
        now = now + delta if delta is not None else now
        return now.strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def today(cls, delta=None):
        now = datetime.datetime.now()
        now = now + delta if delta is not None else now
        return now.strftime("%Y-%m-%d")

    @classmethod
    def delta(cls, d1, d2, seconds=True):
        if seconds:
            d1 = datetime.datetime.strptime(d1, "%Y-%m-%d %H:%M:%S")
            d2 = datetime.datetime.strptime(d2, "%Y-%m-%d %H:%M:%S")
        else:
            d1 = datetime.datetime.strptime(d1, "%Y-%m-%d")
            d2 = datetime.datetime.strptime(d2, "%Y-%m-%d")
        _seconds = (d2 - d1).seconds
        _days = (d2 - d1).days
        return _seconds + _days * 86400 if seconds else _days

    @classmethod
    def diff_month(cls, d1, d2):
        return (d2.year - d1.year) * 12 + d2.month - d1.month

    @classmethod
    def format_delta(cls, delta, tomato_mode=True, with_check=False, blink=False, nap_notice=False):
        hour, minute, second, tomato = cls._format_delta(delta)
        if blink:
            tomato_icon = Colorama.print('x 🍅', blink=True)
            check_icon = Colorama.print('✅ ', blink=True)
        else:
            tomato_icon = 'x 🍅'
            check_icon = '✅ '
        if tomato_mode:
            return "{hour}:{minute}  =>  {tomato} {finish}{nap_notice}".format(
                hour=hour,
                minute=minute,
                tomato=tomato,
                finish=tomato_icon if float(tomato) >= 1 and with_check else '    ',
                nap_notice=Colorama.print('\n [ You need a nap now to relax your eyes ~ ]', 'yellow',
                                          blink=False) if nap_notice and float(tomato) >= 1 else '')
        else:
            return "{hour}:{minute} {enough_break}{nap_notice}".format(
                hour=hour,
                minute=minute,
                enough_break=check_icon if delta > nap_seconds and with_check else '    ',
                nap_notice=Colorama.print('\n [You have got enough rest, back to work now ~ ]', 'yellow',
                                          blink=False) if nap_notice is True else '')

    @classmethod
    def _format_delta(cls, delta):
        hour = '%02d' % int(delta / 3600)
        minute = '%02d' % (int((delta % 3600) / 60) if delta >= 0 else int((delta % 3600 - 3600) / 60))
        second = '%02d' % (int(delta % 60) if delta >= 0 else int(delta % 60 - 60))
        tomato = '%.2f' % round(float(delta) / float(1800), 2)
        tomato = tomato.zfill(5)
        return hour, minute, second, tomato

    @classmethod
    def weekday(cls, d):
        return datetime.datetime.strptime(d, "%Y-%m-%d").weekday() + 1

    @classmethod
    def day_hour(cls, d):
        return datetime.datetime.strptime(d, "%Y-%m-%d %H:%M:%S").strftime("%Y%m%d/%H")

    @classmethod
    def day(cls, d):
        return datetime.datetime.strptime(d, "%Y-%m-%d %H:%M:%S").strftime("%Y%m%d/%H")

    @classmethod
    def hour_list(cls, d_start, d_end):
        hl = []
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
    def merge_visualize(cls, map_start, map_end):
        hour_map = [int(i) for i in ('0' * 60)]
        for i in range(60):
            hour_map[i] = map_start[i] | map_end[i]
        return hour_map

    @classmethod
    def timing_seg_distribute(cls, timing_seg):
        def _visualize_hour(start, end):
            hour_map = [int(i) for i in ('0' * 60)]
            start_min = int(start.strftime("%M"))
            start_hour = int(start.strftime("%H"))
            end_min = int(end.strftime("%M"))
            end_hour = int(end.strftime("%H"))
            end_min = 60 if end_min == 0 and start_hour != end_hour else end_min
            for i in range(start_min, end_min):
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
                    'sum': cls.delta(timing_seg[0], timing_seg[1]),
                    'map': _visualize_hour(st_obj, et_obj)
                }
            }
        else:
            result = dict()
            first_inter = datetime.datetime.strptime(hl[1], "%Y%m%d/%H")
            first_sum = (first_inter - datetime.datetime.strptime(timing_seg[0], "%Y-%m-%d %H:%M:%S")).seconds
            first_map = _visualize_hour(st_obj, datetime.datetime.strptime(hl[1], "%Y%m%d/%H"))
            last_inter = datetime.datetime.strptime(hl[-1], "%Y%m%d/%H")
            last_sum = (datetime.datetime.strptime(timing_seg[1], "%Y-%m-%d %H:%M:%S") - last_inter).seconds
            last_map = _visualize_hour(datetime.datetime.strptime(hl[-1], "%Y%m%d/%H"), et_obj)
            for h in hl:
                if h == sh:
                    result[h] = {'sum': first_sum, 'map': first_map}
                elif h == eh:
                    result[h] = {'sum': last_sum, 'map': last_map}
                else:
                    result[h] = {'sum': 3600, 'map': [int(i) for i in ('1' * 60)]}
            return result

    @classmethod
    def visualize_map(cls, map_dict):
        def _visualize(_map, _sum):
            _sum = int(float(_sum) / float(60))
            _count = 1
            m = ''
            for i in _map:
                if _count <= int(_sum):
                    m += Colorama.print('▓', 'blue') if i else Colorama.print('▓', 'red')
                else:
                    m += Colorama.print('░', 'blue') if i else Colorama.print('░', 'red')
                _count += 1
            return m

        def _cut_last_map(_map):
            _new_map = []
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

        result = dict()
        count = 0
        for h, d in map_dict.items():
            count += 1
            if count == len(map_dict):  # last item
                result[h] = _visualize(_cut_last_map(d['map']), d['sum'])
            else:
                result[h] = _visualize(d['map'], d['sum'])
        return result


class Timer():

    @classmethod
    def init(cls, printer=None):
        record_path, last_files, today_file_name, last_file_name, today_symlink, today, last_day, tmp_detail_data = cls.get_file_name()
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
        create_daily_note(cls.last_file_name.split('/')[-1])
        archive_notes(save_count=note_archive_count, archive_path=note_archive_path)

    @classmethod
    def get_file_name(cls):
        '''
        last_day: "最近"一天的工作。如果结束了（最后一个节点不是正在进行中），则last_day 为 today
        '''
        path_root = os.path.split(os.path.realpath(__file__))[0]
        path = daily_work_time_records_dir
        tmp_detail_data = os.path.join(path_root, 'bin/tmp/detail_data')
        today_file_name = os.path.join(path, Date.date())
        today_symlink = os.path.join(path_root, 'bin/today')
        today = Date.date()
        last_file_name = today_file_name
        last_day = today
        last_files = os.listdir(path)
        last_files.sort()
        if len(last_files) >= 1:
            _last_file_name = os.path.join(path, last_files[-1])
            _last_day = last_files[-1]

            with open(_last_file_name) as fin:
                items = json.loads(fin.read())

            if len(items[-1]) == 1:
                last_file_name = _last_file_name
                last_day = _last_day

        return path, last_files, today_file_name, last_file_name, today_symlink, today, last_day, tmp_detail_data

    @classmethod
    def start(cls):
        if not os.path.isfile(cls.last_file_name):
            with open(cls.last_file_name, 'w') as fout:
                item = json.dumps([[Date.now()]], indent=4)
                fout.write(item)
            update_symlink(cls.last_file_name, cls.today_symlink)
            msg = "{today}'s work started...".format(today=cls.today)
        else:
            msg = "{today}'s work is already started.".format(today=cls.today)
        cls.printer.add(msg)
        cls.printer.print()

    @classmethod
    def is_paused(cls):
        if not os.path.isfile(cls.last_file_name):
            # work is not started.
            return True
        with open(cls.last_file_name) as fin:
            items = json.loads(fin.read())
            return False if len(items[-1]) == 1 else True

    @classmethod
    def get_paused_time(cls):
        if not os.path.isfile(cls.last_file_name):
            # work is not started.
            return None

        with open(cls.last_file_name) as fin:
            items = json.loads(fin.read())
            if len(items[-1]) == 2:
                return Date.delta(items[-1][1], Date.now())
            else:
                return None

    @classmethod
    def pause(cls, delta=None):
        with open(cls.last_file_name) as fin:
            items = json.loads(fin.read())

        got_pauser_point = False

        for i in range(len(items)):
            index = len(items) - 1 - i
            if len(items[index]) != 2:
                got_pauser_point = True
                items[index].append(Date.now(delta))
                break

        if got_pauser_point:
            with open(cls.last_file_name, 'w') as fout:
                fout.write(json.dumps(items, indent=4))
                msg = "{last_day}'s work paused... ".format(last_day=cls.last_day)
                notice(msg, "Action: Pause work")
                cls.printer.add(msg)
        else:
            cls.printer.add('Already paused')

        cls.printer.print()

    @classmethod
    def auto_cut_cross_day(cls):
        if auto_cut_cross_day is True:
            record_path, last_files, today_file_name, last_file_name, today_symlink, today, last_day, tmp_detail_data = cls.get_file_name()
            auto_cut_cross_day_interval_hours = 0
            if not os.path.isfile(today_file_name) and get_idle_time() > auto_cut_cross_day_interval_hours * 3600:
                cls.init()
                cls.start()

    @classmethod
    def proceed(cls):

        cls.auto_cut_cross_day()

        if not cls.is_paused():
            msg = "Already in working status.".format(last_day=cls.last_day)
            notice(msg, "Action: Proceed work")
            cls.printer.add(msg)
            return

        with open(cls.last_file_name) as fin:
            items = json.loads(fin.read())

        with open(cls.last_file_name, 'w') as fout:
            items.append([Date.now()])
            fout.write(json.dumps(items, indent=4))
            msg = "proceed {last_day}'s work ...".format(last_day=cls.last_day)
            notice(msg, "Action: Proceed work")
            cls.printer.add(msg)

        cls.printer.print()

    @classmethod
    def stop(cls):
        Timer.pause()

        work_time = 0

        with open(cls.last_file_name) as fin:
            items = json.loads(fin.read())
            for item in items:
                if len(item) == 2:
                    work_time += Date.delta(item[0], item[1])

        cls.printer.add("{last_day}'s work stoped".format(last_day=cls.last_day))
        cls.printer.add(Date.format_delta(work_time))
        cls.printer.print()

    @classmethod
    def check(cls, specific_date):
        specific_date = cls.last_file_name if specific_date == Date.today() else os.path.join(cls.record_path,
                                                                                              specific_date)
        with open(specific_date) as fin:
            cls.printer.add(*Colorama.color_title('Tomato', 'yellow'))
            items = json.loads(fin.read())

            work_time = 0

            for item in items:
                if len(item) == 2:
                    work_time += Date.delta(item[0], item[1])

            last_item = items[len(items) - 1]
            if len(last_item) == 1:
                tomato = Date.delta(item[0], Date.now())
                work_time += tomato
                msg = '*' + " Now Status: " + "Working "
                cls.printer.add(msg)
                cls.printer.add('*', "Current:",
                                Colorama.print(Date.format_delta(tomato, with_check=True, blink=True, nap_notice=True),
                                               'yellow'))
            else:
                msg = '*' + " Work Status: " + "paused"
                cls.printer.add(msg)

            notice(msg, "Action: Check work status")
        cls.printer.print()

    @classmethod
    def records(cls, count=7):
        cls.printer.add('''Already record {days} days' work, recent {count} days are below:'''.format(
            days=Colorama.print(str(len(cls.last_files)), 'red'),
            count=count))
        cls.printer.add()
        recent_days = cls.last_files[-count:]
        recent_days.reverse()
        for d in recent_days:
            cls.printer.add(d)
        cls.printer.print()

    @classmethod
    def show(cls, specific_date=None, verbose=False, output=None):
        _specific_date = cls.last_file_name if specific_date == Date.today() else os.path.join(cls.record_path,
                                                                                               specific_date)
        _date = _specific_date.split('/')[-1]
        if not os.path.isfile(_specific_date):
            cls.printer.add(Colorama.print('No record.', 'red'))
            cls.printer.print()
            return
        cls.printer.add(*Colorama.color_title(
            'Tomato History : {_date}, Weekday {weekday}'.format(_date=_date, weekday=Date.weekday(_date)), 'yellow',
            TABLE_WIDTH))
        cls.printer.add()
        cls.printer.add('   Num   |  Work Time Interval |        Tomato         |  Nap (5min)')
        cls.printer.add('-' * 70)
        previous_item = None
        with open(_specific_date) as fin:
            items = json.loads(fin.read())
            hl_sum = dict()
            work_time = 0
            for item in items:

                if previous_item and (items.index(item) > len(items) - 9 or verbose):
                    cls.printer.add(
                        Date.format_delta(Date.delta(previous_item[1], item[0]), tomato_mode=False, with_check=False))

                previous_item = item

                if len(item) == 2:
                    if item[1] <= item[0]:
                        previous_item = None
                        continue
                    if items.index(item) > len(items) - 10 or verbose:
                        cls.printer.add('*  %03d:    ' % items.index(item), item[0][10:16], ' ~', item[1][10:16], '   ',
                                        Date.format_delta(Date.delta(item[0], item[1]), with_check=True), '    ',
                                        endl=False)
                    for seg, t in Date.timing_seg_distribute(item).items():
                        if seg not in hl_sum:
                            hl_sum[seg] = t
                        else:
                            hl_sum[seg]['sum'] += t['sum']
                            hl_sum[seg]['map'] = Date.merge_visualize(hl_sum[seg]['map'], t['map'])
                    work_time += Date.delta(item[0], item[1])
                elif items.index(item) == len(items) - 1:
                    for seg, t in Date.timing_seg_distribute([item[0], Date.now()]).items():
                        if seg not in hl_sum:
                            hl_sum[seg] = t
                        else:
                            hl_sum[seg]['sum'] += t['sum']
                            hl_sum[seg]['map'] = Date.merge_visualize(hl_sum[seg]['map'], t['map'])
                    work_time += Date.delta(item[0], Date.now())

            last_item = items[-1]
            if len(last_item) == 1:
                end_time = Date.now()
                tomato = Date.delta(last_item[0], Date.now())
                cls.printer.add('*  %03d:    ' % (len(items) - 1), item[0][10:16], ' ~', '  ... ', '   ',
                                Date.format_delta(Date.delta(last_item[0], Date.now()), with_check=True), '   ',
                                endl=False)
            else:
                end_time = last_item[1]

            cls.printer.add('\n')
            cls.printer.add(*Colorama.color_title('Hour History (unit: Minute)', 'yellow', TABLE_WIDTH))
            cls.printer.add()
            cls.printer.add('   00        10        20        30        40        50        60')
            hl_sum_visual = Date.visualize_map(hl_sum)
            for h in Date.hour_list(items[0][0], end_time):
                cls.printer.add(h[9:] + ': ', endl=False)
                if h in hl_sum_visual and len(hl_sum_visual[h]):
                    cls.printer.add(hl_sum_visual[h],
                                    '%.2f' % round(float(hl_sum[h]['sum']) / 60, 2))
                else:
                    cls.printer.add(Colorama.print('░', 'red') * 60, '00.00')

            cls.printer.print()

            start_time = items[0][0]
            wt = Date.delta(start_time, end_time)
            target_time = Date.now(datetime.timedelta(seconds=work_time_target_hours_one_day * 3600 - work_time))
            cls.printer.add(*Colorama.color_title('Summary', 'yellow', TABLE_WIDTH))
            cls.printer.add()
            target_finish_rate = round(float(work_time) / float(work_time_target_hours_one_day * 3600) * 100)
            target_finish_rate_str = Colorama.print(str(target_finish_rate) + ' %',
                                                    'blue' if target_finish_rate > 90 else 'yellow',
                                                    blink=False)
            # blink = False if target_finish_rate > 90 else True)
            cls.printer.add('*', 'Start Time: ', start_time[:16], '     * Target Finish Rate: ', target_finish_rate_str)
            if specific_date == Date.today():
                cls.printer.add('* Target Time:', target_time[:16], '✅' if target_time <= Date.now() else '    ',
                                '* Work Rate Target:   ', Colorama.print(str(round(
                        float(work_time_target_hours_one_day * 3600) / float(
                            work_time_target_hours_one_day * 3600 + wt - work_time) * 100)) + ' %', 'blue'))
            else:
                cls.printer.add('*', 'Stop Time:  ', last_item[1][:16] if len(last_item) > 1 else last_item[0][:16])
            nap_rate = round(float(wt - work_time) / float(wt) * 100)
            nap_rate_str = str(nap_rate) + ' %'
            cls.printer.add('*', 'All Time:   ', Date.format_delta(wt, with_check=False, blink=False, tomato_mode=True),
                            '* Work Rate:',
                            Colorama.print(str(round(float(work_time) / float(wt) * 100)) + ' %', 'blue'),
                            ', Nap Rate:',
                            Colorama.print(nap_rate_str, 'blue') if nap_rate <= target_nap_rate else Colorama.print(
                                nap_rate_str, 'red', blink=False))

            cls.printer.add('*', 'Work Time:  ', Date.format_delta(work_time, with_check=False, blink=False),
                            '* CountDown:', Date.format_delta(Date.delta(Date.now(), target_time)))
            cls.printer.add('*', 'Nap Time:   ',
                            Date.format_delta((wt - work_time), with_check=False, blink=False, tomato_mode=True))
            cls.printer.add()
            note_path = get_note_path(_date)
            note_info = note_path if os.path.exists(note_path) else "note file is not exist."
            cls.printer.add('* Note: {note_path}'.format(note_path=note_info))
            cls.printer.add()
            DATE = datetime.datetime.strptime(_date, "%Y-%m-%d")
            cls.printer.add(*Colorama.color_title('Calendar', 'yellow', TABLE_WIDTH))
            cls.printer.add()
            cls.printer.add(Colorama._cal_month_expand(DATE.year, DATE.month, DATE.day, indent='  ', quarter=True))
            cls.printer.add()
            cls.printer.add(*Colorama.color_title('Tomato Timer :  NowTime: ' + Date.now(), 'yellow', TABLE_WIDTH))
            cls.printer.print()


def addtional_functions(parameters, printer):
    # Addtional Functions
    if parameters.debug:
        return True

    if parameters.create_note:
        create_daily_note(parameters.date, printer=printer)
        return True

    elif parameters.archive_note:
        if parameters.archive_note_path and parameters.archive_note_count:
            archive_list = archive_notes(save_count=parameters.archive_note_count,
                                         archive_path=parameters.archive_note_path)
            printer.add(json.dumps(archive_list, indent=4))
        else:
            printer.add('archive_note_path or archive_note_count is invalid !')
        printer.print()
        return True

    elif parameters.calendar:
        DATE = datetime.datetime.strptime(parameters.date, "%Y-%m-%d")
        printer.print()
        if parameters.verbose:
            printer.add(Colorama._cal_month_expand(DATE.year, DATE.month, DATE.day), endl=False)
        else:
            printer.add(Colorama._cal(DATE.year, DATE.month, DATE.day), endl=False)
        printer.print()
        return True

    elif parameters.date_calculate:
        try:
            parameters.date_calculate = int(parameters.date_calculate)
        except:
            pass
        msg = Colorama._cal_date_interval(parameters.date, parameters.date_calculate)
        printer.add(*Colorama.color_title('Date Calculator', 'yellow', length=len(msg)))
        printer.add(msg)
        printer.print()
        return True

    return False


def clock_functions(parameters, printer):
    # Tomato Clock Functions
    Timer.init(printer)
    if Timer.last_file_name is None:
        printer.add("Today's work is not started.")
        printer.print()
        return

    if parameters.start:
        Timer.start()
    elif parameters.new_tomato:
        Timer.pause()
        Timer.proceed()
        printer.add(Colorama.print('A new tomato started.', 'yellow', blink=False))
        printer.print()
    elif parameters.pause:
        Timer.pause()
    elif parameters.proceed:
        Timer.proceed()
    elif parameters.pause:
        Timer.pause()
    elif parameters.stop:
        Timer.stop()
    elif parameters.check:
        Timer.check(parameters.date)
    elif parameters.show:
        Timer.show(parameters.date, parameters.verbose)
    elif parameters.records:
        Timer.records()
    elif parameters.clock:
        os.system('clear')
        printer.add(Colorama.print('Tomato Clock is Running...', 'yellow', blink=False))
        printer.print()
        while True:
            try:
                time.sleep(1)

                idle_time = get_idle_time()
                if Timer.is_paused():
                    paused_time = Timer.get_paused_time()
                    if paused_time is not None and paused_time < 10:
                        continue
                    if idle_time < 5:
                        print('*', Date.now(), ': Status auto change to Working')
                        Timer.proceed()
                elif idle_time > nap_seconds:
                    print('*', Date.now(), ': Status auto change to Paused')
                    Timer.pause(datetime.timedelta(seconds=-idle_time))
                # elif

            except KeyboardInterrupt:
                printer.add()
                printer.print()
                Timer.show(parameters.date, parameters.verbose)
                break
    else:
        Timer.show(parameters.date, parameters.verbose)
        # print(Colorama.print('Use "python tomato.py -h" to get more information.', 'yellow'))

def convert_input_date(date):
    try:
        date = int(date)
    except:
        pass

    if date is not None and isinstance(date, int):
        _delta_days = int(date)
        _date = datetime.datetime.strptime(Date.today(), "%Y-%m-%d") + datetime.timedelta(days=_delta_days)
        date = _date.strftime("%Y-%m-%d")

    if date == 'now':
        date = Date.today()

    assert datetime.datetime.strptime(date, "%Y-%m-%d"), "input parameter 'date' format is not valid !"

    return date


def get_input_parameters():
    parser = argparse.ArgumentParser(description="""
            [  Tomato  Timer  ] -- author : shenjiawei
    """)

    parser.add_argument('-dg', '--debug', dest='debug', action='store_true', help="debug code")
    parser.add_argument('-st', '--start', dest='start', action='store_true', help="start one day's work.")
    parser.add_argument('-sp', '--stop', dest='stop', action='store_true', help="stop one day's work.")
    parser.add_argument('-nt', '--new_tomato', dest='new_tomato', action='store_true',
                        help="start a new tomato period by pause and proceed.")
    parser.add_argument('-p', '--pause', dest='pause', action='store_true', help='pause work and have a nap.')
    parser.add_argument('-c', '--proceed', dest='proceed', action='store_true',
                        help='proceed(continue) work and stop nap.')
    parser.add_argument('-ck', '--check', dest='check', action='store_true', help="check status of now's work.")
    parser.add_argument('-s', '--show', dest='show', action='store_true', help='show work procedure of the day. [default]')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                        help='show procedure verbose, use with --show command.')
    parser.add_argument('-d', '--date', dest='date', type=str, default=Date.today(), help='''choose specific date. 
        eg : 2021-01-01 or -1 for delta -1 day from today, must use with other commands.''')
    parser.add_argument('-dc', '--date_calculate', dest='date_calculate', type=str, default=None, help='''Calculate day offset. 
        eg : 2021-01-01 ("now" for today)to get interval from the date; -1 for delta -1 day from the date, ''')
    parser.add_argument('-r', '--records', dest='records', action='store_true', help='show workday records.')
    parser.add_argument('-cn', '--create_note', dest='create_note', action='store_true',
                        help='create a note file of the day.')
    parser.add_argument('-an', '--archive_note', dest='archive_note', action='store_true',
                        help='archive_note note files of the days.')
    parser.add_argument('-anc', '--archive_note_count', dest='archive_note_count', type=int, default=None,
                        help=''' archive_note note files counts ''')
    parser.add_argument('-anp', '--archive_note_path', dest='archive_note_path', type=str, default=None,
                        help=''' archive_note note files to the path ''')
    parser.add_argument('-cal', '--calendar', dest='calendar', action='store_true', help='show calendar of the day.')
    parser.add_argument('-clk', '--clock', dest='clock', action='store_true', help='run an Auto Tomato clock.')
    parser.add_argument('-bw', '--black_and_white', dest='black_and_white', action='store_true',
                        help='print with black and white.')
    parser.add_argument('-pf', '--print_to_file', dest='print_to_file', type=str, default=None,
                        help='print output to the local file')

    parameters = parser.parse_args()

    if parameters.print_to_file is None and parameters.black_and_white is False:
        Colorama.with_color = True

    parameters.date = convert_input_date(parameters.date)
    # parameters.date_calculate = convert_input_date(parameters.date_calculate)

    return parameters


if __name__ == "__main__":
    parameters = get_input_parameters()
    printer = PrintCache(local_file=parameters.print_to_file)
    if addtional_functions(parameters, printer):
        pass
    else:
        clock_functions(parameters, printer)
