# coding:utf-8

# ---------------------------------------------------------------------------------
# PM-Linux面板
# ---------------------------------------------------------------------------------
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------

import os
import sys
import json
import time
import uuid
import logging

from datetime import timedelta

from flask import Flask
from flask import request
from flask import redirect
from flask import Response
from flask import Flask, abort, current_app, session, url_for
from flask import Blueprint, render_template
from flask import render_template_string
from flask_compress import Compress

from flask_socketio import SocketIO, emit, send

from flask_caching import Cache
from werkzeug.local import LocalProxy


from admin.common import isLogined

import core.mw as mw
import config
import utils.config as utils_config
import thisdb

# 初始化db
from admin import setup
setup.init()

app = Flask(__name__, template_folder='templates/default')


# curl --compressed -I "http://127.0.0.1:44010/" -H "Accept-Encoding: br" --write-out "%{json}"
app.config["COMPRESS_ALGORITHM"] = ["br", "zstd", "gzip", "deflate"]
app.config["COMPRESS_LEVEL"] = 9  # 最高压缩级别
app.config["COMPRESS_MIN_SIZE"] = 500  # 最小压缩大小
Compress(app)

# 缓存配置
# 文件缓存: gunicorn 多个worker之间共享(登录失败计数等), 内存缓存会被每个worker各算一份
_cache_dir = mw.getPanelDataDir() + '/cache'
if not os.path.exists(_cache_dir):
    os.makedirs(_cache_dir, mode=0o700)
_cache_cfg = {'CACHE_TYPE': 'FileSystemCache', 'CACHE_DIR': _cache_dir, 'CACHE_THRESHOLD': 2000}
cache = Cache(config=_cache_cfg)
cache.init_app(app, config=_cache_cfg)

# 静态文件配置
app.static_folder = "../static"
app.static_url_path = "/static"
app.jinja_env.trim_blocks = True

# from whitenoise import WhiteNoise
# app.wsgi_app = WhiteNoise(app.wsgi_app, root="../web/static/", prefix="static/", max_age=604800)

# session配置
# 会话密钥: 随机生成并保存在 data/session_secret.pl
# (旧版使用网卡MAC地址推导, 可被预测并伪造登录会话)
import utils.security as security
app.config['SECRET_KEY'] = security.get_session_secret(mw.getPanelDataDir())
# 面板数据库含密码哈希/API密钥/两步验证密钥, 仅root可读
for _f in ('panel.db', 'system.db', 'default.pl'):
    security.restrict_file(mw.getPanelDataDir() + '/' + _f)

# app.config['sessions'] = dict()
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'PM_:'
app.config['SESSION_COOKIE_NAME'] = "PM_SESSION"
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
try:
    _panel_ssl = thisdb.getOptionByJson('panel_ssl', default={'open': False})
    app.config['SESSION_COOKIE_SECURE'] = bool(_panel_ssl.get('open', False))
except Exception:
    pass
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 604800

# db的配置
# app.config['SQLALCHEMY_DATABASE_URI'] = mw.getSqitePrefix()+config.SQLITE_PATH+"?timeout=20"  # 使用 SQLite 数据库
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

# BASIC AUTH
app.config['BASIC_AUTH_OPEN'] = False
try:
    basic_auth = thisdb.getOptionByJson('basic_auth', default={'open':False})
    if basic_auth['open']:
        app.config['BASIC_AUTH_OPEN'] = True
except Exception as e:
    pass

# 加载模块
from .submodules import get_submodules
for module in get_submodules():
    app.logger.info('Registering blueprint module: %s' % module)
    if app.blueprints.get(module.name) is None:
        app.register_blueprint(module)

def sendAuthenticated():
    # 发送http认证信息
    request_host = mw.getHostAddr()
    result = Response('', 401, {'WWW-Authenticate': 'Basic realm="%s"' % request_host.strip()})
    if not 'login' in session and not 'admin_auth' in session:
        session.clear()
    return result

# 不需要校验来源的接口(外部系统回调)
CSRF_EXEMPT_PATHS = ('/hook',)

def checkSameOrigin():
    if request.method in ('GET', 'HEAD', 'OPTIONS'):
        return None
    if request.path in CSRF_EXEMPT_PATHS:
        return None
    # API密钥调用不依赖Cookie, 不受CSRF影响
    if request.headers.get('App-Id', '') != '' and request.headers.get('App-Secret', '') != '':
        return None

    from urllib.parse import urlparse
    source = request.headers.get('Origin') or request.headers.get('Referer') or ''
    if source == '':
        # 浏览器跨站请求一定会携带Origin, 缺失时视为非浏览器客户端
        return None
    src_host = urlparse(source).netloc.lower()
    if src_host == '' or src_host != request.host.lower():
        return Response('Forbidden: cross-site request', 403)
    return None

@app.before_request
def requestCheck():
    request.start_time = time.time()

    domain_error = mw.checkDomainPanel()
    if domain_error is not None:
        return domain_error

    admin_close = thisdb.getOption('admin_close')
    if admin_close == 'yes':
        if not request.path.startswith('/close'):
            return redirect('/close')
    # 自定义basic auth认证
    if app.config['BASIC_AUTH_OPEN']:
        basic_auth = thisdb.getOptionByJson('basic_auth', default={'open':False})
        if not basic_auth['open']:
            return

        auth = request.authorization
        if request.path in ['/download', '/hook', '/down']:
            return
        if not auth:
            return sendAuthenticated()

        salt = basic_auth['salt']
        basic_user = mw.md5((auth.username or '').strip() + salt)
        basic_pwd = mw.md5((auth.password or '').strip() + salt)
        user_ok = security.safe_equals(basic_user, basic_auth['basic_user'])
        pwd_ok = security.safe_equals(basic_pwd, basic_auth['basic_pwd'])
        if not (user_ok and pwd_ok):
            return sendAuthenticated()

    # CSRF: 使用会话Cookie的写操作必须来自本站页面
    csrf_check = checkSameOrigin()
    if csrf_check is not None:
        return csrf_check

