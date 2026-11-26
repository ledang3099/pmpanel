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
@blueprint.route('/update_server', endpoint='update_server')
@panel_login_required
def update_server():
    panel_type = request.args.get('type', 'check')
    version = request.args.get('version', '')
    return sys.updateServer(panel_type, version)



