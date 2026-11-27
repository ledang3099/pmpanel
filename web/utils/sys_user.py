# coding:utf-8

# ---------------------------------------------------------------------------------
# PM-Linux面板
# ---------------------------------------------------------------------------------
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------

# 系统账号管理: 列表、新建、改密码、锁定、登录 Shell、sudo 权限、删除、SSH 公钥
#
# 安全约束:
#   - 所有命令以参数列表执行, 不经过 shell; 密码通过 stdin 传给 chpasswd, 不出现在进程参数中
#   - root 及系统账号(uid < 1000)不可删除/锁定/修改 Shell; 面板运行账号 www 不可删除
#   - 写 ~/.ssh/authorized_keys 时拒绝符号链接(防止普通用户把它链接到 /etc/shadow 等文件)

import os
import re
import pwd
import grp
import stat
import time
import tempfile
import subprocess

import core.mw as mw

NAME_RE = re.compile(r'^[a-z_][a-z0-9_-]{0,30}$')
PROTECTED = ('root', 'www', 'nobody', 'sshd', 'daemon', 'bin', 'sys')
NOLOGIN = ('/usr/sbin/nologin', '/sbin/nologin', '/bin/false', '/usr/bin/false')
KEY_TYPES = ('ssh-ed25519', 'ssh-rsa', 'ecdsa-sha2-nistp256', 'ecdsa-sha2-nistp384',
             'ecdsa-sha2-nistp521', 'sk-ssh-ed25519@openssh.com', 'sk-ecdsa-sha2-nistp256@openssh.com')


def run(cmd, input_data=None, timeout=60):
    try:
        p = subprocess.run(cmd, input=input_data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=timeout, text=True)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, '', cmd[0] + ': 命令不存在'
    except subprocess.TimeoutExpired:
        return 124, '', '执行超时'


def ok(msg='OK', data=None):
    return mw.returnData(True, msg, data)


def fail(msg, data=None):
    return mw.returnData(False, msg, data)


