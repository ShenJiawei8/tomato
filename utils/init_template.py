file_content_plist = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{user_name}.github.tomato</string>
    <key>KeepAlive</key>
    <true/>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/{user_name}/workspace/github/tomato/bin/run.sh</string>
    </array>
    <key>UserName</key>
    <string>{user_name}</string>
    <key>GroupName</key>
    <string>staff</string>
</dict>
</plist>"""

file_content_config = """config#coding=utf-8
nap_seconds = 300 # 5min
user_name = '{user_name}' # Mac user name
work_time_target_hours_one_day = 8.5
target_nap_rate = 0.34
auto_cut_cross_day = True
auto_cut_cross_day_interval_hours = 5 # 0 means go to a new day work just after 00:00 
daily_work_note_dir = '{bin_path}/WorkRecords/DailyWorkNotes'
daily_work_time_records_dir = '{bin_path}/WorkRecords/WorkTimeRecords'
copy_daily_work_note_symlink = '{bin_ath}/WorkRecords/QuickLinks'
use_notice = False"""

file_content_install = """# refer to : https://babodee.wordpress.com/2016/04/09/launchctl-2-0-syntax/

sudo cp /Users/{user_name}/workspace/github/tomato/bin/{user_name}.tomato.plist /Library/LaunchDaemons/{user_name}.tomato.plist
# launchctl bootout /Library/LaunchDaemons/{user_name}.tomato.plist
launchctl bootstrap /Library/LaunchDaemons/{user_name}.tomato.plist
launchctl list {user_name}.github.tomato"""

file_content_run = """/usr/bin/python3 /Users/{user_name}/workspace/github/tomato/tomato.py -clk >> /Users/{user_name}/workspace/github/tomato/bin/log
# launchctl load /Library/LaunchDaemons/{user_name}.tomato.plist"""

file_content_uninstall = """launchctl unload /Library/LaunchDaemons/{user_name}.tomato.plist
sudo rm -f /Library/LaunchDaemons/{user_name}.tomato.plist"""

install_files = [
    {
        "name": "{user_name}.tomato.plist",
        "content": file_content_plist,
    },
    {
        "name": "config.py",
        "content": file_content_config,
    },
    {
        "name": "install.sh",
        "content": file_content_install,
    },
    {
        "name": "run.sh",
        "content": file_content_run,
    }
]
