# coding:utf-8

# ---------------------------------------------------------------------------------
# PM-Linux面板
# ---------------------------------------------------------------------------------
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------

import os
import sys
import re
import time
import math
import psutil
import json

import core.mw as mw

def versionDiff(now, new):
    '''
        test 测试
        new 有新版本
        none 没有新版本
    '''
    new_list = new.split('.')
    if len(new_list) > 3:
        return 'test'

    now_list = now.split('.')
    ret = 'none'
    # distutils 在 Python 3.12 中已被移除, 改用 packaging
    try:
        from packaging.version import Version
        if Version(new.lstrip('v')) > Version(now.lstrip('v')):
            return 'new'
    except Exception:
        if new != now:
            return 'new'
    return 'none'

def getServerInfo():
    import urllib.request
    import ssl
    upAddr = 'https://api.github.com/repos/ledang3099/pmpanel/releases/latest'
    try:
        # 校验证书, 防止更新信息被中间人篡改
        context = ssl.create_default_context()
        req = urllib.request.urlopen(upAddr, context=context, timeout=3)
        result = req.read().decode('utf-8')
        version = json.loads(result)
        return version
    except Exception as e:
        print(str(e))
        return None
    return None

def updateServer(stype, version=''):
    import config
    # 更新服务
    try:
        if not mw.isRestart():
            return mw.returnData(False, '请等待所有安装任务完成再执行!')

        version_new_info = getServerInfo()
        if version_new_info is None:
            return mw.returnData(False, '服务器数据或网络有问题!')

        version_now = config.APP_VERSION
        new_ver = version_new_info['name']
        if stype == 'check':
            diff = versionDiff(version_now, new_ver)
            if diff == 'new':
                return mw.returnData(True, '有新版本!', new_ver)
            elif diff == 'test':
                return mw.returnData(True, '有测试版本!', new_ver)
            else:
                return mw.returnData(False, '已经是最新,无需更新!')

        if stype == 'info':
            diff = versionDiff(version_now, new_ver)
            data = {}
            data['version'] = new_ver
            data['content'] = version_new_info['body'].replace("\n", "<br/>")
            return mw.returnData(True, '更新信息!', data)

        if stype == 'update':
            if version == '':
                return mw.returnData(False, '缺少版本信息!')

            if new_ver != version:
                return mw.returnData(False, '更新失败,请重试!')

            if not re.match(r'^[0-9A-Za-z_.\-]+$', version):
                return mw.returnData(False, '版本号格式不正确!')

            toPath = mw.getPanelDir() + '/temp'
            if not os.path.exists(toPath):
                mw.execShell('mkdir -p ' + toPath)

            newUrl = "https://github.com/ledang3099/pmpanel/archive/refs/tags/" + version + ".zip"

            dist_mw = toPath + '/mw.zip'
            if not os.path.exists(dist_mw):
                mw.execShell('wget -O ' + dist_mw + ' ' + newUrl)

            # GitHub 源码包解压后的目录名为 "仓库名-版本号"
            dist_to = toPath + "/pmpanel-" + version.lstrip('v')
            if not os.path.exists(dist_to):
                os.system('unzip -o ' + dist_mw + ' -d ' + toPath)
            if not os.path.isdir(dist_to):
                mw.execShell('rm -rf ' + dist_mw)
                return mw.returnData(False, '下载或解压更新包失败!')

            cmd_cp = 'cp -rf ' + dist_to + '/* ' + mw.getPanelDir()
            mw.execShell(cmd_cp)

            mw.execShell('rm -rf ' + dist_to)
            mw.execShell('rm -rf ' + dist_mw)

            update_env = '''
#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin

P_VER=`python3 -V | awk '{print $2}'`

if [ ! -f /www/server/pmpanel/bin/activate ];then
cd /www/server/pmpanel && python3 -m venv .
cd /www/server/pmpanel && . /www/server/pmpanel/bin/activate
else
cd /www/server/pmpanel && . /www/server/pmpanel/bin/activate
fi

cn=$(curl -fsSL -m 10 http://ipinfo.io/json | grep "\"country\": \"CN\"")
PIPSRC="https://pypi.python.org/simple"
if [ ! -z "$cn" ];then
PIPSRC="https://pypi.tuna.tsinghua.edu.cn/simple"
fi

cd /www/server/pmpanel && pip3 install -r /www/server/pmpanel/requirements.txt -i $PIPSRC

P_VER_D=`echo "$P_VER"|awk -F '.' '{print $1}'`
P_VER_M=`echo "$P_VER"|awk -F '.' '{print $2}'`
NEW_P_VER=${P_VER_D}.${P_VER_M}

if [ -f /www/server/pmpanel/version/r${NEW_P_VER}.txt ];then
cd /www/server/pmpanel && pip3 install -r /www/server/pmpanel/version/r${NEW_P_VER}.txt -i $PIPSRC
fi
'''
            os.system(update_env)
            mw.restartMw()
            return mw.returnData(True, '安装更新成功!')

        return mw.returnData(False, '已经是最新,无需更新!')
    except Exception as ex:
        # print('updateServer', ex)
        return mw.returnData(False, "连接服务器失败!" + str(ex))




