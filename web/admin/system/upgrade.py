# coding:utf-8

# ---------------------------------------------------------------------------------
# PM-Linux面板
# ---------------------------------------------------------------------------------
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------


from flask import Blueprint, render_template
from flask import request

from admin.user_login_check import panel_login_required

import core.mw as mw
import utils.system as sys

from .system import blueprint

# 升级检测
@blueprint.route('/update_server', endpoint='update_server', methods=['GET', 'POST'])
@panel_login_required
def update_server():
    panel_type = request.values.get('type', 'check')
    version = request.values.get('version', '')
    # 执行更新会修改面板文件, 只接受 POST(受 CSRF 来源校验保护)
    if panel_type == 'update' and request.method != 'POST':
        return mw.returnData(False, '请求方式不正确')
    return sys.updateServer(panel_type, version)



