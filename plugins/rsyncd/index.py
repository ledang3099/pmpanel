# coding: utf-8

# ---------------------------------------------------------------------------------
# PM-Linux面板 rsync 同步插件
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------
# 接收端: rsync 守护进程(rsyncd), 由结构化配置 config.json 生成 rsyncd.conf
# 发送端: lsyncd 实时同步 / 计划任务定时同步
#
# 界面通过 /plugins/callback 调用本文件中的函数(参数为 dict, 返回 dict);
# 服务管理(status/start/stop/...)仍通过命令行调用, 供面板通用的服务页面使用。
# ---------------------------------------------------------------------------------

import os
import re
import sys
import json
import time
import base64
import shlex
import ipaddress
import subprocess

web_dir = os.getcwd() + "/web"
if os.path.exists(web_dir):
    sys.path.append(web_dir)
    os.chdir(web_dir)

import core.mw as mw

RSYNC_VERSION = '3.5.2'
# 低于此版本的 rsync 存在 2026 年公开的守护进程漏洞(CVE-2026-29518 等)
RSYNC_MIN_SAFE = (3, 4, 3)

NAME_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_\-]{0,31}$')
HOST_RE = re.compile(r'^(?=.{1,253}$)([A-Za-z0-9]([A-Za-z0-9\-]{0,61}[A-Za-z0-9])?\.)*[A-Za-z0-9]([A-Za-z0-9\-]{0,61}[A-Za-z0-9])?$')
UNSAFE_CHARS = re.compile(r'[\x00-\x1f\x7f]')


def getPluginName():
    return 'rsyncd'


def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()


def ok(msg='OK', data=None):
    return {'status': True, 'msg': msg, 'data': data}


def fail(msg, data=None):
    return {'status': False, 'msg': msg, 'data': data}


# ------------------------------- 参数校验 ---------------------------------------

def checkName(name):
    return isinstance(name, str) and NAME_RE.match(name) is not None


def checkPath(path):
    if not isinstance(path, str) or not path.startswith('/') or UNSAFE_CHARS.search(path):
        return False
    if '..' in path.split('/') or len(path) > 1024:
        return False
    # 不允许把系统关键目录作为同步目录
    real = os.path.realpath(path).rstrip('/') or '/'
    if real in ('/', '/etc', '/root', '/boot', '/proc', '/sys', '/dev', '/usr', '/bin', '/sbin', '/lib', '/lib64', '/var'):
        return False
    return True


def checkText(text, max_len=200):
    return isinstance(text, str) and len(text) <= max_len and UNSAFE_CHARS.search(text) is None


def checkHost(host):
    if not isinstance(host, str) or host == '':
        return False
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return HOST_RE.match(host) is not None


def parseHostsAllow(value):
    '''
    允许访问的客户端: 以空格/逗号/换行分隔的 IP 或网段, 返回规范化列表; 格式错误返回 None
    '''
    items = [x.strip() for x in re.split(r'[\s,;]+', str(value or '')) if x.strip()]
    result = []
    for item in items:
        try:
            net = ipaddress.ip_network(item, strict=False)
            result.append(str(net) if net.num_addresses > 1 else str(net.network_address))
        except ValueError:
            return None
    return result


def toInt(value, default, low, high):
    try:
        n = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    if n < low or n > high:
        return None
    return n


def checkPassword(pwd):
    return isinstance(pwd, str) and 8 <= len(pwd) <= 128 and UNSAFE_CHARS.search(pwd) is None and ':' not in pwd


# ------------------------------- 配置存取 ---------------------------------------

def configPath():
    return getServerDir() + '/config.json'


def defaultConfig():
    return {
        'receive': {
            'default': {
                'port': 873,
                'max connections': 100,
                'timeout': 600,
                'uid': 'www',
                'gid': 'www',
            },
            'list': []
        },
        'send': {
            'default': {
                'maxProcesses': 8,
                'inotifyMode': 'CloseWrite',
            },
            'list': []
        },
        'migrated': True,
    }


