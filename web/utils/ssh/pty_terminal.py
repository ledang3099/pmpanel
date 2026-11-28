# coding:utf-8

# ---------------------------------------------------------------------------------
# PM-Linux面板
# ---------------------------------------------------------------------------------
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------

# 终端栏目: 本机伪终端(pty)会话
#
# - 每个浏览器连接(socket sid)可开多个终端(tid), 互不干扰
# - 不依赖本机 sshd(面板本身以 root 运行, 与文件管理权限一致)
# - 输出由后台线程实时推送, 支持窗口大小调整
# - 浏览器断开时结束对应的 shell 进程组

import os
import pwd
import time
import codecs
import fcntl
import select
import signal
import struct
import termios
import threading
import subprocess

MAX_SESSIONS = 30          # 全局最多同时打开的终端数
MAX_PER_CLIENT = 8         # 每个浏览器页面最多打开的终端数


class PtyTerminal(object):

    __instance = None
    __lock = threading.Lock()

    @classmethod
    def instance(cls):
        if cls.__instance is None:
            with cls.__lock:
                if cls.__instance is None:
                    cls.__instance = cls()
        return cls.__instance

    def __init__(self):
        self.sessions = {}   # (sid, tid) -> {'proc', 'fd', 'thread', 'started'}
        self.lock = threading.Lock()

    @staticmethod
    def __size(cols, rows):
        try:
            cols = max(20, min(500, int(cols)))
            rows = max(5, min(200, int(rows)))
        except (TypeError, ValueError):
            cols, rows = 100, 30
        return cols, rows

    def __setSize(self, fd, cols, rows):
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))

    def open(self, sid, tid, cols, rows, cwd, emit):
        '''
        emit(event, data): 向该浏览器连接推送消息的函数
        返回 (ok, msg)
        '''
        tid = str(tid)[:32]
        key = (sid, tid)
        with self.lock:
            if key in self.sessions:
                return True, 'already open'
            if len(self.sessions) >= MAX_SESSIONS:
                return False, '终端数量已达上限(%d), 请先关闭不用的终端' % MAX_SESSIONS
            if len([k for k in self.sessions if k[0] == sid]) >= MAX_PER_CLIENT:
                return False, '当前页面最多同时打开 %d 个终端' % MAX_PER_CLIENT
        cols, rows = self.__size(cols, rows)
        user = pwd.getpwuid(os.getuid())
        shell = user.pw_shell if os.path.exists(user.pw_shell or '') and 'nologin' not in user.pw_shell else '/bin/bash'
        if not os.path.exists(shell):
            shell = '/bin/sh'
        home = user.pw_dir if os.path.isdir(user.pw_dir) else '/'
        if not cwd or not os.path.isdir(cwd):
            cwd = home
        env = {
            'HOME': home, 'USER': user.pw_name, 'LOGNAME': user.pw_name, 'SHELL': shell,
            'TERM': 'xterm-256color', 'LANG': os.environ.get('LANG') or 'C.UTF-8',
            'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
        }
        master, slave = os.openpty()
        self.__setSize(slave, cols, rows)
        try:
            proc = subprocess.Popen([shell, '-l'], stdin=slave, stdout=slave, stderr=slave, cwd=cwd, env=env,
                                    start_new_session=True, close_fds=True)
        except OSError as e:
            os.close(master)
            os.close(slave)
            return False, '启动终端失败: ' + str(e)
        os.close(slave)
        flags = fcntl.fcntl(master, fcntl.F_GETFL)
        fcntl.fcntl(master, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        sess = {'proc': proc, 'fd': master, 'started': time.time()}
        with self.lock:
            self.sessions[key] = sess
        t = threading.Thread(target=self.__reader, args=(key, sess, emit), daemon=True)
        sess['thread'] = t
        t.start()
        return True, 'ok'

    def __reader(self, key, sess, emit):
        # fd 只由本线程关闭, 避免关闭后编号被新终端复用时读到别人的输出
        fd = sess['fd']
        decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
        try:
            while not sess.get('closed'):
                try:
                    r, _, _ = select.select([fd], [], [], 0.5)
                except (OSError, ValueError):
                    break
                if sess.get('closed'):
                    break
                if not r:
                    if sess['proc'].poll() is not None:
                        break
                    continue
                try:
                    data = os.read(fd, 65536)
                except BlockingIOError:
                    continue
                except OSError:
                    break
                if not data:
                    break
                text = decoder.decode(data)
                if text:
                    emit('pm_term_out', {'tid': key[1], 'data': text})
        finally:
            was_closed = sess.get('closed')
            self.close(key[0], key[1])
            try:
                os.close(fd)
            except OSError:
                pass
            if not was_closed:
                emit('pm_term_exit', {'tid': key[1]})

    def write(self, sid, tid, data):
        sess = self.sessions.get((sid, str(tid)))
        if not sess or not isinstance(data, str):
            return False
        try:
            os.write(sess['fd'], data.encode('utf-8'))
        except OSError:
            return False
        return True

    def resize(self, sid, tid, cols, rows):
        sess = self.sessions.get((sid, str(tid)))
        if not sess:
            return False
        cols, rows = self.__size(cols, rows)
        try:
            self.__setSize(sess['fd'], cols, rows)
            os.killpg(sess['proc'].pid, signal.SIGWINCH)
        except OSError:
            pass
        return True

    def close(self, sid, tid):
        with self.lock:
            sess = self.sessions.pop((sid, str(tid)), None)
        if not sess:
            return
        sess['closed'] = True
        proc = sess['proc']
        try:
            os.killpg(proc.pid, signal.SIGHUP)
        except OSError:
            pass
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass

    def closeClient(self, sid):
        for key in [k for k in list(self.sessions) if k[0] == sid]:
            self.close(key[0], key[1])

    def count(self):
        return len(self.sessions)
