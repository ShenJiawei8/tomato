# tomato

python command line tool of Tomato work timer. FOR MAC ONLY .

usage:
tomato.py [-h] [-st] [-sp] [-nt] [-p] [-c] [-ck] [-s] [-v] [-d DATE] [-r] [-cn] [-cal] [-clk] [-bw] [-pf PRINT_TO_FILE]

[ Tomato Timer ] -- author : shenjiawei

optional arguments:
-h, --help show this help message and exit
-st, --start start one day's work.
-sp, --stop stop one day's work.
-nt, --new_tomato start a new tomato.
-p, --pause pause work and have a nap.
-c, --proceed proceed(continue) work and stop nap.
-ck, --check check status of now's work.
-s, --show show work procedure of the day.
-v, --verbose show procedure verbose, use with --show command.
-d DATE, --date DATE choose specific date. eg : 2021-01-01 or -1 for delta -1 day from today, use with --check, --show,
--calendar command.
-r, --records show workday records.
-cn, --create_note create a note file of the day.
-cal, --calendar show calendar of the day.
-clk, --clock run an Auto Tomato clock.
-bw, --black_and_white
print with black and white.
-pf PRINT_TO_FILE, --print_to_file PRINT_TO_FILE
print output to the local file

# TODO

* 自动创建文件后, 设置文件的归属
