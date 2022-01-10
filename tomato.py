#coding=utf-8
#Author: shenjiawei

import json
from subprocess import call, check_output
import os
import sys
import re
import datetime
import time
import argparse
import math
import subprocess
import calendar  
import pty
from pprint import pprint
from bin.config import nap_seconds, termgraph_dir, auto_cut_cross_day, \
    auto_cut_cross_day_interval_hours, work_time_target_hours_one_day, \
    daily_work_note_dir, target_nap_rate, schedule, copy_daily_work_note_symlink, \
    user_name, daily_work_time_records_dir, python_path
from utils.user_info import get_user_infos

class PrintCache():
    def __init__(self):
        self.cache = ''
        pass

    def add(self, *segs, endl=True):
        output = ' '.join(segs)
        if endl is True:
            output += '\n'
        self.cache += output

    def get_cache(self):
        return cache

    def clear_cache(self):
        self.cache = ''

    def print(self):
        print(self.cache, flush=True)
        self.clear_cache()
 

def notice(content):
    title = "Work Timer"
    cmd = '''display notification "{content}"  with title "{title}" '''.format(
        content=content,
        title=title
    )
    call(["osascript", "-e", cmd])


def get_idle_time():
    t = os.popen('ioreg -c IOHIDSystem | grep HIDIdleTime').read()
    return float(re.search("= (\d*)", t).group(1))/float(1000000000)


def update_symlink(src, dst):
    if os.path.islink(dst):
        os.remove(dst)
    os.symlink(src, dst)


def chown_to_user(loc, user_info):
    gid, uid = int(user_info['gid']), int(user_info['uid'])
    return os.chown(loc, uid, gid)


def _cal(year, month, day, indent='', expand=0, colorful=False):
    s = calendar.month(year, month)
    s=re.sub(r'\b', ' '*expand, s)
    pre, suf = s.split('Su')
    date = re.sub('^0', ' ', str(day))
    date = date if day >= 10 else ' %s' % date
    if colorful is False:
        suf = re.sub(date, '==', suf, count=1)
        cal = pre + 'Su' + suf
    else:
        suf = re.sub(date, Colorama.print(date, 'red'), suf, count=1)
        cal = Colorama.print(pre.split('\n')[0], 'yellow') + '\n' + Colorama.print(pre.split('\n')[1], 'blue') + Colorama.print('Su', 'blue') + suf
    cal=re.sub('^', indent, cal)
    cal=re.sub('\n', '\n'+indent, cal)
    return cal.rstrip()


