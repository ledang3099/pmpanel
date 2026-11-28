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

app_debug = False
if mw.isAppleSystem():
    app_debug = True


def getPluginName():
    return 'gdrive'


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
from gdriveclient import gdriveclient


gd = gdriveclient(getPluginDir(), getServerDir())
gd.setDebug(False)


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
    cfg = getServerDir() + "/token.json"
    if os.path.exists(cfg):
        return True
    return False


def getConf():
    if not isAuthApi():
        sign_in_url, state = gd.get_sign_in_url()
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
        token = gd.set_auth_url(url)
        # gd.store_token(token)
        # gd.store_user()
        return mw.returnJson(True, "授权成功!")
    except Exception as e:
        return mw.returnJson(False, "授权失败2!:" + str(e))
    return mw.returnJson(False, "授权失败!:" + str(e))


def clearAuth():
    token = getServerDir() + "/token.json"
    if os.path.exists(token):
        os.remove(token)
    return mw.returnJson(True, "清空授权成功!")


def getList():
    if not isAuthApi():
        return mw.returnJson(False, "未配置,请点击`授权`", [])

    args = getArgs()
    data = checkArgs(args, ['file_id'])
    if not data[0]:
        return data[1]

    try:
        flist = gd.get_list(args['file_id'])
        return mw.returnJson(True, "ok", flist)
    except Exception as e:
        return mw.returnJson(False, str(e), [])


def createDir():
    if not isAuthApi():
        return mw.returnJson(False, "未配置,请点击`授权`", [])

    args = getArgs()
    data = checkArgs(args, ['parents', 'name'])
    if not data[0]:
        return data[1]
    isok = gd.create_folder(args['name'], args['parents'])
    if isok:
        return mw.returnJson(True, "创建成功")
    return mw.returnJson(False, "创建失败")


def deleteDir():
    args = getArgs()
    data = checkArgs(args, ['dir_name', 'path'])
    if not data[0]:
        return data[1]

    isok = gd.delete_file_by_id(args['dir_name'])
    if isok:
        return mw.returnJson(True, "删除成功")
    return mw.returnJson(False, "文件不为空,删除失败!")


def deleteFile():
    args = getArgs()
    data = checkArgs(args, ['path', 'filename'])
    if not data[0]:
        return data[1]

    isok = gd.delete_file(args['filename'], parent=args['path'] or 'root')
    if isok:
        return mw.returnJson(True, "删除成功")
    return mw.returnJson(False, "删除失败")


def backupAllFunc(stype):
    if not isAuthApi():
        raise SystemExit('未授权 API，无法上传备份。')
    return scheduled_backup.upload(stype, gd)


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
