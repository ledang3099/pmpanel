# coding:utf-8

# ---------------------------------------------------------------------------------
# PM-Linux面板
# ---------------------------------------------------------------------------------
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------

import json

from flask import Blueprint, render_template
from flask import request

from admin.user_login_check import panel_login_required

from utils.database import Database
from utils.redis_manage import RedisManage

import core.mw as mw
import thisdb

blueprint = Blueprint('database', __name__, url_prefix='/database', template_folder='../../templates')


@blueprint.route('/index', endpoint='index')
@panel_login_required
def index():
    name = thisdb.getOption('template', default='default')
    return render_template('%s/database.html' % name)


@blueprint.route('/info', endpoint='info', methods=['POST'])
@panel_login_required
def info():
    return Database.instance().getInfo()


# 统一调用数据库插件(插件名/函数均为白名单, 参数逐项校验)
@blueprint.route('/call', endpoint='call', methods=['POST'])
@panel_login_required
def call():
    name = request.form.get('name', '')
    func = request.form.get('func', '')
    try:
        args = json.loads(request.form.get('args', '{}') or '{}')
    except ValueError:
        return mw.returnData(False, '参数格式不正确')
    return Database.instance().call(name, func, args)


@blueprint.route('/root_pwd', endpoint='root_pwd', methods=['POST'])
@panel_login_required
def root_pwd():
    return Database.instance().rootPassword(request.form.get('name', ''))


@blueprint.route('/import_dir', endpoint='import_dir', methods=['POST'])
@panel_login_required
def import_dir():
    return mw.returnData(True, 'OK', Database.instance().importDir())


# ------------------------------- Redis -------------------------------------------

def _rname():
    return request.form.get('name', 'redis')


@blueprint.route('/redis_info', endpoint='redis_info', methods=['POST'])
@panel_login_required
def redis_info():
    return RedisManage.instance().getInfo(_rname())


@blueprint.route('/redis_scan', endpoint='redis_scan', methods=['POST'])
@panel_login_required
def redis_scan():
    f = request.form
    return RedisManage.instance().scan(_rname(), f.get('db', '0'), f.get('pattern', '*'), f.get('cursor', '0'), f.get('count', '50'))


@blueprint.route('/redis_get', endpoint='redis_get', methods=['POST'])
@panel_login_required
def redis_get():
    return RedisManage.instance().getKey(_rname(), request.form.get('db', '0'), request.form.get('key', ''))


@blueprint.route('/redis_set', endpoint='redis_set', methods=['POST'])
@panel_login_required
def redis_set():
    f = request.form
    return RedisManage.instance().setKey(_rname(), f.get('db', '0'), f.get('key', ''), f.get('value', ''),
                                         ttl=f.get('ttl', '-1'), key_type=f.get('type', 'string'), field=f.get('field', ''))


@blueprint.route('/redis_ttl', endpoint='redis_ttl', methods=['POST'])
@panel_login_required
def redis_ttl():
    f = request.form
    return RedisManage.instance().setTtl(_rname(), f.get('db', '0'), f.get('key', ''), f.get('ttl', '-1'))


@blueprint.route('/redis_del', endpoint='redis_del', methods=['POST'])
@panel_login_required
def redis_del():
    try:
        keys = json.loads(request.form.get('keys', '[]'))
    except ValueError:
        return mw.returnData(False, '参数格式不正确')
    return RedisManage.instance().delKeys(_rname(), request.form.get('db', '0'), keys)


@blueprint.route('/redis_flush', endpoint='redis_flush', methods=['POST'])
@panel_login_required
def redis_flush():
    return RedisManage.instance().flushDb(_rname(), request.form.get('db', '0'))
