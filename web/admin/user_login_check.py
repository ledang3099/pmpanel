# coding:utf-8

# ---------------------------------------------------------------------------------
# PM-Linux面板
# ---------------------------------------------------------------------------------
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------


from flask import render_template
from flask import Response
from flask import request

from functools import wraps

from admin import session
from admin.common import isLogined

import core.mw as mw
import utils.security as security
import thisdb

def panel_login_required(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        # 面板API调用检查
        app_id = request.headers.get('App-Id','')
        app_secret = request.headers.get('App-Secret','')
        if app_id != '' and app_secret != '':
            panel_api = thisdb.getOptionByJson('panel_api', default={"open":False})
            if not panel_api.get('open', False):
                return Response(status=404)
            info = thisdb.getAppByAppId(app_id)
            if info is None or int(info.get('status', 0)) != 1:
                return Response(status=404)
            if not security.safe_equals(app_secret, info['app_secret']):
                return Response(status=404)
            if not security.ip_in_whitelist(mw.getClientIp(), info.get('white_list', '')):
                return Response(status=403)
            return func(*args, **kwargs)

        if not isLogined():
            unauthorized_status = thisdb.getOption('unauthorized_status')
            if unauthorized_status == '0':
                return render_template('default/path.html')
            return Response(status=int(unauthorized_status))

        return func(*args, **kwargs)
    return wrapper


def panel_not_temp_login(func):
    '''
    临时登录(授权给他人的一次性访问)不允许执行的敏感操作:
    修改账号密码、管理API密钥/临时登录/两步验证等
    '''
    @wraps(func)
    def wrapper(*args, **kwargs):
        if session.get('tmp_login', False):
            return mw.returnData(False, '临时登录用户无权执行此操作!')
        return func(*args, **kwargs)
    return wrapper