class SysUser(object):

    __instance = None

    @classmethod
    def instance(cls):
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    # ------------------------------- 工具 ---------------------------------------

    def adminGroup(self):
        for g in ('sudo', 'wheel'):
            try:
                grp.getgrnam(g)
                return g
            except KeyError:
                continue
        return ''

    def shells(self):
        res = []
        for line in (mw.readFile('/etc/shells') or '').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and os.path.exists(line) and line not in res:
                res.append(line)
        for s in ('/bin/bash', '/bin/sh'):
            if os.path.exists(s) and s not in res:
                res.append(s)
        nologin = self.nologin()
        if nologin not in res:
            res.append(nologin)
        return res

    def nologin(self):
        for s in NOLOGIN:
            if os.path.exists(s):
                return s
        return '/usr/sbin/nologin'

    def shadow(self):
        res = {}
        for line in (mw.readFile('/etc/shadow') or '').splitlines():
            parts = line.split(':')
            if len(parts) >= 8:
                res[parts[0]] = parts
        return res

    def getUser(self, name):
        name = str(name or '').strip()
        if not NAME_RE.match(name) and name != 'root':
            return None
        try:
            return pwd.getpwnam(name)
        except KeyError:
            return None

    def uidRange(self):
        lo, hi = 1000, 60000
        for line in (mw.readFile('/etc/login.defs') or '').splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1].isdigit():
                if parts[0] == 'UID_MIN':
                    lo = int(parts[1])
                elif parts[0] == 'UID_MAX':
                    hi = int(parts[1])
        return lo, hi

    def isManageable(self, pw):
        '''普通账号(UID_MIN <= uid <= UID_MAX) 允许完整管理'''
        lo, hi = self.uidRange()
        return lo <= pw.pw_uid <= hi and pw.pw_name not in PROTECTED

    def lastLogins(self):
        '''从 SSH 登录日志中取各账号最近一次成功登录'''
        res = {}
        try:
            from utils.ssh_manage import SshManage
            for r in SshManage.instance().records():
                if r['status'] == 1 and r['user'] not in res:
                    res[r['user']] = {'time': r['time'], 'ip': r['ip']}
        except Exception:
            pass
        return res

    # ------------------------------- 列表 ---------------------------------------

    def getList(self, show_system=False):
        sh = self.shadow()
        admin = self.adminGroup()
        admins = set()
        if admin:
            admins = set(grp.getgrnam(admin).gr_mem)
        last = self.lastLogins()
        res = []
        for pw in sorted(pwd.getpwall(), key=lambda p: p.pw_uid):
            sp = sh.get(pw.pw_name, [])
            passwd_field = sp[1] if len(sp) > 1 else ''
            expire = sp[7] if len(sp) > 7 else ''
            has_password = passwd_field.lstrip('!') not in ('', '*')
            # 服务账号: 不能登录、没有密码、也没有 /home 下的主目录(如 nixbld、软件包创建的账号)
            service = pw.pw_shell in NOLOGIN and not has_password and not pw.pw_dir.startswith('/home/')
            system = not (pw.pw_uid == 0 or (self.isManageable(pw) and not service))
            if system and not show_system:
                continue
            expired = expire.isdigit() and int(expire) <= int(time.time() / 86400)
            # Ubuntu 新建账号的密码字段为单个 "!"(未设置密码), 不算锁定; usermod -L 会在哈希前加 "!"
            locked = (passwd_field.startswith('!') and has_password) or expired
            groups = [g.gr_name for g in grp.getgrall() if pw.pw_name in g.gr_mem]
            try:
                primary = grp.getgrgid(pw.pw_gid).gr_name
            except KeyError:
                primary = str(pw.pw_gid)
            res.append({
                'name': pw.pw_name,
                'uid': pw.pw_uid,
                'gid': pw.pw_gid,
                'group': primary,
                'groups': groups,
                'home': pw.pw_dir,
                'shell': pw.pw_shell,
                'comment': pw.pw_gecos.split(',')[0],
                'login_shell': pw.pw_shell not in NOLOGIN,
                'locked': locked,
                'has_password': has_password,
                'sudo': pw.pw_uid == 0 or pw.pw_name in admins or primary == admin,
                'keys': self.keyCount(pw),
                'system': system,
                'manageable': self.isManageable(pw),
                'last_login': last.get(pw.pw_name),
            })
        return ok('OK', {'list': res, 'shells': self.shells(), 'admin_group': admin})

    # ------------------------------- 增删改 -------------------------------------

    def checkPassword(self, password):
        password = str(password or '')
        if len(password) < 8:
            return '密码长度至少 8 位'
        if len(password) > 128:
            return '密码过长'
        if re.search(r'[\x00-\x1f\x7f:]', password):
            return '密码不能包含控制字符或冒号'
        kinds = sum(bool(re.search(p, password)) for p in (r'[a-z]', r'[A-Z]', r'\d', r'[^A-Za-z0-9]'))
        if kinds < 3:
            return '密码需包含大写字母、小写字母、数字、符号中的至少三种'
        return ''

    def addUser(self, name, password, shell='/bin/bash', sudo=False, comment=''):
        name = str(name or '').strip()
        if not NAME_RE.match(name):
            return fail('用户名只能由小写字母、数字、下划线、连字符组成, 以字母或下划线开头, 最长 31 位')
        try:
            pwd.getpwnam(name)
            return fail('用户已存在')
        except KeyError:
            pass
        try:
            grp.getgrnam(name)
            return fail('已存在同名用户组, 请更换用户名')
        except KeyError:
            pass
        err = self.checkPassword(password)
        if err:
            return fail(err)
        if shell not in self.shells():
            return fail('登录 Shell 不正确')
        comment = re.sub(r'[:,\n\r\x00]', '', str(comment or ''))[:60]
        cmd = ['useradd', '-m', '-s', shell]
        if comment:
            cmd += ['-c', comment]
        cmd.append(name)
        code, out, err = run(cmd)
        if code != 0:
            return fail('创建失败: ' + (err or out).strip()[-200:])
        code, out, err = run(['chpasswd'], input_data='%s:%s\n' % (name, password))
        if code != 0:
            run(['userdel', '-r', name])
            return fail('设置密码失败: ' + (err or out).strip()[-200:])
        if sudo:
            r = self.setSudo(name, True, log=False)
            if not r['status']:
                return r
        mw.writeLog('系统账号', '新建系统账号[%s]' % name)
        return ok('创建成功')

    def setPassword(self, name, password):
        pw = self.getUser(name)
        if not pw:
            return fail('用户不存在')
        if not (pw.pw_uid == 0 or self.isManageable(pw)):
            return fail('系统账号不允许修改密码')
        err = self.checkPassword(password)
        if err:
            return fail(err)
        code, out, err = run(['chpasswd'], input_data='%s:%s\n' % (pw.pw_name, password))
        if code != 0:
            return fail('修改失败: ' + (err or out).strip()[-200:])
        mw.writeLog('系统账号', '修改账号[%s]密码' % pw.pw_name)
        return ok('密码已修改')

    def setLock(self, name, lock):
        pw = self.getUser(name)
        if not pw or not self.isManageable(pw):
            return fail('该账号不允许此操作')
        # -L 锁定密码, -e 1 让账号过期, 使密钥登录也被拒绝
        cmd = ['usermod', '-L', '-e', '1', pw.pw_name] if lock else ['usermod', '-U', '-e', '', pw.pw_name]
        code, out, err = run(cmd)
        if code != 0 and not lock and 'unlocking the user' in (err or ''):
            # 无密码账号无法 -U, 只取消过期
            code, out, err = run(['usermod', '-e', '', pw.pw_name])
        if code != 0:
            return fail('操作失败: ' + (err or out).strip()[-200:])
        mw.writeLog('系统账号', ('锁定' if lock else '解锁') + '账号[%s]' % pw.pw_name)
        return ok('已锁定' if lock else '已解锁')

    def setShell(self, name, shell):
        pw = self.getUser(name)
        if not pw or not self.isManageable(pw):
            return fail('该账号不允许此操作')
        if shell not in self.shells():
            return fail('登录 Shell 不正确')
        code, out, err = run(['usermod', '-s', shell, pw.pw_name])
        if code != 0:
            return fail('操作失败: ' + (err or out).strip()[-200:])
        mw.writeLog('系统账号', '账号[%s]登录 Shell 改为 %s' % (pw.pw_name, shell))
        return ok('设置成功')

    def setSudo(self, name, enable, log=True):
        pw = self.getUser(name)
        if not pw or not self.isManageable(pw):
            return fail('该账号不允许此操作')
        group = self.adminGroup()
        if not group:
            return fail('系统中没有 sudo 或 wheel 用户组, 请先安装 sudo')
        if enable:
            code, out, err = run(['usermod', '-aG', group, pw.pw_name])
        else:
            code, out, err = run(['gpasswd', '-d', pw.pw_name, group])
        if code != 0:
            return fail('操作失败: ' + (err or out).strip()[-200:])
        if log:
            mw.writeLog('系统账号', ('授予' if enable else '取消') + '账号[%s] sudo 权限' % pw.pw_name)
        return ok('设置成功')

    def delUser(self, name, remove_home=False):
        pw = self.getUser(name)
        if not pw or not self.isManageable(pw):
            return fail('root、系统账号及面板运行账号不能删除')
        # 有进程在运行时 userdel 会失败, 提示用户
        code, out, _ = run(['pgrep', '-u', pw.pw_name])
        if out.strip():
            return fail('该账号仍有进程在运行(可能已登录), 请先结束后再删除')
        cmd = ['userdel']
        if remove_home:
            cmd.append('-r')
        cmd.append(pw.pw_name)
        code, out, err = run(cmd)
        # userdel -r 在找不到邮件目录时返回 12, 账号已删除
        if code not in (0, 12):
            return fail('删除失败: ' + (err or out).strip()[-200:])
        mw.writeLog('系统账号', '删除系统账号[%s]%s' % (pw.pw_name, '(含主目录)' if remove_home else ''))
        return ok('已删除')

    # ------------------------------- SSH 公钥 -----------------------------------

    def keyFile(self, pw):
        return os.path.join(pw.pw_dir, '.ssh', 'authorized_keys')

    def __readKeys(self, pw):
        path = self.keyFile(pw)
        try:
            st = os.lstat(path)
        except OSError:
            return []
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
            return []
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read().splitlines()
        except (IOError, OSError):
            return []

    def keyCount(self, pw):
        return len([l for l in self.__readKeys(pw) if l.strip() and not l.strip().startswith('#')])

    def anyAuthorizedKeys(self):
        for pw in pwd.getpwall():
            if pw.pw_shell in NOLOGIN:
                continue
            if (pw.pw_uid == 0 or self.isManageable(pw)) and self.keyCount(pw):
                return True
        return False

    def fingerprint(self, line):
        fd, tmp = tempfile.mkstemp(prefix='pmkey_')
        try:
            with os.fdopen(fd, 'w') as f:
                f.write(line + '\n')
            code, out, err = run(['ssh-keygen', '-l', '-f', tmp])
            if code != 0:
                return None
            parts = out.split()
            # 2048 SHA256:xxxx comment (RSA)
            return {'bits': parts[0], 'fingerprint': parts[1], 'type': parts[-1].strip('()')}
        finally:
            os.remove(tmp)

    def listKeys(self, name):
        pw = self.getUser(name)
        if not pw or not (pw.pw_uid == 0 or self.isManageable(pw)):
            return fail('该账号不允许此操作')
        res = []
        for idx, line in enumerate(self.__readKeys(pw)):
            s = line.strip()
            if not s or s.startswith('#'):
                continue
            info = self.fingerprint(s) or {'bits': '', 'fingerprint': '无法识别', 'type': ''}
            m = re.search(r'(?:^|\s)((?:ssh|ecdsa|sk)-\S+)\s+\S+\s*(.*)$', s)
            info['comment'] = (m.group(2) if m else '')[:80]
            info['line'] = idx
            info['options'] = bool(m and s.index(m.group(1)) > 0)
            res.append(info)
        return ok('OK', res)

    def __writeKeys(self, pw, lines):
        ssh_dir = os.path.join(pw.pw_dir, '.ssh')
        if os.path.islink(pw.pw_dir) and pw.pw_uid != 0:
            return '主目录为符号链接, 拒绝写入'
        if os.path.lexists(ssh_dir):
            if os.path.islink(ssh_dir) or not os.path.isdir(ssh_dir):
                return '~/.ssh 不是普通目录, 拒绝写入'
        else:
            if not os.path.isdir(pw.pw_dir):
                return '主目录不存在'
            os.mkdir(ssh_dir, 0o700)
            os.chown(ssh_dir, pw.pw_uid, pw.pw_gid)
        path = os.path.join(ssh_dir, 'authorized_keys')
        if os.path.lexists(path) and (os.path.islink(path) or not os.path.isfile(path)):
            return 'authorized_keys 不是普通文件, 拒绝写入'
        # 先写临时文件再原子替换, 避免写到一半断开
        fd, tmp = tempfile.mkstemp(prefix='.authorized_keys.', dir=ssh_dir)
        try:
            with os.fdopen(fd, 'w') as f:
                f.write('\n'.join(lines).rstrip('\n') + '\n' if lines else '')
            os.chmod(tmp, 0o600)
            os.chown(tmp, pw.pw_uid, pw.pw_gid)
            os.replace(tmp, path)
        except OSError as e:
            if os.path.exists(tmp):
                os.remove(tmp)
            return '写入失败: ' + str(e)
        os.chmod(ssh_dir, 0o700)
        os.chown(ssh_dir, pw.pw_uid, pw.pw_gid)
        return ''

    def addKey(self, name, key):
        pw = self.getUser(name)
        if not pw or not (pw.pw_uid == 0 or self.isManageable(pw)):
            return fail('该账号不允许此操作')
        key = str(key or '').strip()
        if '\n' in key or '\r' in key:
            return fail('一次只能添加一个公钥(单行)')
        parts = key.split()
        if len(parts) < 2 or parts[0] not in KEY_TYPES:
            return fail('公钥格式不正确, 应以 ssh-ed25519 / ssh-rsa / ecdsa-sha2-* 开头')
        if len(key) > 16384:
            return fail('公钥过长')
        info = self.fingerprint(key)
        if not info:
            return fail('无法识别的公钥')
        if parts[0] == 'ssh-rsa' and info['bits'].isdigit() and int(info['bits']) < 2048:
            return fail('RSA 公钥长度至少 2048 位')
        lines = self.__readKeys(pw)
        for l in lines:
            s = l.strip()
            if s and not s.startswith('#'):
                other = self.fingerprint(s)
                if other and other['fingerprint'] == info['fingerprint']:
                    return fail('该公钥已存在')
        lines.append(key)
        err = self.__writeKeys(pw, lines)
        if err:
            return fail(err)
        mw.writeLog('系统账号', '账号[%s]添加 SSH 公钥 %s' % (pw.pw_name, info['fingerprint']))
        return ok('公钥已添加')

    def delKey(self, name, fingerprint):
        pw = self.getUser(name)
        if not pw or not (pw.pw_uid == 0 or self.isManageable(pw)):
            return fail('该账号不允许此操作')
        lines = self.__readKeys(pw)
        keep = []
        removed = False
        for l in lines:
            s = l.strip()
            if s and not s.startswith('#'):
                info = self.fingerprint(s)
                if info and info['fingerprint'] == fingerprint:
                    removed = True
                    continue
            keep.append(l)
        if not removed:
            return fail('未找到该公钥')
        err = self.__writeKeys(pw, keep)
        if err:
            return fail(err)
        mw.writeLog('系统账号', '账号[%s]删除 SSH 公钥 %s' % (pw.pw_name, fingerprint))
        return ok('公钥已删除')

    def genKey(self, name, key_type='ed25519', passphrase=''):
        '''生成密钥对: 公钥加入 authorized_keys, 私钥只返回一次供下载, 服务器上不保留'''
        pw = self.getUser(name)
        if not pw or not (pw.pw_uid == 0 or self.isManageable(pw)):
            return fail('该账号不允许此操作')
        if key_type not in ('ed25519', 'rsa'):
            return fail('密钥类型不正确')
        passphrase = str(passphrase or '')
        if passphrase and len(passphrase) < 6:
            return fail('私钥密码至少 6 位')
        tmpdir = tempfile.mkdtemp(prefix='pmkeygen_')
        try:
            os.chmod(tmpdir, 0o700)
            keyfile = os.path.join(tmpdir, 'id')
            comment = '%s@pmpanel-%s' % (pw.pw_name, time.strftime('%Y%m%d'))
            cmd = ['ssh-keygen', '-q', '-t', key_type, '-C', comment, '-f', keyfile, '-N', passphrase]
            if key_type == 'rsa':
                cmd[4:4] = ['-b', '4096']
            code, out, err = run(cmd)
            if code != 0:
                return fail('生成失败: ' + (err or out).strip()[-200:])
            private = mw.readFile(keyfile)
            public = (mw.readFile(keyfile + '.pub') or '').strip()
        finally:
            for f in os.listdir(tmpdir):
                os.remove(os.path.join(tmpdir, f))
            os.rmdir(tmpdir)
        r = self.addKey(pw.pw_name, public)
        if not r['status']:
            return r
        return ok('密钥已生成, 请立即下载私钥(服务器不保存私钥)', {
            'private_key': private,
            'public_key': public,
            'filename': '%s_%s_id_%s' % (pw.pw_name, time.strftime('%Y%m%d'), key_type),
        })
