# tomato

python command line tool of Tomato work timer. FOR MAC ONLY .

usage:
tomato.py [-h] [-st] [-sp] [-nt] [-p] [-c] [-ck] [-s] [-v] [-d DATE] [-r] [-cn] [-cal] [-clk] [-bw] [-pf PRINT_TO_FILE]

[ Tomato Timer ] -- author : shenjiawei

optional arguments:
-h, --help            show this help message and exit
-dg, --debug          debug code
-st, --start          start one day's work.
-sp, --stop           stop one day's work.
-nt, --new_tomato     start a new tomato period by pause and proceed.
-p, --pause           pause work and have a nap.
-c, --proceed         proceed(continue) work and stop nap.
-ck, --check          check status of now's work.
-s, --show            show work procedure of the day. [default]
-v, --verbose         show procedure verbose, use with --show command.
-vv, --verbose_vertical
show calendar verbose with vertical format, use with --calendar command.
-vq, --verbose_quarter
show calendar verbose with quarter range, use with --calendar command.
-d DATE, --date DATE  choose specific date. eg : 2021-01-01 and -1 for delta -1 day from today, must use with other commands.
-dc DATE_CALCULATE, --date_calculate DATE_CALCULATE
Calculate day offset. eg : 2021-01-01 ("now" is short for today) to get interval from the date and -1 for delta -1 day from the date.
-r, --records         show workday records.
-cn, --create_note    create a note file of the day.
-an, --archive_note   archive_note note files of the days.
-anc ARCHIVE_NOTE_COUNT, --archive_note_count ARCHIVE_NOTE_COUNT
archive_note note files counts
-anp ARCHIVE_NOTE_PATH, --archive_note_path ARCHIVE_NOTE_PATH
archive_note note files to the path
-cal, --calendar      show calendar of the day.
-clk, --clock         run an Auto Tomato clock.
-b, --black_and_white
print with black and white.
-pf PRINT_TO_FILE, --print_to_file PRINT_TO_FILE
print output to the local file

# TODO

* 自动创建文件后, 设置文件的归属
