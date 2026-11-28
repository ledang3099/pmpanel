# coding:utf-8

# ---------------------------------------------------------------------------------
# PM-Linux面板
# ---------------------------------------------------------------------------------
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------

# SSH 管理: 服务状态/控制、sshd 配置、登录日志与统计
#
# 配置写入原则:
#   sshd 对同一配置项"先出现者生效"。主配置通常在开头 Include /etc/ssh/sshd_config.d/*.conf,
#   且发行版自带的 50-cloud-init.conf 等会覆盖主配置。因此若存在 Include, 面板的设置写入
#   排序最靠前的 sshd_config.d/00-pmpanel.conf; 否则直接修改主配置。
#   每次修改都用 `sshd -t` 校验, 失败则还原, 不会因为配置错误导致 SSH 无法启动。

import os
import re
import gzip
import time
import shutil
import datetime
import ipaddress
import subprocess

import core.mw as mw

SSHD_CONFIG = '/etc/ssh/sshd_config'
DROPIN_DIR = '/etc/ssh/sshd_config.d'
DROPIN_FILE = DROPIN_DIR + '/00-pmpanel.conf'

# 允许面板修改的配置项及取值校验
ALLOWED = {
    'Port': lambda v: re.fullmatch(r'\d{1,5}', v) and 1 <= int(v) <= 65535,
    'PermitRootLogin': lambda v: v in ('yes', 'no', 'prohibit-password'),
    'PasswordAuthentication': lambda v: v in ('yes', 'no'),
    'PubkeyAuthentication': lambda v: v in ('yes', 'no'),
    'MaxAuthTries': lambda v: re.fullmatch(r'\d{1,2}', v) and 1 <= int(v) <= 20,
}

# 端口冲突检查(常用服务端口)
RESERVED_PORTS = ('21', '25', '80', '443', '888', '3306', '6379')

LOG_FILES = ['/var/log/auth.log', '/var/log/secure']

