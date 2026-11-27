# coding: utf-8

import time
import random
import os
import json
import re
import sys
import subprocess

web_dir = os.getcwd() + "/web"
if os.path.exists(web_dir):
    sys.path.append(web_dir)
    os.chdir(web_dir)

import core.mw as mw


def getPluginName():
    return 'sys-opt'


def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()


def getArgs():
    args = sys.argv[2:]
    tmp = {}
    args_len = len(args)

    if args_len == 1:
        t = args[0].strip('{').strip('}')
        t = t.split(':')
        tmp[t[0]] = t[1]
    elif args_len > 1:
        for i in range(len(args)):
            t = args[i].split(':')
            tmp[t[0]] = t[1]
    return tmp


def checkArgs(data, ck=[]):
    for i in range(len(ck)):
        if not ck[i] in data:
            return (False, mw.returnJson(False, '参数:(' + ck[i] + ')没有!'))
    return (True, mw.returnJson(True, 'ok'))


def contentReplace(content):
    service_path = mw.getServerDir()
    content = content.replace('{$ROOT_PATH}', mw.getFatherDir())
    content = content.replace('{$SERVER_PATH}', service_path)
    content = content.replace('{$SERVER_APP}', service_path + '/sys-opt')
    return content


def status():
    return 'start' if os.path.isfile(sysConf()) else 'stop'


def reload():
    result = subprocess.run(['sysctl', '-p', ensureSysConf()], capture_output=True)
    return 'ok' if result.returncode == 0 else 'fail'


def start():
    return reload()


def stop():
    return reload()


def restart():
    return reload()


def configTpl():
    path = getPluginDir() + '/tpl'
    pathFile = os.listdir(path)
    tmp = []
    for one in pathFile:
        file = path + '/' + one
        tmp.append(file)
    return mw.getJson(tmp)


def readConfigTpl():
    args = getArgs()
    data = checkArgs(args, ['file'])
    if not data[0]:
        return data[1]

    path = args['file']
    tpl_dir = os.path.join(getPluginDir(), 'tpl')
    if os.path.dirname(path) != tpl_dir or os.path.basename(path) not in os.listdir(tpl_dir):
        return mw.returnJson(False, '配置模板不存在。')
    content = mw.readFile(path)
    content = contentReplace(content)
    return mw.returnJson(True, 'ok', content)


def sysConf():
    legacy = '/etc/sysctl.conf'
    managed = '/etc/sysctl.d/99-pmpanel.conf'
    return legacy if os.path.isfile(legacy) and not os.path.isfile(managed) else managed


def ensureSysConf():
    path = sysConf()
    with open(path, 'a', encoding='utf-8'):
        pass
    return path


def secRunLog():
    if os.path.exists('/var/log/auth.log'):
        return '/var/log/auth.log'
    if os.path.exists('/var/log/messages'):
        return '/var/log/messages'
    return '/var/log/secure'


def msgRunLog():
    if os.path.exists('/var/log/kern.log'):
        return '/var/log/kern.log'
    return '/var/log/messages'


def cronRunLog():
    if os.path.exists('/var/log/syslog.log'):
        return '/var/log/syslog.log'
    if os.path.exists('/var/log/syslog'):
        return '/var/log/syslog'
    return '/var/log/cron'


def systemRunLog():
    return '/var/log/syslog'

def showHosts():
    return '/etc/hosts'

def showResolv():
    return '/etc/resolv.conf'

if __name__ == "__main__":
    func = sys.argv[1]
    if func == 'status':
        print(status())
    elif func == 'start':
        print(start())
    elif func == 'stop':
        print(stop())
    elif func == 'restart':
        print(restart())
    elif func == 'reload':
        print(reload())
    elif func == 'conf':
        print(ensureSysConf())
    elif func == 'config_tpl':
        print(configTpl())
    elif func == 'read_config_tpl':
        print(readConfigTpl())
    elif func == 'sec_run_log':
        print(secRunLog())
    elif func == 'msg_run_log':
        print(msgRunLog())
    elif func == 'cron_run_log':
        print(cronRunLog())
    elif func == 'sys_run_log':
        print(systemRunLog())
    elif func == 'hosts':
        print(showHosts())
    elif func == 'resolv':
        print(showResolv())
    else:
        print('err')
