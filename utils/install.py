#coding=utf-8
#Author: shenjiawei


import os, errno
from utils.user_info import get_user_name
from utils.init_template import install_files

def _install_file(path, file_name, file_content):
    with open(os.path.join(path, file_name), 'w') as fout:
        fout.write(file_content)


def _mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise
    return path


def _get_bin_path(user_name):
    tomato_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bin_path = os.path.join(tomato_path, user_name)
    return _mkdir_p(bin_path)


def install(user_name=None):
    user_name = get_user_name() if user_name is None else user_name
    bin_path = _get_bin_path(user_name)
    for f in install_files:
        name = f['name'].format(user_name=user_name)
        content = f['content'].format(user_name=user_name)
        _install_file(bin_path, name, content)
    return 


if __name__ == "__main__":
    print(install())
