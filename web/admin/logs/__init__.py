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
import utils.adult_log as adult_log
import thisdb

# 日志页面
blueprint = Blueprint('logs', __name__, url_prefix='/logs', template_folder='../../templates')
@blueprint.route('/index', endpoint='index')
@panel_login_required
def index():
    name = thisdb.getOption('template', default='default')
    return render_template('%s/logs.html' % name)

# 日志列表
@blueprint.route('/get_log_list', endpoint='get_log_list', methods=['POST'])
@panel_login_required
def get_log_list():
    p = request.form.get('p', '1').strip()
    size = request.form.get('limit', '10').strip()
    search = request.form.get('search', '').strip()

    info = thisdb.getLogsList(page=int(p),size=int(size), search=search)

    data = {}
    data['data'] = info['list']
    data['page'] = mw.getPage({'count':info['count'],'tojs':'getLogs','p':p,'row':size})
    return data

# 日志清空
@blueprint.route('/del_panel_logs', endpoint='del_panel_logs', methods=['POST'])
@panel_login_required
def del_panel_logs():
    thisdb.clearLog()
    mw.writeLog('面板设置', '面板操作日志已清空!')
    return mw.returnData(True, '面板操作日志已清空!')

# 系统审计日志列表
@blueprint.route('/get_audit_logs_files', endpoint='get_audit_logs_files', methods=['POST'])
@panel_login_required
def get_audit_logs_files():
    logs_file = adult_log.getAuditLogsFiles()
    return mw.returnData(True, 'ok', logs_file)

# 系统审计日志列表
@blueprint.route('/get_audit_file', endpoint='get_audit_file', methods=['POST'])
@panel_login_required
def get_audit_file():
    name = request.form.get('log_name', '').strip()
    return adult_log.getAuditLogsName(name)











# ------------------------------- 日志中心(新版) ---------------------------------

from flask import Response
from utils.log_center import LogCenter


def _lines():
    return request.form.get('lines', '200')


@blueprint.route('/overview', endpoint='overview', methods=['POST'])
@panel_login_required
def overview():
    return LogCenter.instance().overview()


@blueprint.route('/operation', endpoint='operation', methods=['POST'])
@panel_login_required
def operation():
    f = request.form
    return LogCenter.instance().operationLogs(f.get('p', '1'), f.get('limit', '20'), f.get('search', '').strip(), f.get('type', '').strip())


@blueprint.route('/operation_types', endpoint='operation_types', methods=['POST'])
@panel_login_required
def operation_types():
    return LogCenter.instance().logTypes()


@blueprint.route('/operation_export', endpoint='operation_export', methods=['GET'])
@panel_login_required
def operation_export():
    data = LogCenter.instance().exportOperationLogs(request.args.get('search', '').strip(), request.args.get('type', '').strip())
    return Response(data, mimetype='text/csv; charset=utf-8',
                    headers={'Content-Disposition': 'attachment; filename=panel_logs_%s.csv' % mw.formatDate('%Y%m%d%H%M%S')})


@blueprint.route('/panel_run', endpoint='panel_run', methods=['POST'])
@panel_login_required
def panel_run():
    return LogCenter.instance().panelRun(request.form.get('name', 'panel_error'), _lines(), request.form.get('search', ''))


@blueprint.route('/panel_run_clear', endpoint='panel_run_clear', methods=['POST'])
@panel_login_required
def panel_run_clear():
    return LogCenter.instance().clearPanelRun(request.form.get('name', ''))


@blueprint.route('/site_list', endpoint='site_list', methods=['POST'])
@panel_login_required
def site_list():
    return LogCenter.instance().siteList()


@blueprint.route('/site_log', endpoint='site_log', methods=['POST'])
@panel_login_required
def site_log():
    f = request.form
    return LogCenter.instance().siteLog(f.get('name', ''), f.get('type', 'access'), _lines(), f.get('search', ''))


@blueprint.route('/site_log_clear', endpoint='site_log_clear', methods=['POST'])
@panel_login_required
def site_log_clear():
    return LogCenter.instance().clearSiteLog(request.form.get('name', ''), request.form.get('type', 'access'))


@blueprint.route('/cron_list', endpoint='cron_list', methods=['POST'])
@panel_login_required
def cron_list():
    return LogCenter.instance().cronList()


@blueprint.route('/cron_log', endpoint='cron_log', methods=['POST'])
@panel_login_required
def cron_log():
    return LogCenter.instance().cronLog(request.form.get('id', ''), _lines(), request.form.get('search', ''))


@blueprint.route('/cron_log_clear', endpoint='cron_log_clear', methods=['POST'])
@panel_login_required
def cron_log_clear():
    return LogCenter.instance().clearCronLog(request.form.get('id', ''))


@blueprint.route('/soft_list', endpoint='soft_list', methods=['POST'])
@panel_login_required
def soft_list():
    return LogCenter.instance().softList()


@blueprint.route('/soft_log', endpoint='soft_log', methods=['POST'])
@panel_login_required
def soft_log():
    return LogCenter.instance().softLog(request.form.get('key', ''), _lines(), request.form.get('search', ''))


@blueprint.route('/system_list', endpoint='system_list', methods=['POST'])
@panel_login_required
def system_list():
    return mw.returnData(True, 'OK', LogCenter.instance().systemFiles())


@blueprint.route('/system_log', endpoint='system_log', methods=['POST'])
@panel_login_required
def system_log():
    return LogCenter.instance().systemLog(request.form.get('name', ''), _lines(), request.form.get('search', ''))


@blueprint.route('/clean_site_logs', endpoint='clean_site_logs', methods=['POST'])
@panel_login_required
def clean_site_logs():
    return LogCenter.instance().cleanSiteLogs()


@blueprint.route('/clean_cron_logs', endpoint='clean_cron_logs', methods=['POST'])
@panel_login_required
def clean_cron_logs():
    return LogCenter.instance().cleanCronLogs()
