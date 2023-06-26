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

if __name__ == "__main__":
    main()
