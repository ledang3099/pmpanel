# coding:utf-8

import sys
import io
import os
import time
import re
import json

web_dir = os.getcwd() + "/web"
if os.path.exists(web_dir):
    sys.path.append(web_dir)
    os.chdir(web_dir)

import core.mw as mw

app_debug = False
if mw.isAppleSystem():
    app_debug = True


def getPluginName():
    return 'webhook'

def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()


def getCfgFilePath():
    return getServerDir() + "/cfg.json"


def getCfg():
    cfg = getCfgFilePath()
    if not os.path.exists(cfg):
        initCfg()

    data = mw.readFile(cfg)
    data = json.loads(data)
    return data


def runShellArgs(args):
    import hmac
    import subprocess
    access_key = str(args.get('access_key', ''))
    if not re.match(r'^[0-9a-f]{32}$', access_key):
        return mw.returnJson(False, '指定Hook不存在!')
    data = getCfg()
    for i in range(len(data)):
        if hmac.compare_digest(str(data[i]['access_key']), access_key):
            script_dir = getServerDir() + "/scripts"
            shellFile = script_dir + '/' + data[i]['access_key']
            param = args['params']
            if param == '':
                param = 'no-parameters'

            # 旧版把参数直接拼接进shell命令, 可注入任意命令; 现在作为独立参数传递, 不经过shell
            params = re.sub("\"", '', param).split()
            log = open(shellFile + '.log', 'ab')
            subprocess.Popen(['bash', shellFile] + params, stdout=log, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, start_new_session=True)
            log.close()
            data[i]['count'] += 1
            data[i]['uptime'] = int(time.time())
            mw.writeFile(getCfgFilePath(), json.dumps(data))
            return mw.returnJson(True, '运行成功!')
    return mw.returnJson(False, '指定Hook不存在!')