MONTHS = {m: i for i, m in enumerate(
    ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'], 1)}

RE_ISO = re.compile(r'^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})\S*\s+\S+\s+(sshd(?:-session)?)\[\d+\]:\s+(.*)$')
RE_BSD = re.compile(r'^([A-Z][a-z]{2})\s+(\d{1,2})\s+(\d{2}:\d{2}:\d{2})\s+\S+\s+(sshd(?:-session)?)\[\d+\]:\s+(.*)$')
RE_ACCEPT = re.compile(r'^Accepted (\S+) for (\S+) from (\S+) port (\d+)')
RE_FAIL = re.compile(r'^Failed (\S+) for (invalid user )?(\S+) from (\S+) port (\d+)')
RE_INVALID = re.compile(r'^Invalid user (\S*) from (\S+) port (\d+)')

METHOD_NAME = {
    'password': '密码',
    'publickey': '密钥',
    'keyboard-interactive/pam': '密码',
    'none': '无',
    'gssapi-with-mic': 'GSSAPI',
}


def run(cmd, input_data=None, timeout=30):
    '''执行命令(参数列表, 不经过 shell), 返回 (returncode, stdout, stderr)'''
    try:
        p = subprocess.run(cmd, input=input_data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=timeout, text=True)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, '', cmd[0] + ': not found'
    except subprocess.TimeoutExpired:
        return 124, '', 'timeout'


def which(name):
    for d in ('/usr/sbin', '/usr/bin', '/sbin', '/bin', '/usr/local/sbin', '/usr/local/bin'):
        if os.access(d + '/' + name, os.X_OK):
            return d + '/' + name
    return shutil.which(name) or ''


def hasSystemd():
    return os.path.isdir('/run/systemd/system')


def ok(msg='OK', data=None):
    return mw.returnData(True, msg, data)


def fail(msg, data=None):
    return mw.returnData(False, msg, data)


class SshManage(object):

    __instance = None
    # 日志解析缓存: {文件: (mtime, size, records)}
    __log_cache = {}

    @classmethod
    def instance(cls):
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    # ------------------------------- 服务 ---------------------------------------

    def sshdBin(self):
        return which('sshd')

    def unitName(self):
        if not hasSystemd():
            return ''
        code, out, _ = run(['systemctl', 'list-unit-files', 'ssh.service', 'sshd.service', '--no-legend'])
        names = [line.split()[0] for line in out.splitlines() if line.strip()]
        if 'ssh.service' in names:
            return 'ssh'
        if 'sshd.service' in names:
            return 'sshd'
        return ''

    def socketActive(self):
        '''Ubuntu 22.10+ 默认通过 ssh.socket 监听端口'''
        if not hasSystemd():
            return False
        code, out, _ = run(['systemctl', 'is-active', 'ssh.socket'])
        return out.strip() == 'active'

    def listenerPid(self):
        '''sshd 主进程(listener) 的 pid'''
        for pidfile in ('/run/sshd.pid', '/var/run/sshd.pid'):
            pid = (mw.readFile(pidfile) or '').strip()
            if pid.isdigit() and os.path.exists('/proc/' + pid):
                return int(pid)
        for d in os.listdir('/proc'):
            if not d.isdigit():
                continue
            try:
                with open('/proc/' + d + '/cmdline', 'rb') as f:
                    cmd = f.read().split(b'\0')
                with open('/proc/' + d + '/stat') as f:
                    st = f.read()
                ppid = st[st.rfind(')') + 2:].split()[1]
            except (IOError, OSError, IndexError):
                continue
            exe = os.path.basename(cmd[0].decode('utf-8', 'ignore')) if cmd and cmd[0] else ''
            if exe == 'sshd' and (ppid == '1' or b'-D' in cmd or len(cmd) <= 2):
                # 排除每个连接派生的子进程(其父进程为 sshd)
                try:
                    with open('/proc/' + ppid + '/cmdline', 'rb') as f:
                        parent = os.path.basename(f.read().split(b'\0')[0].decode('utf-8', 'ignore'))
                except (IOError, OSError):
                    parent = ''
                if parent != 'sshd':
                    return int(d)
        return 0

    def isRunning(self):
        if self.listenerPid():
            return True
        return self.socketActive()

    def service(self, action):
        if action not in ('start', 'stop', 'restart', 'reload'):
            return fail('参数错误')
        unit = self.unitName()
        if unit:
            if self.socketActive() and action in ('start', 'stop', 'restart'):
                code, out, err = run(['systemctl', action, 'ssh.socket'])
                if code != 0:
                    return fail('操作失败: ' + (err or out).strip()[-300:])
                if action == 'stop':
                    run(['systemctl', 'stop', unit])
                return ok('操作成功')
            code, out, err = run(['systemctl', action, unit])
            if code != 0:
                return fail('操作失败: ' + (err or out).strip()[-300:])
            return ok('操作成功')

        # 无 systemd: 直接管理 sshd 进程
        pid = self.listenerPid()
        if action in ('stop', 'restart') and pid:
            try:
                os.kill(pid, 15)
            except OSError as e:
                return fail('停止失败: ' + str(e))
            for _ in range(30):
                if not os.path.exists('/proc/%d' % pid):
                    break
                time.sleep(0.1)
        if action == 'reload':
            if not pid:
                return fail('SSH 服务未运行')
            os.kill(pid, 1)
            return ok('操作成功')
        if action in ('start', 'restart'):
            if self.listenerPid():
                return ok('操作成功')
            sshd = self.sshdBin()
            if not sshd:
                return fail('未找到 sshd, 请先安装 openssh-server')
            os.makedirs('/run/sshd', mode=0o755, exist_ok=True)
            code, out, err = run([sshd])
            if code != 0:
                return fail('启动失败: ' + (err or out).strip()[-300:])
        return ok('操作成功')

    # ------------------------------- 配置 ---------------------------------------

    def effective(self):
        '''sshd 实际生效的配置(sshd -T), 失败时退回解析配置文件'''
        sshd = self.sshdBin()
        if sshd:
            code, out, _ = run([sshd, '-T'])
            if code == 0 and out:
                conf = {}
                for line in out.splitlines():
                    parts = line.split(None, 1)
                    if len(parts) == 2:
                        key = parts[0].lower()
                        # port 等可出现多次
                        conf.setdefault(key, parts[1])
                return conf
        return self.parseFiles()

    def configFiles(self):
        files = [SSHD_CONFIG]
        main = mw.readFile(SSHD_CONFIG) or ''
        for m in re.finditer(r'^\s*Include\s+(.+)$', main, re.M | re.I):
            pattern = m.group(1).strip()
            if not pattern.startswith('/'):
                pattern = '/etc/ssh/' + pattern
            import glob
            files.extend(sorted(glob.glob(pattern)))
        return files

    def parseFiles(self):
        '''按 sshd 规则(先出现者生效)解析配置, 不处理 Match 块'''
        conf = {}
        main = mw.readFile(SSHD_CONFIG) or ''
        order = []
        for line in main.splitlines():
            m = re.match(r'^\s*Include\s+(.+)$', line, re.I)
            if m:
                import glob
                pattern = m.group(1).strip()
                if not pattern.startswith('/'):
                    pattern = '/etc/ssh/' + pattern
                for f in sorted(glob.glob(pattern)):
                    order.extend((mw.readFile(f) or '').splitlines())
            else:
                order.append(line)
        for line in order:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if re.match(r'^Match\s', line, re.I):
                break
            parts = line.split(None, 1)
            if len(parts) == 2:
                conf.setdefault(parts[0].lower(), parts[1].strip())
        return conf

    def usesDropin(self):
        main = mw.readFile(SSHD_CONFIG) or ''
        return bool(re.search(r'^\s*Include\s+/etc/ssh/sshd_config\.d/\*\.conf', main, re.M | re.I))

    def getInfo(self):
        conf = self.effective()
        data = {
            'installed': bool(self.sshdBin()) or os.path.exists(SSHD_CONFIG),
            'status': self.isRunning(),
            'port': conf.get('port', '22'),
            # sshd -T 输出旧别名 without-password
            'permit_root_login': {'without-password': 'prohibit-password'}.get(
                conf.get('permitrootlogin', 'prohibit-password'), conf.get('permitrootlogin', 'prohibit-password')),
            'password_auth': conf.get('passwordauthentication', 'yes'),
            'pubkey_auth': conf.get('pubkeyauthentication', 'yes'),
            'max_auth_tries': conf.get('maxauthtries', '6'),
            'config_file': DROPIN_FILE if self.usesDropin() else SSHD_CONFIG,
            'socket': self.socketActive(),
            'version': '',
        }
        code, out, err = run(['ssh', '-V'])
        data['version'] = (err or out).strip().split(',')[0]
        data['ping'] = self.pingAllowed()
        return data

    def pingAllowed(self):
        val = (mw.readFile('/proc/sys/net/ipv4/icmp_echo_ignore_all') or '0').strip()
        return val != '1'

    def setValues(self, values):
        '''写入一组 sshd 配置; 校验失败则还原'''
        for k, v in values.items():
            if k not in ALLOWED or not ALLOWED[k](str(v)):
                return fail('参数不正确: %s' % k)

        if self.usesDropin():
            target = DROPIN_FILE
            old = mw.readFile(target) if os.path.exists(target) else None
            lines = [l for l in (old or '').splitlines() if l.strip()]
            body = [l for l in lines if not l.startswith('#')]
            current = {}
            for l in body:
                parts = l.split(None, 1)
                if len(parts) == 2:
                    current[parts[0]] = parts[1]
            current.update({k: str(v) for k, v in values.items()})
            content = '# 由 PM 面板管理, 优先于其他 sshd_config.d 配置生效\n'
            content += ''.join('%s %s\n' % (k, v) for k, v in current.items())
            os.makedirs(DROPIN_DIR, mode=0o755, exist_ok=True)
        else:
            target = SSHD_CONFIG
            old = mw.readFile(target) or ''
            content = old
            for k, v in values.items():
                rep = re.compile(r'^[ \t]*#?[ \t]*' + k + r'[ \t]+\S.*$', re.M | re.I)
                # 只替换第一处(Match 块前), 其余同名配置注释掉, 避免歧义
                found = [False]

                def repl(m):
                    if found[0]:
                        return m.group(0) if m.group(0).lstrip().startswith('#') else '#' + m.group(0)
                    found[0] = True
                    return '%s %s' % (k, v)
                head, sep, tail = content.partition('\nMatch ')
                head = rep.sub(repl, head)
                if not found[0]:
                    head = '%s %s\n' % (k, v) + head
                content = head + sep + tail

        mw.writeFile(target, content)
        if target == DROPIN_FILE:
            os.chmod(target, 0o644)
        sshd = self.sshdBin()
        if sshd:
            code, out, err = run([sshd, '-t'])
            if code != 0:
                self.__restore(target, old)
                return fail('配置校验失败, 已还原: ' + (err or out).strip()[-300:])
        return ok('设置成功')

    def __restore(self, target, old):
        if old is None:
            if os.path.exists(target):
                os.remove(target)
        else:
            mw.writeFile(target, old)

    def applyAndReload(self, port_changed=False):
        if self.socketActive() and port_changed:
            # ssh.socket 的端口由 sshd_config 生成, 需重新生成并重启 socket
            run(['systemctl', 'daemon-reload'])
            code, out, err = run(['systemctl', 'restart', 'ssh.socket'])
            if code != 0:
                return fail('重启 ssh.socket 失败: ' + (err or out).strip()[-200:])
            return ok('设置成功')
        if not self.isRunning():
            return ok('设置成功(SSH 服务未运行, 启动后生效)')
        r = self.service('reload' if not port_changed else 'restart')
        if not r['status']:
            return r
        self.waitListening()
        return ok('设置成功')

    def waitListening(self, timeout=8):
        '''sshd 重载/重启时会短暂关闭监听端口, 等待其恢复后再返回'''
        import socket
        port = int(self.effective().get('port', '22') or 22)
        end = time.time() + timeout
        while time.time() < end:
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=1) as sock:
                    sock.settimeout(1)
                    if sock.recv(8).startswith(b'SSH-'):
                        return True
            except (OSError, socket.timeout):
                pass
            time.sleep(0.2)
        return False

    def setPort(self, port):
        port = str(port).strip()
        if not ALLOWED['Port'](port):
            return fail('端口范围必须在 1-65535 之间')
        if port in RESERVED_PORTS:
            return fail('端口 %s 为常用服务端口, 请更换' % port)
        old_port = self.effective().get('port', '22')
        if port == old_port:
            return ok('端口未变化')
        # 先在防火墙放行新端口, 放行失败则不修改, 避免改完后无法连接
        try:
            from utils.firewall import Firewall
            fr = Firewall.instance().ensurePortOpen(port, 'SSH端口')
        except Exception as e:
            fr = fail('防火墙放行新端口出错: %s' % e)
        if not fr['status']:
            return fail('%s, 已取消修改 SSH 端口, 请先检查防火墙' % fr['msg'])
        r = self.setValues({'Port': port})
        if not r['status']:
            return r
        r = self.applyAndReload(port_changed=True)
        if r['status']:
            mw.writeLog('SSH管理', 'SSH 端口由 %s 修改为 %s' % (old_port, port))
        return r

    def setOption(self, key, value, force=False):
        value = str(value).strip()
        if key not in ('PermitRootLogin', 'PasswordAuthentication', 'PubkeyAuthentication', 'MaxAuthTries'):
            return fail('参数错误')
        if not ALLOWED[key](value):
            return fail('取值不正确')
        conf = self.effective()
        pwd = conf.get('passwordauthentication', 'yes')
        key_on = conf.get('pubkeyauthentication', 'yes')
        if key == 'PasswordAuthentication':
            pwd = value
        if key == 'PubkeyAuthentication':
            key_on = value
        if pwd == 'no' and key_on == 'no':
            return fail('不能同时关闭密码登录和密钥登录, 否则将无法通过 SSH 登录服务器')
        if key == 'PasswordAuthentication' and value == 'no' and not force:
            from utils.sys_user import SysUser
            if not SysUser.instance().anyAuthorizedKeys():
                return fail('当前没有任何账号配置 SSH 公钥, 关闭密码登录后将无法登录。请先在"系统账号"中添加密钥',
                            {'need_force': True})
        if key == 'PermitRootLogin' and value == 'prohibit-password' and not force:
            from utils.sys_user import SysUser
            if not SysUser.instance().listKeys('root').get('data'):
                return fail('root 账号尚未配置 SSH 公钥, 设为"仅密钥登录"后 root 将无法用密码登录',
                            {'need_force': True})
        r = self.setValues({key: value})
        if not r['status']:
            return r
        r = self.applyAndReload()
        if r['status']:
            mw.writeLog('SSH管理', '设置 %s 为 %s' % (key, value))
        return r

    def setPing(self, allow):
        val = '0' if allow else '1'
        conf_file = '/etc/sysctl.d/90-pmpanel-ping.conf'
        mw.writeFile(conf_file, 'net.ipv4.icmp_echo_ignore_all = %s\n' % val)
        # 兼容旧版写在 /etc/sysctl.conf 的配置
        old = mw.readFile('/etc/sysctl.conf') or ''
        if 'icmp_echo_ignore_all' in old:
            mw.writeFile('/etc/sysctl.conf', re.sub(r'^.*icmp_echo_ignore_all.*\n?', '', old, flags=re.M))
        try:
            with open('/proc/sys/net/ipv4/icmp_echo_ignore_all', 'w') as f:
                f.write(val)
        except (IOError, OSError) as e:
            return fail('设置失败: ' + str(e))
        mw.writeLog('SSH管理', '允许 Ping' if allow else '禁止 Ping')
        return ok('设置成功')

    # ------------------------------- 登录日志 ------------------------------------

    def __parseLine(self, line, year_now):
        m = RE_ISO.match(line)
        if m:
            ts = m.group(1) + ' ' + m.group(2)
            msg = m.group(4)
        else:
            m = RE_BSD.match(line)
            if not m:
                return None
            mon = MONTHS.get(m.group(1))
            if not mon:
                return None
            ts = '%04d-%02d-%02d %s' % (year_now, mon, int(m.group(2)), m.group(3))
            msg = m.group(5)
        a = RE_ACCEPT.match(msg)
        if a:
            return {'time': ts, 'status': 1, 'method': a.group(1), 'user': a.group(2),
                    'ip': a.group(3), 'port': a.group(4)}
        f = RE_FAIL.match(msg)
        if f:
            return {'time': ts, 'status': 0, 'method': f.group(1), 'user': f.group(3),
                    'ip': f.group(4), 'port': f.group(5), 'invalid': bool(f.group(2))}
        return None

    def __fixYear(self, records):
        # 传统 syslog 格式没有年份: 若时间晚于现在, 视为去年
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for r in records:
            if r['time'] > now:
                r['time'] = str(int(r['time'][:4]) - 1) + r['time'][4:]

    def __readFile(self, path):
        try:
            st = os.stat(path)
        except OSError:
            return []
        key = (st.st_mtime, st.st_size)
        cached = self.__log_cache.get(path)
        if cached and cached[0] == key:
            return cached[1]
        year_now = datetime.datetime.fromtimestamp(st.st_mtime).year
        records = []
        opener = gzip.open if path.endswith('.gz') else open
        try:
            with opener(path, 'rt', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if 'sshd' not in line or ('Accepted ' not in line and 'Failed ' not in line):
                        continue
                    r = self.__parseLine(line.rstrip('\n'), year_now)
                    if r:
                        records.append(r)
        except (IOError, OSError, EOFError):
            return []
        self.__fixYear(records)
        self.__log_cache[path] = (key, records)
        return records

    def __readJournal(self):
        if not which('journalctl'):
            return []
        code, out, _ = run(['journalctl', '--no-pager', '-q', '-o', 'short-iso',
                            '_COMM=sshd', '_COMM=sshd-session', '--since', '-90d'], timeout=60)
        if code != 0:
            return []
        year_now = datetime.datetime.now().year
        records = []
        for line in out.splitlines():
            if 'Accepted ' not in line and 'Failed ' not in line:
                continue
            # short-iso: 2026-11-27T09:14:03+0000 host sshd[123]: msg
            r = self.__parseLine(line, year_now)
            if r:
                records.append(r)
        return records

    def logSources(self):
        files = []
        for base in LOG_FILES:
            if os.path.exists(base):
                files.append(base)
                for i in range(1, 8):
                    for cand in ('%s.%d' % (base, i), '%s.%d.gz' % (base, i)):
                        if os.path.exists(cand):
                            files.append(cand)
        return files

    def records(self):
        files = self.logSources()
        res = []
        if files:
            for f in files:
                res.extend(self.__readFile(f))
        else:
            res = self.__readJournal()
        res.sort(key=lambda r: r['time'], reverse=True)
        return res

    def getLogs(self, page=1, limit=20, status='all', search=''):
        try:
            page = max(1, int(page))
            limit = max(1, min(100, int(limit)))
        except ValueError:
            page, limit = 1, 20
        rows = self.records()
        if status == 'success':
            rows = [r for r in rows if r['status'] == 1]
        elif status == 'fail':
            rows = [r for r in rows if r['status'] == 0]
        search = (search or '').strip()
        if search:
            rows = [r for r in rows if search in r['ip'] or search in r['user']]
        total = len(rows)
        items = []
        for r in rows[(page - 1) * limit: page * limit]:
            item = dict(r)
            item['method_name'] = METHOD_NAME.get(r['method'], r['method'])
            items.append(item)
        return ok('OK', {
            'list': items,
            'total': total,
            'page': page,
            'limit': limit,
            'source': ', '.join(self.logSources()) or 'journald',
        })

    def getStats(self):
        rows = self.records()
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        stats = {
            'success_total': 0, 'fail_total': 0,
            'success_today': 0, 'fail_today': 0,
            'fail_ip_count': 0, 'top_fail_ips': [],
            'last_success': None,
        }
        fail_ips = {}
        for r in rows:
            is_today = r['time'].startswith(today)
            if r['status'] == 1:
                stats['success_total'] += 1
                if is_today:
                    stats['success_today'] += 1
                if stats['last_success'] is None:
                    stats['last_success'] = r
            else:
                stats['fail_total'] += 1
                if is_today:
                    stats['fail_today'] += 1
                item = fail_ips.setdefault(r['ip'], {'ip': r['ip'], 'count': 0, 'last': r['time'], 'users': set()})
                item['count'] += 1
                item['users'].add(r['user'])
        stats['fail_ip_count'] = len(fail_ips)
        top = sorted(fail_ips.values(), key=lambda x: x['count'], reverse=True)[:10]
        blocked = self.blockedIps()
        for t in top:
            t['users'] = sorted(t['users'])[:5]
            t['blocked'] = t['ip'] in blocked
        stats['top_fail_ips'] = top
        stats['source'] = ', '.join(self.logSources()) or 'journald'
        return ok('OK', stats)

    def blockedIps(self):
        try:
            from utils.firewall import Firewall
            return Firewall.instance().getBlockedIps()
        except Exception:
            return set()

    def blockIp(self, ip):
        ip = str(ip).strip()
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return fail('IP 地址不正确')
        if addr.is_loopback:
            return fail('不能屏蔽本机地址')
        from utils.firewall import Firewall
        r = Firewall.instance().addBlockIp(ip, 'SSH 登录失败过多')
        if r.get('status'):
            mw.writeLog('SSH管理', '屏蔽 SSH 爆破 IP ' + ip)
        return r

    def clearLogsCache(self):
        self.__log_cache.clear()
