# coding:utf-8

import sys
import io
import os
import time
import re
import json


# print(sys.platform)
if sys.platform != "darwin":
    os.chdir("/www/server/pmpanel")


web_dir = os.getcwd() + "/web"
if os.path.exists(web_dir):
    sys.path.append(web_dir)
    os.chdir(web_dir)

import core.mw as mw
from utils import scheduled_backup

_ver = sys.version_info
is_py2 = (_ver[0] == 2)
is_py3 = (_ver[0] == 3)

DEBUG = False

if is_py2:
    reload(sys)
    sys.setdefaultencoding('utf-8')

app_debug = False
if mw.isAppleSystem():
    app_debug = True


def getPluginName():
    return 'msonedrive'


def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()


def in_array(name, arr=[]):
    for x in arr:
        if name == x:
            return True
    return False


sys.path.append(getPluginDir() + "/class")
from msodclient import msodclient


msodc = msodclient(getPluginDir(), getServerDir())
msodc.setDebug(False)


def getArgs():
    args = sys.argv[2:]
    tmp = {}
    args_len = len(args)
    if args_len == 1:
        t = args[0].strip('{').strip('}')
        if t.strip() == '':
            tmp = []
        else:
            t = t.split(':', 1)
            tmp[t[0]] = t[1]
        tmp[t[0]] = t[1]
    elif args_len > 1:
        for i in range(len(args)):
            t = args[i].split(':', 1)
            tmp[t[0]] = t[1]
    return tmp


def checkArgs(data, ck=[]):
    for i in range(len(ck)):
        if not ck[i] in data:
            return (False, mw.returnJson(False, '参数:(' + ck[i] + ')没有!'))
    return (True, mw.returnJson(True, 'ok'))


def status():
    return 'start'


def isAuthApi():
    cfg = getServerDir() + "/user.conf"
    if os.path.exists(cfg):
        return True
    return False


def getConf():
    if not isAuthApi():
        sign_in_url, state = msodc.get_sign_in_url()
        return mw.returnJson(False, "未授权!", {'auth_url': sign_in_url})
    return mw.returnJson(True, "OK")


def setAuthUrl():
    args = getArgs()
    data = checkArgs(args, ['url'])
    if not data[0]:
        return data[1]

    url = args['url']

    try:
        if url.startswith("http://"):
            url = url.replace("http://", "https://")
        token = msodc.get_token_from_authorized_url(authorized_url=url)
        msodc.store_token(token)
        msodc.store_user()
        return mw.returnJson(True, "授权成功!")
    except Exception as e:
        return mw.returnJson(False, "授权失败2!:" + str(e))
    return mw.returnJson(False, "授权失败!:" + str(e))


def clearAuth():
    cfg = getServerDir() + "/user.conf"
    if os.path.exists(cfg):
        os.remove(cfg)

    token = getServerDir() + "/token.pickle"
    if os.path.exists(token):
        os.remove(token)

    return mw.returnJson(True, "清空授权成功!")


def getList():
    cfg = getServerDir() + "/user.conf"
    if not os.path.exists(cfg):
        return mw.returnJson(False, "未配置,请点击`授权`", [])

    args = getArgs()
    data = checkArgs(args, ['path'])
    if not data[0]:
        return data[1]

    try:
        flist = msodc.get_list(args['path'])
        return mw.returnJson(True, "ok", flist)
    except Exception as e:
        return mw.returnJson(False, str(e), [])


def createDir():
    cfg = getServerDir() + "/user.conf"
    if not os.path.exists(cfg):
        return mw.returnJson(False, "未配置OneDrive,请点击`授权`", [])

    args = getArgs()
    data = checkArgs(args, ['path', 'name'])
    if not data[0]:
        return data[1]

    file = args['path'] + "/" + args['name']
    isok = msodc.create_dir(file)
    if isok:
        return mw.returnJson(True, "创建成功")
    return mw.returnJson(False, "创建失败")


def deleteDir():
    args = getArgs()
    data = checkArgs(args, ['dir_name', 'path'])
    if not data[0]:
        return data[1]

    file = args['path'] + "/" + args['dir_name']
    file = file.strip('/')
    isok = msodc.delete_object(file)
    if isok:
        return mw.returnJson(True, "删除成功")
    return mw.returnJson(False, "文件不为空,删除失败!")


def deleteFile():
    args = getArgs()
    data = checkArgs(args, ['path', 'filename'])
    if not data[0]:
        return data[1]

    file = args['path'] + "/" + args['filename']
    file = file.strip('/')
    isok = msodc.delete_object(file)
    if isok:
        return mw.returnJson(True, "删除成功")
    return mw.returnJson(False, "删除失败")


def backupAllFunc(stype):
    if not isAuthApi():
        raise SystemExit('未授权 API，无法上传备份。')
    return scheduled_backup.upload(stype, msodc)


def installPreInspection():
    return 'ok'

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
    elif func == 'install_pre_inspection':
        print(installPreInspection())
    elif func == 'conf':
        print(getConf())
    elif func == 'set_auth_url':
        print(setAuthUrl())
    elif func == 'clear_auth':
        print(clearAuth())
    elif func == "get_list":
        print(getList())
    elif func == "create_dir":
        print(createDir())
    elif func == "delete_dir":
        print(deleteDir())
    elif func == 'delete_file':
        print(deleteFile())
    elif in_array(func, ['site', 'database', 'path']) or func.find('database_') > -1:
        print(backupAllFunc(func))
    else:
        print('error')