def create_daily_note(date):
    
    def get_note_path(date):
        return os.path.join(daily_work_note_dir, date+'.md')

    def get_note_link_path(date):
        return os.path.join(copy_daily_work_note_symlink, date+'.md')


    note_path = get_note_path(date)
    DATE = datetime.datetime.strptime(date, "%Y-%m-%d")

    if os.path.isfile(note_path):
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
                last_todo = ''.join(_last_todo_list)
                last_todo = re.sub('# TODAY', '# '+last_day, last_todo)
                break
        else:
            print('Cannot find todo of recent 30 days, init with empty todo')
            last_todo = ''

        
    with open(note_path, 'a+') as fout:
        msg = '''
{cal}

{date}'s work started, have a nice day ~
{last_todo}

        # TODAY:
            [ ] 

        # DONE:
            [x] 

@ start work record below


'''.format(
            date=date,
            cal=_cal(DATE.year, DATE.month, DATE.day),
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


class Colorama(object):

    @classmethod
    def red(cls, msg):
        return "\033[1;31m%s\033[0m" % (msg)

    @classmethod
    def blue(cls, msg):
        return "\033[36m%s\033[0m" % (msg)

    @classmethod
    def yellow(cls, msg):
        return "\033[1;33m\033[01m%s\033[0m" % (msg)

    @classmethod
    def blink(cls, msg):
        return "\033[5m%s\033[0m" % (msg)

    @classmethod
    def print(cls, msg, color, blink=False):
        if color == 'red':
            msg = cls.red(msg)
        if color == 'blue':
            msg = cls.blue(msg)
        if color == 'yellow':
            msg = cls.yellow(msg)
        if blink:
            return cls.blink(msg)
        return msg

    @classmethod
    def termgraph_color(cls, output, color):
        result = []
        output = output.split('\n')
        for o in output:
            if len(o) == 0:
                continue
            line_segs = o.split(' ')
            line = '{t} {l} {p}'.format(
                t=line_segs[0],
                l=cls.print(line_segs[1], color),
                p=line_segs[2])
            result.append(line)
        return '\n'.join(result)


def color_title(msg, color, length=36, delimiter='*'):
    length = float(length)
    l = float(len(msg))
    side = (length - l) / 2
    left = math.floor(side)
    right = math.ceil(side) 
    return delimiter * left, Colorama.print(msg, color), delimiter * right


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
    def delta(cls, d1, d2):
        d1 = datetime.datetime.strptime(d1, "%Y-%m-%d %H:%M:%S")
        d2 = datetime.datetime.strptime(d2, "%Y-%m-%d %H:%M:%S")
        return (d2-d1).seconds + (d2-d1).days * 86400

    @classmethod
    def format_delta(cls, delta, tomato_mode=True, with_check=False, blink=False, nap_notice=False):
        hour, minute, second, tomato = cls._format_delta(delta)
        if blink:
            tomato_icon = Colorama.blink('🍅 ') 
            check_icon = Colorama.blink('✅ ') 
        else:
            tomato_icon = '🍅 '
            check_icon = '✅ '
        if tomato_mode:
            return "{hour}:{minute}  =>  {tomato} {finish}{nap_notice}".format(
                hour=hour, 
                minute=minute, 
                tomato=tomato, 
                finish=tomato_icon if float(tomato) >= 1 and with_check else '   ',
                nap_notice=Colorama.print('\n [Good job! You need a nap now to relax your eyes ~ ]', 'yellow', blink=False) if nap_notice and float(tomato) >= 1 else '')
        else:
            return "{hour}:{minute} {enough_break}{nap_notice}".format(
                hour=hour, 
                minute=minute, 
                enough_break=check_icon if delta > nap_seconds and with_check else '   ',
                nap_notice=Colorama.print('\n [You have got enough rest, back to work now ~ ]', 'yellow', blink=False) if nap_notice is True else '')

    @classmethod
    def _format_delta(cls, delta):
        hour = '%02d' % int(delta / 3600)
        minute = '%02d' % (int((delta % 3600) / 60) if delta >= 0 else int((delta % 3600 - 3600) / 60))
        second = '%02d' % (int(delta % 60) if delta >=0 else int(delta % 60 - 60)) 
        tomato = '%.2f' % round(float(delta)/float(1800), 2)
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
    def timing_seg_distribute(cls, timing_seg):
        sh = cls.day_hour(timing_seg[0])
        eh = cls.day_hour(timing_seg[1])
        hl = cls.hour_list(timing_seg[0], timing_seg[1])
        if len(hl) == 1:
            return {sh: cls.delta(timing_seg[0], timing_seg[1])}
        else:
            result = dict()
            first_inter = datetime.datetime.strptime(hl[1], "%Y%m%d/%H")
            first = (first_inter - datetime.datetime.strptime(timing_seg[0], "%Y-%m-%d %H:%M:%S")).seconds
            last_inter = datetime.datetime.strptime(hl[-1], "%Y%m%d/%H")
            last = (datetime.datetime.strptime(timing_seg[1], "%Y-%m-%d %H:%M:%S") - last_inter).seconds
            for h in hl:
                if h == sh:
                    result[h] = first 
                elif h == eh:
                    result[h] = last
                else:
                    result[h] = 3600
            return result


class Timer():

    @classmethod
    def init(cls, printer):
        record_path, last_files, today_file_name, last_file_name, today_symlink, today, last_day, tmp_detail_data = cls.get_file_name()
        cls.record_path = record_path
        cls.last_files = last_files
        cls.today_file_name = today_file_name
        cls.last_file_name = last_file_name
        cls.today_symlink = today_symlink
        cls.today = today
        cls.last_day = last_day
        cls.tmp_detail_data = tmp_detail_data
        cls.printer = printer
        update_symlink(cls.last_file_name, cls.today_symlink)
        create_daily_note(cls.last_file_name.split('/')[-1])

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
        with open(cls.last_file_name) as fin:
            items = json.loads(fin.read())
            return False if len(items[-1]) == 1 else True

    @classmethod
    def get_paused_time(cls):
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
                pause_time = Date.now(delta)
                pause_time = pause_time if pause_time >= items[index][0] else items[index][0]
                items[index].append(Date.now(delta))
                break

        if got_pauser_point:
            with open(cls.last_file_name, 'w') as fout:
                fout.write(json.dumps(items, indent=4))
                msg = "{last_day}'s work paused... ".format(last_day=cls.last_day)
                notice(msg)
                cls.printer.add(msg)
        else:
            cls.printer.add('already paused')

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
            msg = "already in working status.".format(last_day=cls.last_day)
            notice(msg)
            cls.printer.add(msg)
            return

        with open(cls.last_file_name) as fin:
            items = json.loads(fin.read())
            
        with open(cls.last_file_name, 'w') as fout:
            items.append([Date.now()])
            fout.write(json.dumps(items, indent=4))
            msg = "proceed {last_day}'s work ...".format(last_day=cls.last_day)
            notice(msg)
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
        specific_date = cls.last_file_name if specific_date == Date.today() else os.path.join(cls.record_path, specific_date)
        with open(specific_date) as fin:
            cls.printer.add(*color_title('Tomato', 'yellow'))
            items = json.loads(fin.read())

            work_time = 0

            start_time = items[0][0]

            for item in items:
                if len(item) == 2:
                    work_time += Date.delta(item[0], item[1])

            last_item = items[len(items)-1]
            if len(last_item) == 1:
                tomato = Date.delta(item[0], Date.now())
                work_time += tomato
                msg = '*' + " Now Status: " + "Working "
                cls.printer.add(msg)
                cls.printer.add('*', "Current:", Colorama.yellow(Date.format_delta(tomato, with_check=True, blink=True, nap_notice=True)))
            else:
                msg = '*' + " Work Status: " + "paused"
                cls.printer.add(msg)
 
            notice(msg)
        cls.printer.print()

    @classmethod
    def records(cls, count=7):
        for d in cls.last_files[-count:]:
            cls.printer.add(d)
        cls.printer.print()

    @classmethod
    def show(cls, specific_date=None, verbose=False, output=None):
        _specific_date = cls.last_file_name if specific_date==Date.today() else os.path.join(cls.record_path, specific_date)
        _date = _specific_date.split('/')[-1]
        if not os.path.isfile(_specific_date):
            cls.printer.add(Colorama.red('No record.'))
            cls.printer.print()
            return 
        cls.printer.add(*color_title('Tomato History : {_date}, Weekday {weekday}'.format(_date=_date, weekday=Date.weekday(_date)), 'yellow', 68))
        cls.printer.add()
        cls.printer.add('   Num   |  Work Time Interval |        Tomato        |  Nap (5min)')
        cls.printer.add('-' * 70)
        previous_item = None
        with open(_specific_date) as fin:
            items = json.loads(fin.read())
            hl_sum = dict()
            work_time = 0
            for item in items:

                if previous_item and (items.index(item) > len(items) - 9 or verbose):
                    cls.printer.add(Date.format_delta(Date.delta(previous_item[1], item[0]), tomato_mode=False, with_check=False))

                previous_item = item

                if len(item) == 2:
                    if item[1] <= item[0]:
                        previous_item = None
                        continue
                    if items.index(item) > len(items) - 10 or verbose:
                        cls.printer.add('*  %03d:    ' % items.index(item), item[0][10:16], ' ~', item[1][10:16], '     ', Date.format_delta(Date.delta(item[0], item[1]), with_check=True), '     ', endl=False)
                    for seg, t in Date.timing_seg_distribute(item).items():
                        if seg not in hl_sum:
                            hl_sum[seg] = 0
                        hl_sum[seg] += t
                    work_time += Date.delta(item[0], item[1])
                elif items.index(item) == len(items) - 1:
                    for seg, t in Date.timing_seg_distribute([item[0], Date.now()]).items():
                        if seg not in hl_sum:
                            hl_sum[seg] = 0
                        hl_sum[seg] += t
                    work_time += Date.delta(item[0], Date.now())

            last_item = items[-1]
            if len(last_item) == 1:
                end_time = Date.now()
                tomato = Date.delta(last_item[0], Date.now())
                cls.printer.add('*  %03d:    ' % (len(items)-1), item[0][10:16], ' ~', '  ... ',  '     ', Date.format_delta(Date.delta(last_item[0], Date.now()), with_check=True), '    ', endl=False)
            else:
                end_time = last_item[1]

            with open(cls.tmp_detail_data, 'w+') as fout:
                lines = []
                for h in Date.hour_list(items[0][0], end_time):
                    if h in hl_sum:
                        min = '%.2f' % round(float(hl_sum[h])/float(60), 2)
                        lines.append(h + '    ' +  min + '\n')
                    else:
                        lines.append(h + '    ' +  str(0.00)+ '\n')
                fout.writelines(lines)
            cls.printer.add('\n')
            cls.printer.add(*color_title('Hour History (unit: Minute)', 'yellow', 68))
            cmd = '{termgraph} {tmp} --color cyan'.format(termgraph=termgraph_dir, tmp=cls.tmp_detail_data)
            result = check_output(cmd, shell=True, stderr=subprocess.STDOUT)
            cls.printer.add()
            cls.printer.add(Colorama.termgraph_color(result.decode()[:-1], 'blue'))
            cls.printer.add()

            start_time = items[0][0]
            wt = Date.delta(start_time, end_time)
            target_time = Date.now(datetime.timedelta(seconds=work_time_target_hours_one_day * 3600 - work_time))
            cls.printer.add(*color_title('Summary', 'yellow', 68))
            cls.printer.add()
            target_finish_rate = round(float(work_time) / float(work_time_target_hours_one_day * 3600) * 100)
            target_finish_rate_str = Colorama.print(str(target_finish_rate)+' %', 
                'blue' if target_finish_rate > 90 else 'yellow', 
                blink = False)
                # blink = False if target_finish_rate > 90 else True)
            cls.printer.add('*', 'Start Time: ', start_time[:16], '    Target Finish Rate: ', target_finish_rate_str)
            if specific_date == Date.today():
                cls.printer.add('*', 'Target Time:', target_time[:16], '✅ ' if target_time <= Date.now() else '   ', 'Work Rate Target:   ', Colorama.blue(str(round(float(work_time_target_hours_one_day * 3600) / float(work_time_target_hours_one_day * 3600 + wt - work_time) * 100))+' %'))
            else:
                cls.printer.add('*', 'Stop Time:  ', last_item[1][:16] if len(last_item) > 1 else last_item[0][:16])
            nap_rate = round(float(wt-work_time) / float(wt) * 100)
            nap_rate_str = str(nap_rate)+' %'
            cls.printer.add('*', 'All Time:   ', Date.format_delta(wt, with_check=False, blink=False, tomato_mode=True), 
                'Work Rate:', Colorama.blue(str(round(float(work_time) / float(wt) * 100))+' %'), 
                ', Nap Rate:', Colorama.blue(nap_rate_str) if nap_rate <= target_nap_rate else Colorama.print(nap_rate_str, 'red', blink=False))
 
            cls.printer.add('*', 'Work Time:  ', Date.format_delta(work_time, with_check=False, blink=False), 'CountDown:', Date.format_delta(Date.delta(Date.now(), target_time)))
            cls.printer.add('*', 'Nap Time:   ', Date.format_delta((wt-work_time), with_check=False, blink=False, tomato_mode=True))
            cls.printer.add()
            DATE = datetime.datetime.strptime(_date, "%Y-%m-%d")
            cls.printer.add(_cal(DATE.year, DATE.month, DATE.day, indent=' '*23))
            cls.printer.add()
            cls.printer.add(*color_title('Tomato Timer :  NowTime: '+Date.now(), 'yellow', 68, '-'))
            cls.printer.print()

                    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""
            [  Tomato  Timer  ] -- author : shenjiawei
    """)

    parser.add_argument('-st', '--start', dest='start', action='store_true', help="start one day's work.")
    parser.add_argument('-sp', '--stop', dest='stop', action='store_true', help="stop one day's work.")
    parser.add_argument('-p', '--pause', dest='pause', action='store_true', help='pause work and have a nap.')
    parser.add_argument('-c', '--proceed', dest='proceed', action='store_true', help='proceed(continue) work and stop nap.')
    parser.add_argument('-ck', '--check', dest='check', action='store_true', help="check status of now's work.")
    parser.add_argument('-s', '--show', dest='show', action='store_true', help='show work procedure of the day.')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', help='show procedure verbose, use with --show command.')
    parser.add_argument('-d', '--date', dest='date', type=str, default=Date.today(), help='''choose specific date. 
        eg : 2021-01-01 or -1 for delta -1 day from today, use with --check, --show, --calendar command.''')
    parser.add_argument('-r', '--records', dest='records', action='store_true', help='show workday records.')
    parser.add_argument('-cn', '--create_note', dest='create_note', action='store_true', help='create a note file of the day.')
    parser.add_argument('-cal', '--calendar', dest='calendar', action='store_true', help='show calendar of the day.')
    parser.add_argument('-clk', '--clock', dest='clock', action='store_true', help='run an Auto Tomato clock.')

    parameters = parser.parse_args()

    printer = PrintCache()

    try:
        parameters.date = int(parameters.date)
    except:
        pass

    if parameters.date is not None and isinstance(parameters.date, int):
        _delta_days = int(parameters.date)
        _date = datetime.datetime.strptime(Date.today(), "%Y-%m-%d") + datetime.timedelta(days=_delta_days)
        parameters.date = _date.strftime("%Y-%m-%d")
 
    if parameters.create_note:
        create_daily_note(parameters.date) 
        sys.exit(0) 
    elif parameters.calendar:
        DATE = datetime.datetime.strptime(parameters.date, "%Y-%m-%d")
        printer.add(_cal(DATE.year, DATE.month, DATE.day, colorful=True), endl=True)
        printer.print()
        sys.exit(0) 

    Timer.init(printer)
    if Timer.last_file_name is None:
        printer.add("Today's work is not started.")
        printer.print()

    if parameters.start:
        Timer.start()
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
        print(Colorama.print('Tomato Clock is Running...', 'yellow', blink=False))
        while True:
            try:
                idle_time = get_idle_time()
                if Timer.is_paused():
                    if Timer.get_paused_time() < 10:
                        continue
                    if idle_time < 5:
                        print('*', Date.now(), ': Status auto change to Working')
                        Timer.proceed()
                elif idle_time > nap_seconds:
                        print('*', Date.now(), ': Status auto change to Paused')
                        Timer.pause(datetime.timedelta(seconds=-idle_time))
                
                time.sleep(1)
            except KeyboardInterrupt:
                print()
                Timer.show(parameters.date, parameters.verbose)
                break
    else:
        print(Colorama.print('Use "python tomato.py -h" to get more information.', 'yellow'))

