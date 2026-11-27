# coding:utf-8

# ---------------------------------------------------------------------------------
# PM-Linux面板
# ---------------------------------------------------------------------------------
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------


from flask import Blueprint, render_template
from flask import request

from admin.user_login_check import panel_login_required

from utils.firewall import Firewall as MwFirewall
from utils.ssh_manage import SshManage
from utils.sys_user import SysUser

import core.mw as mw
import thisdb

blueprint = Blueprint('firewall', __name__, url_prefix='/firewall', template_folder='../../templates')
@blueprint.route('/index', endpoint='index')
@panel_login_required
def index():
    name = thisdb.getOption('template', default='default')
    return render_template('%s/firewall.html' % name)


# 防火墙列表
@blueprint.route('/get_list', endpoint='get_list', methods=['POST'])
@panel_login_required
def get_list():
    p = request.form.get('p', '1').strip()
    limit = request.form.get('limit', '10').strip()
    return MwFirewall.instance().getList(p,limit)

# 获取站点日志目录
@blueprint.route('/get_www_path', endpoint='get_www_path', methods=['POST'])
@panel_login_required
def get_www_path():
    path = mw.getLogsDir()
    return {'path': path}

# 获取 SSH/防火墙 概要信息
@blueprint.route('/get_ssh_info', endpoint='get_ssh_info', methods=['POST'])
@panel_login_required
def get_ssh_info():
    data = SshManage.instance().getInfo()
    data['firewall_status'] = False if mw.isAppleSystem() else MwFirewall.instance().getFwStatus()
    return data


# 切换ping开关(status=1 表示禁 ping, 与旧版接口兼容)
@blueprint.route('/set_ping', endpoint='set_ping', methods=['POST'])
@panel_login_required
def set_ping():
    if mw.isAppleSystem():
        return mw.returnData(True, '开发机不能设置!')
    status = request.form.get('status', '0').strip()
    return SshManage.instance().setPing(status != '1')

# 修改ssh端口
@blueprint.route('/set_ssh_port', endpoint='set_ssh_port', methods=['POST'])
@panel_login_required
def set_ssh_port():
    if mw.isAppleSystem():
        return mw.returnData(True, '开发机不能设置!')
    port = request.form.get('port', '').strip()
    return SshManage.instance().setPort(port)

# 添加放行端口
@blueprint.route('/add_accept_port', endpoint='add_accept_port', methods=['POST'])
@panel_login_required
def add_accept_port():
    port = request.form.get('port', '').strip()
    ps = request.form.get('ps', '').strip()
    protocol = request.form.get('protocol', '').strip()
    stype = request.form.get('type', '').strip()
    if stype == 'address':
        return MwFirewall.instance().addBlockIp(port, ps)
    return MwFirewall.instance().addAcceptPort(port, ps, stype, protocol=protocol)

# 删除放行端口
@blueprint.route('/del_accept_port', endpoint='del_accept_port', methods=['POST'])
@panel_login_required
def del_accept_port():
    port = request.form.get('port', '').strip()
    firewall_id = request.form.get('id', '').strip()
    protocol = request.form.get('protocol', '').strip()
    return MwFirewall.instance().delAcceptPort(firewall_id, port, protocol=protocol)


# 设置防火墙状态
@blueprint.route('/set_fw', endpoint='set_fw', methods=['POST'])
@panel_login_required
def set_fw():
    if mw.isAppleSystem():
        return mw.returnData(True, '开发机不能设置!')
    status = request.form.get('status', '1')
    return MwFirewall.instance().setFw(status)

# ------------------------------- SSH 管理 -------------------------------------

def _devGuard():
    if mw.isAppleSystem():
        return mw.returnData(False, '开发机不能设置!')
    return None


@blueprint.route('/ssh_set', endpoint='ssh_set', methods=['POST'])
@panel_login_required
def ssh_set():
    g = _devGuard()
    if g:
        return g
    key = request.form.get('key', '').strip()
    value = request.form.get('value', '').strip()
    force = request.form.get('force', '') == '1'
    return SshManage.instance().setOption(key, value, force=force)


@blueprint.route('/ssh_service', endpoint='ssh_service', methods=['POST'])
@panel_login_required
def ssh_service():
    g = _devGuard()
    if g:
        return g
    action = request.form.get('action', '').strip()
    r = SshManage.instance().service(action)
    if r['status']:
        mw.writeLog('SSH管理', {'start': '启动', 'stop': '停止', 'restart': '重启', 'reload': '重载'}.get(action, action) + ' SSH 服务')
    return r


@blueprint.route('/ssh_logs', endpoint='ssh_logs', methods=['POST'])
@panel_login_required
def ssh_logs():
    return SshManage.instance().getLogs(
        page=request.form.get('p', '1'),
        limit=request.form.get('limit', '20'),
        status=request.form.get('status', 'all'),
        search=request.form.get('search', ''),
    )


