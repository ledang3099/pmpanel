# coding:utf-8

# ---------------------------------------------------------------------------------
# PM-Linux面板
# ---------------------------------------------------------------------------------
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------

# 终端栏目: 本机终端(多标签) + 常用命令; 已安装 SSH终端(webssh)插件时可管理远程服务器

import os
import json

from flask import Blueprint, render_template
from flask import request

from admin.user_login_check import panel_login_required

import core.mw as mw
import thisdb

blueprint = Blueprint('terminal', __name__, url_prefix='/terminal', template_folder='../../templates')

MAX_COMMANDS = 100


@blueprint.route('/index', endpoint='index')
@panel_login_required
def index():
    name = thisdb.getOption('template', default='default')
    return render_template('%s/terminal.html' % name)


@blueprint.route('/info', endpoint='info', methods=['POST'])
@panel_login_required
def info():
    webssh = os.path.exists(mw.getServerDir() + '/webssh')
    return mw.returnData(True, 'OK', {'webssh': webssh})


def _commands():
    data = thisdb.getOptionByJson('terminal_commands', default=[])
    return data if isinstance(data, list) else []


@blueprint.route('/commands', endpoint='commands', methods=['POST'])
@panel_login_required
def commands():
    return mw.returnData(True, 'OK', _commands())


@blueprint.route('/command_save', endpoint='command_save', methods=['POST'])
@panel_login_required
def command_save():
    name = request.form.get('name', '').strip()
    cmd = request.form.get('cmd', '').rstrip()
    idx = request.form.get('index', '')
    if not name or len(name) > 50:
        return mw.returnData(False, '名称不能为空且不超过 50 字')
    if not cmd or len(cmd) > 4000:
        return mw.returnData(False, '命令不能为空且不超过 4000 字')
    items = _commands()
    if idx != '':
        try:
            items[int(idx)] = {'name': name, 'cmd': cmd}
        except (ValueError, IndexError):
            return mw.returnData(False, '参数错误')
    else:
        if len(items) >= MAX_COMMANDS:
            return mw.returnData(False, '最多保存 %d 条常用命令' % MAX_COMMANDS)
        items.append({'name': name, 'cmd': cmd})
    thisdb.setOption('terminal_commands', json.dumps(items, ensure_ascii=False))
    return mw.returnData(True, '已保存')


@blueprint.route('/command_del', endpoint='command_del', methods=['POST'])
@panel_login_required
def command_del():
    items = _commands()
    try:
        items.pop(int(request.form.get('index', '')))
    except (ValueError, IndexError):
        return mw.returnData(False, '参数错误')
    thisdb.setOption('terminal_commands', json.dumps(items, ensure_ascii=False))
    return mw.returnData(True, '已删除')


# 页面关闭时浏览器通过 sendBeacon 调用, 立即结束该页面打开的终端
# (长轮询模式下服务端要等心跳超时才能感知断开)
@blueprint.route('/close', endpoint='close', methods=['POST'])
@panel_login_required
def close():
    sid = request.form.get('sid', '')
    if sid:
        from utils.ssh.pty_terminal import PtyTerminal
        PtyTerminal.instance().closeClient(sid)
    return mw.returnData(True, 'OK')
