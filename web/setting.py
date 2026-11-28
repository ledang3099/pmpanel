# coding:utf-8

# ---------------------------------------------------------------------------------
# PM-Linux面板
# ---------------------------------------------------------------------------------
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------
# 配置文件
# ---------------------------------------------------------------------------------



import time
import sys
import random
import os

# 初始化db
from admin import setup
setup.init()

import core.mw as mw
import utils.system as system 
import thisdb

# Socket.IO(终端、WebSSH)在 threading 模式下只能运行在单个进程中:
# 多个 worker 时同一连接的请求会落到不同进程, 出现 "Invalid session"。
# 面板并发不高, 用 1 个进程 + 多线程即可。
workers = 1

panel_dir = mw.getPanelDir()
log_dir = mw.getMWLogs()
if not os.path.exists(log_dir):
    os.mkdir(log_dir)

data_dir = panel_dir+'/data'
if not os.path.exists(data_dir):
    os.mkdir(data_dir)

# default port
panel_port = '7200'
from utils.firewall import Firewall as MwFirewall
default_port_file = data_dir+'/port.pl'
if os.path.exists(default_port_file): 
    panel_port = mw.readFile(default_port_file)
    panel_port.strip()

# panel_dbfile = data_dir + "/panel.db"
# and not os.path.exists(panel_dbfile)
# if os.path.exists(default_port_file):
#     MwFirewall.instance().addPanelPort(panel_port)

if not os.path.exists(default_port_file):
    panel_port = str(random.randint(10000, 65530))
    MwFirewall.instance().addPanelPort(panel_port)
    mw.writeFile(default_port_file, panel_port)

bind = []
default_ipv6_file = data_dir+'/ipv6.pl'
if os.path.exists(default_ipv6_file):
    bind.append('[0:0:0:0:0:0:0:0]:%s' % panel_port)
else:
    bind.append('0.0.0.0:%s' % panel_port)

panel_ssl_data = thisdb.getOptionByJson('panel_ssl', default={'open':False})
if panel_ssl_data['open']:
    choose = panel_ssl_data['choose']
    if mw.inArray(['local','nginx'],choose):
        panel_cert = panel_dir+'/ssl/'+choose+'/cert.pem'
        panel_private = panel_dir+'/ssl/'+choose+'/private.pem'
        if os.path.exists(panel_cert) and os.path.exists(panel_private):
            certfile = panel_cert
            keyfile  = panel_private
            ciphers = 'TLSv1 TLSv1.1 TLSv1.2 TLSv1.3'
            ssl_version = 2
            http2 = True

# 每个打开的终端/WebSocket 会长期占用一个线程, 线程数需留足余量
threads = 32
backlog = 2048
reload = False
daemon = True
# 不按请求数重启进程: 重启会断开所有终端和 WebSocket 连接
max_requests = 0
# # worker_class = 'geventwebsocket.gunicorn.workers.GeventWebSocketWorker'
worker_class = 'gthread'
timeout = 600
keepalive = 60
preload_app = False
capture_output = True
access_log_format = '%(t)s %(p)s %(h)s "%(r)s" %(s)s %(L)s %(b)s %(f)s" "%(a)s"'
loglevel = 'warning'
errorlog = log_dir + '/panel_error.log'
accesslog = log_dir + '/panel.log'
pidfile = log_dir + '/panel.pid'