@blueprint.route('/ssh_stats', endpoint='ssh_stats', methods=['POST'])
@panel_login_required
def ssh_stats():
    return SshManage.instance().getStats()


@blueprint.route('/ssh_block_ip', endpoint='ssh_block_ip', methods=['POST'])
@panel_login_required
def ssh_block_ip():
    g = _devGuard()
    if g:
        return g
    return SshManage.instance().blockIp(request.form.get('ip', ''))


# 兼容旧版接口(status=1 表示禁止)
@blueprint.route('/set_ssh_root_status', endpoint='set_ssh_root_status', methods=['POST'])
@panel_login_required
def set_ssh_root_status():
    g = _devGuard()
    if g:
        return g
    value = 'no' if request.form.get('status', '1') == '1' else 'yes'
    return SshManage.instance().setOption('PermitRootLogin', value)


@blueprint.route('/set_ssh_pass_status', endpoint='set_ssh_pass_status', methods=['POST'])
@panel_login_required
def set_ssh_pass_status():
    g = _devGuard()
    if g:
        return g
    value = 'no' if request.form.get('status', '1') == '1' else 'yes'
    return SshManage.instance().setOption('PasswordAuthentication', value)


@blueprint.route('/set_ssh_pubkey_status', endpoint='set_ssh_pubkey_status', methods=['POST'])
@panel_login_required
def set_ssh_pubkey_status():
    g = _devGuard()
    if g:
        return g
    value = 'no' if request.form.get('status', '1') == '1' else 'yes'
    return SshManage.instance().setOption('PubkeyAuthentication', value)


# ------------------------------- 系统账号 -------------------------------------

@blueprint.route('/user_list', endpoint='user_list', methods=['POST'])
@panel_login_required
def user_list():
    return SysUser.instance().getList(show_system=request.form.get('system', '') == '1')


@blueprint.route('/user_add', endpoint='user_add', methods=['POST'])
@panel_login_required
def user_add():
    g = _devGuard()
    if g:
        return g
    f = request.form
    return SysUser.instance().addUser(f.get('name', ''), f.get('password', ''),
                                      shell=f.get('shell', '/bin/bash'),
                                      sudo=f.get('sudo', '') == '1', comment=f.get('comment', ''))


@blueprint.route('/user_passwd', endpoint='user_passwd', methods=['POST'])
@panel_login_required
def user_passwd():
    g = _devGuard()
    if g:
        return g
    return SysUser.instance().setPassword(request.form.get('name', ''), request.form.get('password', ''))


@blueprint.route('/user_lock', endpoint='user_lock', methods=['POST'])
@panel_login_required
def user_lock():
    g = _devGuard()
    if g:
        return g
    return SysUser.instance().setLock(request.form.get('name', ''), request.form.get('lock', '') == '1')


@blueprint.route('/user_shell', endpoint='user_shell', methods=['POST'])
@panel_login_required
def user_shell():
    g = _devGuard()
    if g:
        return g
    return SysUser.instance().setShell(request.form.get('name', ''), request.form.get('shell', ''))


@blueprint.route('/user_sudo', endpoint='user_sudo', methods=['POST'])
@panel_login_required
def user_sudo():
    g = _devGuard()
    if g:
        return g
    return SysUser.instance().setSudo(request.form.get('name', ''), request.form.get('sudo', '') == '1')


@blueprint.route('/user_del', endpoint='user_del', methods=['POST'])
@panel_login_required
def user_del():
    g = _devGuard()
    if g:
        return g
    return SysUser.instance().delUser(request.form.get('name', ''), request.form.get('remove_home', '') == '1')


@blueprint.route('/user_keys', endpoint='user_keys', methods=['POST'])
@panel_login_required
def user_keys():
    return SysUser.instance().listKeys(request.form.get('name', ''))


@blueprint.route('/user_key_add', endpoint='user_key_add', methods=['POST'])
@panel_login_required
def user_key_add():
    g = _devGuard()
    if g:
        return g
    return SysUser.instance().addKey(request.form.get('name', ''), request.form.get('key', ''))


@blueprint.route('/user_key_del', endpoint='user_key_del', methods=['POST'])
@panel_login_required
def user_key_del():
    g = _devGuard()
    if g:
        return g
    return SysUser.instance().delKey(request.form.get('name', ''), request.form.get('fingerprint', ''))


@blueprint.route('/user_key_gen', endpoint='user_key_gen', methods=['POST'])
@panel_login_required
def user_key_gen():
    g = _devGuard()
    if g:
        return g
    return SysUser.instance().genKey(request.form.get('name', ''), request.form.get('type', 'ed25519'),
                                     request.form.get('passphrase', ''))
