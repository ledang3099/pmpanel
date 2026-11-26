# coding:utf-8

# ---------------------------------------------------------------------------------
# PM-Linux面板
# ---------------------------------------------------------------------------------
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------

import re
import json
import os
import time

from flask import Blueprint, render_template
from flask import request

from admin import session
from admin.user_login_check import panel_login_required, panel_not_temp_login

import core.mw as mw
import utils.config as utils_config

from .setting import blueprint
import thisdb

# 设置API
@blueprint.route('/set_panel_api', endpoint='set_panel_api', methods=['POST'])
@panel_login_required
@panel_not_temp_login
def set_panel_api():
    panel_api = thisdb.getOptionByJson('panel_api', default={'open':False})
    if not panel_api['open']:
        panel_api['open'] = True
        thisdb.setOption('panel_api', json.dumps(panel_api))
        return mw.returnData(True, '开启API成功!')
    else:
        panel_api['open'] = False
        thisdb.setOption('panel_api', json.dumps(panel_api))
        return mw.returnData(True, '关闭API成功!')


# 获取APP列表
@blueprint.route('/get_app_list', endpoint='get_app_list', methods=['POST'])
@panel_login_required
@panel_not_temp_login
def get_app_list():
    limit = request.form.get('limit', '5').strip()
    page = request.form.get('page', '1').strip()
    tojs = request.form.get('tojs', 'getAppList').strip()

    info = thisdb.getAppList(page=int(page),size=int(limit))
    data = {}
    data['data'] = info['list']
    data['page'] = mw.getPage({'count':info['count'],'tojs':tojs,'p':page,'row':limit})
    return data


# 添加APP列表
@blueprint.route('/add_app', endpoint='add_app', methods=['POST'])
@panel_login_required
@panel_not_temp_login
def add_app():
    app_id = request.form.get('app_id', '').strip()
    app_secret = request.form.get('app_secret', '1').strip()
    limit_addr = request.form.get('limit_addr', '').strip()
    if limit_addr == '':
        return mw.returnData(False, 'IP限制不能为空!')
    if app_id == '' or not re.match(r'^[A-Za-z0-9_\-]{6,64}$', app_id):
        return mw.returnData(False, 'APP ID格式不正确(6-64位字母数字)!')
    if len(app_secret) < 16:
        return mw.returnData(False, 'APP密钥长度不能少于16位!')
    if thisdb.getAppByAppId(app_id) is not None:
        return mw.returnData(False, 'APP ID已存在!')

    rid = thisdb.addApp(app_id,app_secret,limit_addr)
    if rid > 0:
        return mw.returnData(True, '添加成功!')
    return mw.returnData(False, '添加失败!')

# 添加APP列表
@blueprint.route('/toggle_app_status', endpoint='toggle_app_status', methods=['POST'])
@panel_login_required
@panel_not_temp_login
def toggle_app_status():
    aid = request.form.get('id', '').strip()
    rid = thisdb.toggleAppStatus(aid)
    if rid > 0:
        return mw.returnData(True, '切换成功!')
    return mw.returnData(False, '切换失败!')


# 获取APP列表
@blueprint.route('/delete_app', endpoint='delete_app', methods=['POST'])
@panel_login_required
@panel_not_temp_login
def delete_app():
    aid = request.form.get('id', '').strip()
    rid = thisdb.deleteAppById(aid)
    if rid > 0:
        return mw.returnData(True, '删除成功!')
    return mw.returnData(False, '删除失败!')
