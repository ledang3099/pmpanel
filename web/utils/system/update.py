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

REPO = 'ledang3099/pmpanel'


def getServerInfo():
    """
    读取 GitHub 上最新的正式发布(Release)
    返回 (info, error): 成功时 info 为 release 数据; 失败时 error 为原因
    """
    import urllib.request
    import urllib.error
    import ssl
    url = 'https://api.github.com/repos/%s/releases/latest' % REPO
    try:
        # 校验证书, 防止更新信息被中间人篡改
        req = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'pmpanel-updater'})
        with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=8) as resp:
            info = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, '仓库中还没有发布正式版本(Release), 暂无可用更新'
        if e.code == 403:
            return None, 'GitHub 接口访问受限(请求过于频繁), 请稍后再试'
        return None, 'GitHub 返回错误 %s' % e.code
    except Exception as e:
        return None, '无法连接 GitHub, 请检查服务器网络: %s' % str(e)[:100]
    tag = str(info.get('tag_name') or '')
    if not re.match(r'^v?[0-9]+(\.[0-9]+){1,3}([-.][0-9A-Za-z]+)?$', tag):
        return None, '最新发布的标签名格式不正确: ' + tag[:40]
    info['version'] = tag.lstrip('v')
    return info, ''


def _download(url, path):
    import urllib.request
    import ssl
    req = urllib.request.Request(url, headers={'User-Agent': 'pmpanel-updater'})
    with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=120) as resp, open(path, 'wb') as f:
        while True:
            chunk = resp.read(1024 * 256)
            if not chunk:
                break
            f.write(chunk)


def _safeExtract(archive, dest):
    """解压发布包, 拒绝绝对路径、../ 以及链接文件, 返回包内唯一的顶层目录"""
    import tarfile
    with tarfile.open(archive, 'r:gz') as tar:
        members = tar.getmembers()
        tops = set()
        for m in members:
            name = m.name
            if name.startswith('/') or '..' in name.split('/'):
                raise ValueError('更新包中包含不安全的路径: ' + name)
            if m.issym() or m.islnk() or m.isdev():
                raise ValueError('更新包中包含不允许的文件类型: ' + name)
            tops.add(name.split('/')[0])
        if len(tops) != 1:
            raise ValueError('更新包结构不正确')
        tar.extractall(dest, members=members)
    return os.path.join(dest, tops.pop())


def applyUpdate(info):
    import shutil
    import subprocess
    import tempfile
    tag = info['tag_name']
    panel = mw.getPanelDir()
    work = tempfile.mkdtemp(prefix='update-', dir=panel + '/temp' if os.path.isdir(panel + '/temp') else None)
    try:
        archive = os.path.join(work, 'release.tar.gz')
        _download('https://github.com/%s/archive/refs/tags/%s.tar.gz' % (REPO, tag), archive)
        src = _safeExtract(archive, os.path.join(work, 'src'))
        if not os.path.isfile(os.path.join(src, 'web/app.py')):
            return mw.returnData(False, '更新包不完整')
        # 用新版本自带的覆盖脚本: 保留运行数据, 任一文件复制失败则整体回滚
        r = subprocess.run([sys.executable, os.path.join(src, 'scripts/update/apply_release.py'), src, panel],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if r.returncode != 0:
            return mw.returnData(False, '覆盖文件失败, 已回滚: ' + r.stdout.strip()[-300:])
        # 安装新版本需要的 Python 依赖
        pip = os.path.join(panel, 'bin', 'pip3')
        req = os.path.join(panel, 'requirements.txt')
        if os.path.exists(pip) and os.path.exists(req):
            subprocess.run([pip, 'install', '-q', '-r', req], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1800)
            pyver = '%d.%d' % sys.version_info[:2]
            extra = os.path.join(panel, 'version', 'r%s.txt' % pyver)
            if os.path.exists(extra):
                subprocess.run([pip, 'install', '-q', '-r', extra], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1800)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    mw.writeLog('面板设置', '面板已更新到 ' + info['version'])
    mw.restartMw()
    return mw.returnData(True, '已更新到 %s, 面板正在重启' % info['version'])


def updateServer(stype, version=''):
    import config
    import html
    try:
        if not mw.isRestart():
            return mw.returnData(False, '请等待所有安装任务完成再执行!')

        info, err = getServerInfo()
        if info is None:
            return mw.returnData(False, err)

        version_now = config.APP_VERSION
        new_ver = info['version']
        diff = versionDiff(version_now, new_ver)

        if stype == 'check':
            if diff == 'new':
                return mw.returnData(True, '有新版本!', new_ver)
            if diff == 'test':
                return mw.returnData(True, '有测试版本!', new_ver)
            return mw.returnData(False, '当前已是最新版本(%s)' % version_now, 'latest')

        if stype == 'info':
            data = {
                'version': new_ver,
                'current': version_now,
                'title': html.escape(info.get('name') or new_ver),
                # 发布说明转义后再换行, 防止发布内容中的 HTML 被执行
                'content': html.escape(info.get('body') or '').replace("\n", "<br/>"),
                'published_at': info.get('published_at', ''),
            }
            return mw.returnData(True, '更新信息!', data)

        if stype == 'update':
            if version != new_ver:
                return mw.returnData(False, '版本信息已变化, 请重新检查更新!')
            if diff == 'none':
                return mw.returnData(False, '当前已是最新版本')
            return applyUpdate(info)

        return mw.returnData(False, '参数错误')
    except Exception as ex:
        return mw.returnData(False, '更新失败: ' + str(ex)[:200])