def getConfig():
    path = configPath()
    data = None
    if os.path.exists(path):
        try:
            data = json.loads(mw.readFile(path))
        except Exception:
            data = None
    if not isinstance(data, dict):
        data = defaultConfig()
    base = defaultConfig()
    for k in ('receive', 'send'):
        data.setdefault(k, base[k])
        data[k].setdefault('default', base[k]['default'])
        data[k].setdefault('list', [])
    if not data.get('migrated'):
        migrateOldConf(data)
    return data


def saveConfig(data):
    path = configPath()
    if not os.path.exists(getServerDir()):
        os.makedirs(getServerDir())
    tmp = path + '.tmp'
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2))
    os.replace(tmp, path)


def migrateOldConf(data):
    '''
    旧版插件把接收模块直接写在 rsyncd.conf 中, 这里导入为结构化配置(只执行一次)
    '''
    conf = appConf()
    content = mw.readFile(conf) or ''
    global_hosts = ''
    m = re.search(r'(?m)^\s*hosts allow\s*=\s*(.*)$', content.split('[', 1)[0])
    if m:
        global_hosts = m.group(1).strip()
    names = re.findall(r'(?m)^\[(.+?)\]\s*$', content)
    exist = set(x['name'] for x in data['receive']['list'])
    for name in names:
        if not checkName(name) or name in exist:
            continue
        block = re.search(r'(?ms)^\[' + re.escape(name) + r'\]\s*$(.*?)(?=^\[|\Z)', content)
        opts = {}
        if block:
            for line in block.group(1).splitlines():
                if '=' in line:
                    k, v = line.split('=', 1)
                    opts[k.strip()] = v.strip()
        path = opts.get('path', '')
        if not checkPath(path):
            continue
        hosts = parseHostsAllow(opts.get('hosts allow', global_hosts if global_hosts != '*' else ''))
        data['receive']['list'].append({
            'name': name,
            'path': path,
            'comment': opts.get('comment', '')[:200],
            'hosts': hosts or [],
            'read_only': opts.get('read only', 'false') == 'true',
            'open_all': (hosts is None or hosts == []) and global_hosts == '*',
            'add_time': int(time.time()),
        })
    # 旧版默认以 root 身份读写文件且关闭 chroot, 统一改为安全默认值, 仅保留端口
    old_default = data['receive'].get('default', {})
    new_default = defaultConfig()['receive']['default']
    port = toInt(old_default.get('port', 873), 873, 1, 65535)
    new_default['port'] = port or 873
    data['receive']['default'] = new_default

    # 旧版发送任务字段: name(=接收模块/用户), rsync{bwlimit,compress,port}, 布尔值为字符串
    new_send = []
    for t in data['send'].get('list', []):
        if 'module' in t:
            new_send.append(t)
            continue
        name = str(t.get('name', ''))
        r = t.get('rsync', {}) or {}
        item = {
            'name': name, 'ip': str(t.get('ip', '')), 'port': toInt(r.get('port', t.get('port', 873)), 873, 1, 65535) or 873,
            'module': name, 'user': name, 'password': str(t.get('password', '')),
            'path': str(t.get('path', '')), 'realtime': str(t.get('realtime', 'true')) == 'true',
            'delay': toInt(t.get('delay', 3), 3, 1, 3600) or 3, 'delete': str(t.get('delete', 'false')) == 'true',
            'compress': str(r.get('compress', 'true')) == 'true', 'bwlimit': toInt(r.get('bwlimit', 0), 0, 0, 10485760) or 0,
            'period': t.get('period', 'day') if t.get('period') in ('day', 'minute-n') else 'day',
            'hour': toInt(t.get('hour', 2), 2, 0, 23) or 0, 'minute': toInt(t.get('minute', 30), 30, 0, 59) or 0,
            'minute_n': toInt(t.get('minute-n', 30), 30, 1, 1440) or 30,
            'exclude': [x for x in t.get('exclude', []) if checkText(x, 255) and '"' not in x],
        }
        if checkName(name) and checkHost(item['ip']) and checkPath(item['path']):
            new_send.append(item)
    data['send']['list'] = new_send
    data['send']['default'] = defaultConfig()['send']['default']

    data['migrated'] = True
    saveConfig(data)
    writeRsyncdConf(data)


