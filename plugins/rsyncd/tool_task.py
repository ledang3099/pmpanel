# coding:utf-8

# ---------------------------------------------------------------------------------
# rsync 同步插件: 定时同步任务(写入面板计划任务)
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------

import os
import sys
import json
import shlex

web_dir = os.getcwd() + "/web"
if os.path.exists(web_dir):
    sys.path.append(web_dir)
    os.chdir(web_dir)

import core.mw as mw
from utils.crontab import crontab as MwCrontab

TASK_PREFIX = "[勿删]同步插件定时任务["


def getServerDir():
    return mw.getServerDir() + '/rsyncd'


def taskName(name):
    return TASK_PREFIX + name + "]"


def removeBgTask():
    '''删除本插件创建的全部定时任务(按名称前缀匹配, 旧版只删除第一个)'''
    rows = mw.M("crontab").field("id,name").where("name like ?", (TASK_PREFIX + '%',)).select()
    for row in rows or []:
        MwCrontab.instance().delete(row['id'])
    cfg = getServerDir() + "/task_config.json"
    if os.path.exists(cfg):
        os.remove(cfg)
    return True


def createBgTaskByName(t):
    name = t['name']
    send_dir = getServerDir() + '/send/' + name
    log = send_dir + '/run.log'

    if t.get('period') == 'minute-n':
        params_type, where1, hour, minute = 'minute-n', str(int(t.get('minute_n', 30))), '', ''
    else:
        params_type, where1 = 'day', ''
        hour, minute = str(int(t.get('hour', 2))), str(int(t.get('minute', 30)))

    q = shlex.quote
    cmd = 'echo "===== $(date +"%Y-%m-%d %H:%M:%S") 定时同步开始 =====" >> ' + q(log) + "\n"
    cmd += 'bash ' + q(send_dir + '/cmd') + ' >> ' + q(log) + ' 2>&1' + "\n"
    cmd += 'echo "===== $(date +"%Y-%m-%d %H:%M:%S") 定时同步结束 =====" >> ' + q(log) + "\n"

    params = {
        'name': taskName(name),
        'type': params_type,
        'week': "",
        'where1': where1,
        'hour': hour,
        'minute': minute,
        'save': "",
        'backup_to': "",
        'stype': "toShell",
        'sname': '',
        'sbody': cmd,
        'url_address': '',
    }
    return MwCrontab.instance().add(params)


def createBgTask(data):
    removeBgTask()
    for t in data:
        if not t.get('realtime'):
            createBgTaskByName(t)
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "remove":
        removeBgTask()
