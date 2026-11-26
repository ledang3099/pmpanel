# coding:utf-8

# ---------------------------------------------------------------------------------
# PM-Linux面板
# ---------------------------------------------------------------------------------
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------

import time

from admin import session
import thisdb

def isLogined():
    if 'login' in session  and session['login'] == True and 'username' in session:
        username = session['username']
        info = thisdb.getUserByName(username)
        if info is None:
            return False

        # print(userInfo)
        if info['name'] != session['username']:
            return False

        now_time = int(time.time())

        if 'overdue' in session and now_time > session['overdue']:
            # 会话已过期: 清除会话 (旧版在此处续期, 导致过期会话下一次请求又变为有效)
            session.clear()
            return False

        if 'tmp_login_expire' in session and now_time > int(session['tmp_login_expire']):
            session.clear()
            return False
        return True