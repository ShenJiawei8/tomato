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
from utils.user_info import get_user_infos, get_user_name
from utils.install import install
from icalendar import Calendar, Event
try:
    from bin.config import nap_seconds, auto_cut_cross_day, \
        auto_cut_cross_day_interval_hours, work_time_target_hours_one_day, \
        daily_work_note_dir, target_nap_rate, copy_daily_work_note_symlink, \
        user_name, daily_work_time_records_dir, use_notice
except:
    print("need install first")


def main():
    username = get_user_name()
    print(username)
    print(nap_seconds, auto_cut_cross_day, \
    auto_cut_cross_day_interval_hours, work_time_target_hours_one_day, \
    daily_work_note_dir, target_nap_rate, copy_daily_work_note_symlink, \
    user_name, daily_work_time_records_dir, use_notice
)

def read_calendar():
    holidays = []
    work_days = []
    with open('cn_zh.ics', 'rb') as fin:
        cal = Calendar.from_ical(fin.read())
        
        for component in cal.walk():
            if component.name == "VEVENT":
                summary = component.get('SUMMARY')
                start = component.get('DTSTART').dt
                end = component.get('DTEND').dt
                description = component.get('DESCRIPTION')
                location = component.get('LOCATION')

                if "班" in summary :
                    work_days.append([start, end])

                if "休" not in summary:
                    holidays.append([start, end])
        
                continue

    return holidays, work_days

def is_holiday(date, holidays=[], work_days=[])
    if len(holidays) == 0 or len(work_days) == 0:
        holidays, work_days = read_calendar()



if __name__ == "__main__":
    pass