# ------------------------------- rsync 程序 -------------------------------------

def rsyncBin():
    own = getServerDir() + '/bin/rsync'
    if os.path.exists(own):
        return own
    out = subprocess.run(['sh', '-c', 'command -v rsync'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout.decode().strip()
    return out


def binVersion(binary):
    if not binary or not os.path.exists(binary):
        return ''
    try:
        out = subprocess.run([binary, '--version'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10).stdout.decode()
    except Exception:
        return ''
    m = re.search(r'version\s+v?(\d+\.\d+\.\d+)', out)
    return m.group(1) if m else ''


def versionTuple(v):
    try:
        return tuple(int(x) for x in v.split('.')[:3])
    except Exception:
        return (0, 0, 0)


def lsyncdBin():
    return subprocess.run(['sh', '-c', 'command -v lsyncd'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout.decode().strip()


# ------------------------------- 接收端 rsyncd.conf -----------------------------

def appConf():
    return getServerDir() + '/rsyncd.conf'


def secretsFile(name):
    return getServerDir() + '/receive/' + name + '/auth.db'


def writeSecret(name, password):
    path = secretsFile(name)
    d = os.path.dirname(path)
    if not os.path.exists(d):
        os.makedirs(d, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as f:
        f.write(name + ':' + password + '\n')


def readSecret(name):
    content = mw.readFile(secretsFile(name)) or ''
    line = content.strip().split('\n')[0] if content else ''
    if ':' in line:
        return line.split(':', 1)[1]
    return ''


def getLog():
    return getServerDir() + '/rsyncd.log'


def writeRsyncdConf(data=None):
    if data is None:
        data = getConfig()
    d = data['receive']['default']
    lines = [
        '# 由 PM 面板根据 config.json 自动生成, 请在面板中修改',
        'uid = %s' % d.get('uid', 'www'),
        'gid = %s' % d.get('gid', 'www'),
        # 开启 chroot: 规避 CVE-2026-29518 / CVE-2026-43619 等 "use chroot = no" 下的符号链接竞争漏洞
        'use chroot = yes',
        'port = %d' % int(d.get('port', 873)),
        'max connections = %d' % int(d.get('max connections', 100)),
        'timeout = %d' % int(d.get('timeout', 600)),
        'log file = %s' % getLog(),
        'pid file = /var/run/rsyncd.pid',
        'list = false',
        'reverse lookup = no',
        'strict modes = yes',
        'dont compress = *.gz *.tgz *.zip *.z *.Z *.rpm *.deb *.bz2 *.xz *.zst *.mp4 *.avi *.rar *.7z',
        '',
    ]
    for m in data['receive']['list']:
        lines.append('[%s]' % m['name'])
        lines.append('path = %s' % m['path'])
        if m.get('comment'):
            lines.append('comment = %s' % m['comment'])
        lines.append('auth users = %s' % m['name'])
        lines.append('secrets file = %s' % secretsFile(m['name']))
        lines.append('read only = %s' % ('true' if m.get('read_only') else 'false'))
        lines.append('ignore errors = yes')
        if m.get('hosts'):
            lines.append('hosts allow = %s' % ' '.join(m['hosts']))
            lines.append('hosts deny = *')
        elif not m.get('open_all'):
            # 未设置允许的IP时只允许本机, 避免对公网开放
            lines.append('hosts allow = 127.0.0.1 ::1')
            lines.append('hosts deny = *')
        lines.append('')
    path = appConf()
    if not os.path.exists(getServerDir()):
        os.makedirs(getServerDir())
    mw.writeFile(path, '\n'.join(lines))
    os.chmod(path, 0o644)


# ------------------------------- 服务管理(命令行) -------------------------------

def systemctl(*args):
    p = subprocess.run(['systemctl'] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.returncode == 0


def installService(name, tpl, mapping):
    content = mw.readFile(getPluginDir() + '/init.d/' + tpl) or ''
    for k, v in mapping.items():
        content = content.replace(k, v)
    # 写入 /etc/systemd/system: 优先级高于发行版软件包自带的 unit, 卸载时也不会删掉系统包的文件
    path = '/etc/systemd/system/' + name + '.service'
    if mw.readFile(path) != content:
        mw.writeFile(path, content)
        systemctl('daemon-reload')


def initDreplace():
    data = getConfig()
    writeRsyncdConf(data)
    writeLsyncdConf(data, reload_service=False)
    if not mw.isAppleSystem():
        installService('rsyncd', 'rsyncd.service.tpl', {
            '{$SERVER_PATH}': mw.getServerDir(),
            '{$RSYNC_BIN}': rsyncBin(),
        })
        lbin = lsyncdBin()
        if lbin:
            installService('lsyncd', 'lsyncd.service.tpl', {
                '{$SERVER_PATH}': mw.getServerDir(),
                '{$LSYNCD_BIN}': lbin,
            })


def status():
    if mw.isAppleSystem():
        return 'stop'
    return 'start' if systemctl('is-active', '--quiet', 'rsyncd') else 'stop'


def serviceOp(method):
    initDreplace()
    if mw.isAppleSystem():
        return 'fail'
    r = systemctl(method, 'rsyncd')
    if hasSendRealtime():
        systemctl(method, 'lsyncd')
    elif method in ('stop', 'restart'):
        systemctl('stop', 'lsyncd')
    return 'ok' if r else 'fail'


def start():
    return serviceOp('start')


def stop():
    return serviceOp('stop')


def restart():
    return serviceOp('restart')


def reload():
    # rsync 守护进程每次连接都会重新读取配置文件, reload 只需刷新配置
    initDreplace()
    if hasSendRealtime():
        systemctl('restart', 'lsyncd')
    return 'ok'


def initdStatus():
    if mw.isAppleSystem():
        return "Apple Computer does not support"
    return 'ok' if systemctl('is-enabled', '--quiet', 'rsyncd') else 'fail'


def initdInstall():
    if mw.isAppleSystem():
        return "Apple Computer does not support"
    systemctl('enable', 'rsyncd')
    if hasSendRealtime():
        systemctl('enable', 'lsyncd')
    return 'ok'


def initdUinstall():
    if mw.isAppleSystem():
        return "Apple Computer does not support"
    systemctl('disable', 'rsyncd')
    systemctl('disable', 'lsyncd')
    return 'ok'


def restartIfRunning():
    if status() == 'start':
        # rsyncd 每个连接都会重新读取配置, 无需重启; lsyncd 需要重启
        pass
    if hasSendRealtime():
        if systemctl('is-active', '--quiet', 'lsyncd'):
            systemctl('restart', 'lsyncd')
        else:
            systemctl('start', 'lsyncd')
    else:
        systemctl('stop', 'lsyncd')


# ------------------------------- 概览 -------------------------------------------

def firewallHasPort(port):
    try:
        return mw.M('firewall').where('port=?', (str(port),)).count() > 0
    except Exception:
        return False


def get_info(args=None):
    binary = rsyncBin()
    ver = binVersion(binary)
    own = binary == getServerDir() + '/bin/rsync'
    data = getConfig()
    port = int(data['receive']['default'].get('port', 873))
    open_all = [m['name'] for m in data['receive']['list'] if m.get('open_all')]
    info = {
        'rsync_bin': binary,
        'rsync_version': ver,
        'rsync_own_build': own,
        'rsync_target': RSYNC_VERSION,
        'rsync_outdated': ver != '' and versionTuple(ver) < RSYNC_MIN_SAFE,
        'lsyncd_bin': lsyncdBin(),
        'port': port,
        'port_open': firewallHasPort(port),
        'service': status(),
        'open_all_modules': open_all,
        'receive_count': len(data['receive']['list']),
        'send_count': len(data['send']['list']),
    }
    return ok('OK', info)


def open_port(args=None):
    data = getConfig()
    port = str(int(data['receive']['default'].get('port', 873)))
    try:
        from utils.firewall import Firewall as MwFirewall
        MwFirewall.instance().addAcceptPort(port, 'RSYNC同步', 'port')
    except Exception as e:
        return fail('放行端口失败: ' + str(e))
    return ok('已放行端口 ' + port + ', 请确保每个接收目录都设置了允许访问的IP')


# ------------------------------- 接收端 -----------------------------------------

def findByName(lst, name):
    for i, x in enumerate(lst):
        if x.get('name') == name:
            return i
    return -1


def rec_list(args=None):
    data = getConfig()
    res = []
    for m in data['receive']['list']:
        item = dict(m)
        item['has_password'] = readSecret(m['name']) != ''
        res.append(item)
    return ok('OK', res)


def rec_get(args):
    name = (args or {}).get('name', '')
    if name == '':
        return ok('OK', {
            'name': '', 'path': mw.getWwwDir(), 'comment': '', 'hosts': [],
            'read_only': False, 'password': mw.getRandomString(20),
        })
    data = getConfig()
    i = findByName(data['receive']['list'], name)
    if i < 0:
        return fail('接收目录不存在')
    item = dict(data['receive']['list'][i])
    item['password'] = readSecret(name)
    return ok('OK', item)


def rec_save(args):
    args = args or {}
    name = str(args.get('name', '')).strip()
    path = str(args.get('path', '')).strip().rstrip('/') or '/'
    comment = str(args.get('comment', '')).strip()
    password = str(args.get('password', ''))
    hosts = parseHostsAllow(args.get('hosts', ''))
    is_new = str(args.get('is_new', '0')) == '1'

    if not checkName(name):
        return fail('名称只能包含字母、数字、下划线和短横线(1-32位), 且以字母或数字开头')
    if not checkPath(path):
        return fail('目录路径不正确(必须是绝对路径, 不能是系统目录)')
    if not checkText(comment):
        return fail('备注不能超过200个字符, 且不能包含换行')
    if not checkPassword(password):
        return fail('密码长度为8-128位, 不能包含冒号和换行')
    if hosts is None:
        return fail('允许访问的IP格式不正确, 请填写IP或网段(如 1.2.3.4 或 10.0.0.0/24), 多个用空格分隔')
    if not hosts:
        return fail('请填写允许访问的IP(发送端服务器的IP), 不建议对所有IP开放')

    data = getConfig()
    lst = data['receive']['list']
    i = findByName(lst, name)
    if is_new and i >= 0:
        return fail('名称已存在')
    for x in lst:
        if x['name'] != name and os.path.realpath(x['path']) == os.path.realpath(path):
            return fail('该目录已被接收目录[%s]使用' % x['name'])

    read_only = str(args.get('read_only', 'false')) in ('true', '1', 'True')
    if not os.path.exists(path):
        os.makedirs(path, mode=0o755)
        if not mw.isAppleSystem():
            try:
                import shutil
                shutil.chown(path, 'www', 'www')
            except Exception:
                pass
    elif not read_only and not mw.isAppleSystem():
        # rsync 服务以 www 身份写入文件, 目录所有者不是 www 时会出现 Permission denied
        import pwd
        try:
            owner = pwd.getpwuid(os.stat(path).st_uid).pw_name
        except KeyError:
            owner = str(os.stat(path).st_uid)
        if owner != 'www':
            return fail('目录所有者是 %s, rsync 服务以 www 身份写入会失败。请先在终端执行: chown -R www:www %s' % (owner, shlex.quote(path)))

    item = {
        'name': name,
        'path': path,
        'comment': comment,
        'hosts': hosts,
        'read_only': read_only,
        'open_all': False,
        'add_time': lst[i]['add_time'] if i >= 0 else int(time.time()),
    }
    if i >= 0:
        lst[i] = item
    else:
        lst.append(item)
    writeSecret(name, password)
    saveConfig(data)
    writeRsyncdConf(data)
    return ok('保存成功')


def rec_delete(args):
    name = (args or {}).get('name', '')
    if not checkName(name):
        return fail('参数错误')
    data = getConfig()
    i = findByName(data['receive']['list'], name)
    if i < 0:
        return fail('接收目录不存在')
    data['receive']['list'].pop(i)
    saveConfig(data)
    writeRsyncdConf(data)
    d = os.path.dirname(secretsFile(name))
    if os.path.isdir(d):
        import shutil
        shutil.rmtree(d, ignore_errors=True)
    return ok('删除成功')


def rec_client_cmd(args):
    '''生成发送端使用的连接密钥和手动同步命令'''
    name = (args or {}).get('name', '')
    data = getConfig()
    i = findByName(data['receive']['list'], name)
    if i < 0:
        return fail('接收目录不存在')
    port = int(data['receive']['default'].get('port', 873))
    pwd = readSecret(name)
    key = base64.b64encode(json.dumps({'A': name, 'B': pwd, 'C': str(port)}).encode()).decode()
    ip = mw.getHostAddr() or mw.getLocalIp()
    pass_file = '/root/.rsync_' + name + '.pass'
    cmd = "umask 077 && printf '%s' " + shlex.quote(pwd) + " > " + pass_file + "\n"
    cmd += 'rsync -avzP --port=%d --password-file=%s /要同步的目录/ %s@%s::%s' % (port, pass_file, name, ip, name)
    return ok('OK', {'secret_key': key, 'cmd': cmd})


# ------------------------------- 发送端 -----------------------------------------

def sendDir(name):
    return getServerDir() + '/send/' + name


def hasSendRealtime(data=None):
    if data is None:
        data = getConfig()
    return any(x.get('realtime') for x in data['send']['list'])


def luaStr(s):
    return json.dumps(str(s), ensure_ascii=False)


def buildRsyncArgs(t, binary):
    args = [binary, '-az', '--partial', '--port=' + str(int(t['port']))]
    if int(t.get('bwlimit', 0)) > 0:
        args.append('--bwlimit=' + str(int(t['bwlimit'])))
    if t.get('delete'):
        args.append('--delete')
    if not t.get('compress', True):
        args.remove('-az')
        args.insert(1, '-a')
    args.append('--exclude-from=' + sendDir(t['name']) + '/exclude')
    args.append('--password-file=' + sendDir(t['name']) + '/pass')
    src = t['path'].rstrip('/') + '/'
    args.append(src)
    args.append('%s@%s::%s' % (t['user'], t['ip'], t['module']))
    return args


def writeLsyncdConf(data=None, reload_service=True):
    if data is None:
        data = getConfig()
    binary = rsyncBin()
    d = data['send']['default']
    content = 'settings {\n'
    content += '\tlogfile = ' + luaStr(getServerDir() + '/lsyncd.log') + ',\n'
    content += '\tstatusFile = ' + luaStr(getServerDir() + '/lsyncd.status') + ',\n'
    content += '\tinotifyMode = ' + luaStr(d.get('inotifyMode', 'CloseWrite')) + ',\n'
    content += '\tmaxProcesses = %d,\n' % int(d.get('maxProcesses', 8))
    content += '}\n\n'

    for t in data['send']['list']:
        sd = sendDir(t['name'])
        if not os.path.exists(sd):
            os.makedirs(sd, mode=0o700)
        mw.writeFile(sd + '/exclude', '\n'.join(t.get('exclude', [])) + '\n')
        fd = os.open(sd + '/pass', os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(t['password'])
        # 手动/定时同步脚本: 参数逐个转义, 不受目录名/地址中特殊字符影响
        cmd = '#!/bin/bash\n' + ' '.join(shlex.quote(x) for x in buildRsyncArgs(t, binary)) + '\n'
        mw.writeFile(sd + '/cmd', cmd)
        os.chmod(sd + '/cmd', 0o700)

        if not t.get('realtime'):
            continue
        extra = ['--port=' + str(int(t['port']))]
        if int(t.get('bwlimit', 0)) > 0:
            extra.append('--bwlimit=' + str(int(t['bwlimit'])))
        content += 'sync {\n'
        content += '\tdefault.rsync,\n'
        content += '\tsource = ' + luaStr(t['path'].rstrip('/') + '/') + ',\n'
        content += '\ttarget = ' + luaStr('%s@%s::%s' % (t['user'], t['ip'], t['module'])) + ',\n'
        content += '\tdelete = %s,\n' % ('true' if t.get('delete') else 'false')
        content += '\tdelay = %d,\n' % int(t.get('delay', 3))
        content += '\tinit = false,\n'
        content += '\texclude = {' + ', '.join(luaStr(x) for x in t.get('exclude', [])) + '},\n'
        content += '\trsync = {\n'
        content += '\t\tbinary = ' + luaStr(binary) + ',\n'
        content += '\t\tarchive = true,\n'
        content += '\t\tcompress = %s,\n' % ('true' if t.get('compress', True) else 'false')
        content += '\t\tpassword_file = ' + luaStr(sd + '/pass') + ',\n'
        content += '\t\t_extra = {' + ', '.join(luaStr(x) for x in extra) + '},\n'
        content += '\t}\n'
        content += '}\n\n'

    mw.writeFile(getServerDir() + '/lsyncd.conf', content)
    if reload_service and not mw.isAppleSystem():
        restartIfRunning()
        try:
            import tool_task
            tool_task.createBgTask(data['send']['list'])
        except Exception:
            print(mw.getTracebackInfo())


def send_list(args=None):
    data = getConfig()
    res = []
    for t in data['send']['list']:
        item = dict(t)
        item.pop('password', None)
        res.append(item)
    return ok('OK', res)


def send_get(args):
    name = (args or {}).get('name', '')
    if name == '':
        return ok('OK', {
            'name': '', 'ip': '', 'port': 873, 'module': '', 'user': '', 'password': '',
            'path': mw.getWwwDir(), 'realtime': True, 'delay': 3, 'delete': False,
            'compress': True, 'bwlimit': 0, 'period': 'day', 'hour': 2, 'minute': 30, 'minute_n': 30,
            'exclude': ['**/*.log', '**/*.tmp', '**/*.temp', '.git', '.user.ini', '/**.upload.tmp'],
        })
    data = getConfig()
    i = findByName(data['send']['list'], name)
    if i < 0:
        return fail('同步任务不存在')
    return ok('OK', data['send']['list'][i])


def send_save(args):
    args = args or {}
    name = str(args.get('name', '')).strip()
    is_new = str(args.get('is_new', '0')) == '1'
    key = str(args.get('secret_key', '')).strip()

    module = str(args.get('module', '')).strip()
    user = str(args.get('user', '')).strip()
    password = str(args.get('password', ''))
    port = toInt(args.get('port', 873), 873, 1, 65535)
    if key:
        try:
            m = json.loads(base64.b64decode(key).decode())
            module = user = str(m['A'])
            password = str(m['B'])
            port = toInt(m.get('C', 873), 873, 1, 65535)
        except Exception:
            return fail('接收端密钥格式错误')

    ip = str(args.get('ip', '')).strip()
    path = str(args.get('path', '')).strip().rstrip('/') or '/'
    realtime = str(args.get('realtime', 'true')) in ('true', '1', 'True')
    delete = str(args.get('delete', 'false')) in ('true', '1', 'True')
    compress = str(args.get('compress', 'true')) in ('true', '1', 'True')
    delay = toInt(args.get('delay', 3), 3, 1, 3600)
    bwlimit = toInt(args.get('bwlimit', 0), 0, 0, 10 * 1024 * 1024)
    period = str(args.get('period', 'day'))
    hour = toInt(args.get('hour', 2), 2, 0, 23)
    minute = toInt(args.get('minute', 30), 30, 0, 59)
    minute_n = toInt(args.get('minute_n', 30), 30, 1, 1440)

    if not checkName(name):
        return fail('任务名称只能包含字母、数字、下划线和短横线(1-32位)')
    if not checkHost(ip):
        return fail('接收端服务器地址格式不正确')
    if not checkName(module) or not checkName(user):
        return fail('接收目录名称/用户名格式不正确')
    if not checkPassword(password):
        return fail('密码长度为8-128位, 不能包含冒号和换行')
    if port is None or delay is None or bwlimit is None or hour is None or minute is None or minute_n is None:
        return fail('端口、延迟、限速或定时参数不正确')
    if period not in ('day', 'minute-n'):
        return fail('定时周期不正确')
    if not checkPath(path) or not os.path.isdir(path):
        return fail('同步目录不存在或不允许同步')

    data = getConfig()
    lst = data['send']['list']
    i = findByName(lst, name)
    if is_new and i >= 0:
        return fail('任务名称已存在')

    exclude = lst[i].get('exclude') if i >= 0 else send_get({'name': ''})['data']['exclude']
    item = {
        'name': name, 'ip': ip, 'port': port, 'module': module, 'user': user, 'password': password,
        'path': path, 'realtime': realtime, 'delay': delay, 'delete': delete, 'compress': compress,
        'bwlimit': bwlimit, 'period': period, 'hour': hour, 'minute': minute, 'minute_n': minute_n,
        'exclude': exclude,
    }
    if realtime and not lsyncdBin():
        return fail('未安装 lsyncd, 无法使用实时同步, 请改用定时同步或重新安装插件')
    if i >= 0:
        lst[i] = item
    else:
        lst.append(item)
    saveConfig(data)
    writeLsyncdConf(data)
    return ok('保存成功')


def send_delete(args):
    name = (args or {}).get('name', '')
    data = getConfig()
    i = findByName(data['send']['list'], name)
    if i < 0:
        return fail('同步任务不存在')
    data['send']['list'].pop(i)
    saveConfig(data)
    writeLsyncdConf(data)
    if checkName(name) and os.path.isdir(sendDir(name)):
        import shutil
        shutil.rmtree(sendDir(name), ignore_errors=True)
    return ok('删除成功')


def send_run(args):
    name = (args or {}).get('name', '')
    if not checkName(name) or not os.path.exists(sendDir(name) + '/cmd'):
        return fail('同步任务不存在')
    log = open(sendDir(name) + '/run.log', 'ab')
    log.write(('\n===== %s 手动同步 =====\n' % time.strftime('%Y-%m-%d %H:%M:%S')).encode())
    log.flush()
    subprocess.Popen(['bash', sendDir(name) + '/cmd'], stdout=log, stderr=subprocess.STDOUT,
                     stdin=subprocess.DEVNULL, start_new_session=True)
    log.close()
    return ok('已开始同步, 可在日志中查看进度')


def send_log(args):
    name = (args or {}).get('name', '')
    if name == '__lsyncd__':
        path = getServerDir() + '/lsyncd.log'
    elif checkName(name):
        path = sendDir(name) + '/run.log'
    else:
        return fail('参数错误')
    return ok('OK', mw.getLastLine(path, 300) if os.path.exists(path) else '')


def send_set_exclude(args):
    args = args or {}
    name = args.get('name', '')
    exclude = args.get('exclude', [])
    if isinstance(exclude, str):
        exclude = [x.strip() for x in exclude.split('\n') if x.strip()]
    if not isinstance(exclude, list) or len(exclude) > 200:
        return fail('排除规则格式不正确')
    for x in exclude:
        if not checkText(x, 255) or '"' in x:
            return fail('排除规则不能包含换行或双引号: ' + str(x)[:50])
    data = getConfig()
    i = findByName(data['send']['list'], name)
    if i < 0:
        return fail('同步任务不存在')
    data['send']['list'][i]['exclude'] = exclude
    saveConfig(data)
    writeLsyncdConf(data)
    return ok('保存成功')


def rec_log(args=None):
    path = getLog()
    return ok('OK', mw.getLastLine(path, 300) if os.path.exists(path) else '')


def runInfo():
    return json.dumps(get_info()['data'])


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
    elif func == 'initd_status':
        print(initdStatus())
    elif func == 'initd_install':
        print(initdInstall())
    elif func == 'initd_uninstall':
        print(initdUinstall())
    elif func == 'conf':
        print(appConf())
    elif func == 'run_log':
        print(getLog())
    elif func == 'init':
        initDreplace()
        print('ok')
    else:
        print('error')
