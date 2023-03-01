import os


'''
Use conmmand to get users info:
command
    dscacheutil -q user

output : 
    name: jiawei
    password: ********
    uid: 501
    gid: 20
    dir: /Users/jiawei
    shell: /bin/zsh
    gecos: jiawei
'''

def get_user_infos(user_name):
    user_infos = []
    users = get_all_users()
    for user in users:
        if user['name'] == user_name:
            user_infos.append(user)
    return user_infos


def get_all_users():
    users = []
    _users = os.popen('dscacheutil -q user').read()
    _users = _users.split('\n\n')
    for user in _users:
        if not user.strip():
            continue
        _user_dict_items = user.split('\n')
        _user_dict = {item.split(':')[0].strip():item.split(':')[1].strip() for item in _user_dict_items}
        users.append(_user_dict)
    return users

        
def get_user_id(user_name=''):
    user_id = os.popen('id -u {user_name}'.format(user_name=user_name)).read()
    return user_id.strip()


def get_user_name():
    user_name = os.popen('whoami').read()
    return user_name.strip()


if __name__ == '__main__':
    print(get_user_name())
    pass