@app.after_request
def requestAfter(response):
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['X-Response-Time'] = round(time.time() - request.start_time, 4) 
    return response


@app.errorhandler(404)
def page_unauthorized(error):
    from flask import redirect
    return redirect('/', code=302)
    # return render_template_string('404 not found', error_info=error), 404


# 设置模板全局变量
@app.context_processor
def inject_global_variables():
    app_ver = config.APP_VERSION
    if mw.isDebugMode():
        app_ver = app_ver + str(time.time())

    data = utils_config.getGlobalVar()
    g_config = {
        'version': app_ver,
        'title' : config.APP_NAME,
        'ip' : '127.0.0.1'
    }
    return dict(config=g_config, data=data)

# webssh
# socketio = SocketIO(manage_session=False, async_mode='threading',
#                     logger=False, engineio_logger=False, debug=False,
#                     ping_interval=25, ping_timeout=120)
# cors_allowed_origins 保持默认(仅同源), 防止跨站WebSocket劫持 webssh
socketio = SocketIO(logger=False,
    engineio_logger=False,
    async_handlers=False,
    async_mode='threading')
socketio.init_app(app)

@socketio.on('connect')
def check_socket_domain(auth=None):
    if mw.checkDomainPanel() is not None:
        return False


@socketio.on('webssh_websocketio')
def webssh_websocketio(data):
    if not isLogined():
        emit('server_response', {'data': '会话丢失，请重新登陆面板!\r\n'})
        return
    import utils.ssh.ssh_terminal as ssh_terminal
    shell_client = ssh_terminal.ssh_terminal.instance()
    shell_client.run(request.sid, data)
    return


@socketio.on('webssh')
def webssh(data):
    if not isLogined():
        emit('server_response', {'data': '会话丢失，请重新登陆面板!\r\n'})
        return None

    import utils.ssh.ssh_local as ssh_local
    shell = ssh_local.ssh_local.instance()
    shell.run(data)
    return


# ------------------------------- 终端栏目: 本机 pty 终端 -------------------------------

def _pmTermEmitter(sid):
    def _emit(event, data):
        socketio.emit(event, data, to=sid)
    return _emit


@socketio.on('pm_term_open')
def pm_term_open(data):
    if not isLogined():
        emit('pm_term_out', {'tid': (data or {}).get('tid', ''), 'data': '会话丢失，请重新登录面板!\r\n'})
        return
    from utils.ssh.pty_terminal import PtyTerminal
    data = data if isinstance(data, dict) else {}
    tid = str(data.get('tid', ''))[:32]
    ok, msg = PtyTerminal.instance().open(request.sid, tid, data.get('cols'), data.get('rows'),
                                          data.get('cwd', ''), _pmTermEmitter(request.sid))
    if not ok:
        emit('pm_term_out', {'tid': tid, 'data': '\x1b[31m' + msg + '\x1b[0m\r\n'})
        emit('pm_term_exit', {'tid': tid})
    else:
        mw.writeLog('终端', '打开本机终端')


@socketio.on('pm_term_input')
def pm_term_input(data):
    if not isLogined() or not isinstance(data, dict):
        return
    from utils.ssh.pty_terminal import PtyTerminal
    PtyTerminal.instance().write(request.sid, data.get('tid', ''), data.get('data', ''))


@socketio.on('pm_term_resize')
def pm_term_resize(data):
    if not isLogined() or not isinstance(data, dict):
        return
    from utils.ssh.pty_terminal import PtyTerminal
    PtyTerminal.instance().resize(request.sid, data.get('tid', ''), data.get('cols'), data.get('rows'))


@socketio.on('pm_term_close')
def pm_term_close(data):
    if not isinstance(data, dict):
        return
    from utils.ssh.pty_terminal import PtyTerminal
    PtyTerminal.instance().close(request.sid, data.get('tid', ''))


@socketio.on('disconnect')
def pm_term_disconnect(*args):
    # 浏览器关闭/刷新页面时结束该页面打开的所有终端
    from utils.ssh.pty_terminal import PtyTerminal
    PtyTerminal.instance().closeClient(request.sid)


# File logging
logger = logging.getLogger('werkzeug')
logger.setLevel(config.CONSOLE_LOG_LEVEL)

from utils.enhanced_log_rotation import EnhancedRotatingFileHandler
fh = EnhancedRotatingFileHandler(config.LOG_FILE,
                                 config.LOG_ROTATION_SIZE,
                                 config.LOG_ROTATION_AGE,
                                 config.LOG_ROTATION_MAX_LOG_FILES)
fh.setLevel(config.FILE_LOG_LEVEL)
app.logger.addHandler(fh)
logger.addHandler(fh)

# Console logging
ch = logging.StreamHandler()
ch.setLevel(config.CONSOLE_LOG_LEVEL)
ch.setFormatter(logging.Formatter(config.CONSOLE_LOG_FORMAT))

# Log the startup
app.logger.info('########################################################')
app.logger.info('Starting %s v%s...', config.APP_NAME, config.APP_VERSION)
app.logger.info('########################################################')
app.logger.debug("Python syspath: %s", sys.path)
