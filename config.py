#coding=utf-8

nap_seconds = 300 # 5min
user_name = 'jiawei' # Mac user name
termgraph_dir = '/Users/jiawei/workspace/environ/py3/bin/termgraph'
work_time_target_hours_one_day = 8.5
target_nap_rate = 0.34
auto_cut_cross_day = True
auto_cut_cross_day_interval_hours = 5
daily_work_note_dir = '/Users/jiawei/nasWorkspace/fileCab/notes/DailyWork'
copy_daily_work_note_symlink = '/Users/jiawei/nasWorkspace/fileCab/notes/HotLinks'
schedule = {
    """osascript -e 'display alert "定期检查 Lark 消息" message "每隔 30min 打开 lark 一次, 检查通知消息"';open /Applications/Lark.app""":1800
}

