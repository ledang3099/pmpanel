# coding:utf-8

# ---------------------------------------------------------------------------------
# PM-Linux面板
# ---------------------------------------------------------------------------------
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------

# 日志栏目: 面板运行日志、网站日志、计划任务日志、软件日志、系统日志、日志占用与清理
#
# 所有日志文件都通过"名称 -> 路径"白名单定位, 前端只传名称, 不接受任意路径。

import os
import re
import glob
import time

import core.mw as mw

MAX_LINES = 5000
SITE_RE = re.compile(r'^[A-Za-z0-9_.\-]{1,255}$')


def ok(msg='OK', data=None):
    return mw.returnData(True, msg, data)


def fail(msg, data=None):
    return mw.returnData(False, msg, data)


def tail(path, lines=200, search='', max_bytes=32 * 1024 * 1024):
    '''读取文件最后 lines 行; 有关键词时在末尾 max_bytes 范围内过滤'''
    try:
        lines = max(1, min(MAX_LINES, int(lines)))
    except (TypeError, ValueError):
        lines = 200
    if not os.path.isfile(path):
        return {'lines': [], 'size': 0, 'exists': False}
    size = os.path.getsize(path)
    want = lines if not search else MAX_LINES * 50
    with open(path, 'rb') as f:
        f.seek(0, 2)
        end = f.tell()
        pos = end
        data = b''
        while pos > 0 and data.count(b'\n') <= want and end - pos < max_bytes:
            step = min(65536, pos)
            pos -= step
            f.seek(pos)
            data = f.read(step) + data
    text = data.decode('utf-8', 'ignore').split('\n')
    if pos > 0:
        text = text[1:]
    if text and text[-1] == '':
        text = text[:-1]
    if search:
        kw = search.lower()
        text = [l for l in text if kw in l.lower()]
    return {'lines': text[-lines:], 'size': size, 'exists': True, 'mtime': int(os.path.getmtime(path))}


def dirSize(path):
    total = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def truncate(path):
    if not os.path.isfile(path) or os.path.islink(path):
        return False
    with open(path, 'w'):
        pass
    return True


class LogCenter(object):

    __instance = None

    @classmethod
    def instance(cls):
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    # ------------------------------- 面板运行日志 --------------------------------

    def panelFiles(self):
        d = mw.getPanelDir() + '/logs'
        return {
            'panel_error': ('面板错误日志', d + '/panel_error.log'),
            'panel': ('面板运行日志', d + '/panel.log'),
            'panel_task': ('后台任务日志', d + '/panel_task.log'),
            'panel_exec': ('命令执行日志', d + '/panel_exec.log'),
        }

    def panelRun(self, name, lines=200, search=''):
        files = self.panelFiles()
        if name not in files:
            return fail('参数错误')
        r = tail(files[name][1], lines, search)
        r['items'] = [{'name': k, 'title': v[0], 'size': os.path.getsize(v[1]) if os.path.exists(v[1]) else 0}
                      for k, v in files.items()]
        return ok('OK', r)

    def clearPanelRun(self, name):
        files = self.panelFiles()
        if name not in files:
            return fail('参数错误')
        truncate(files[name][1])
        mw.writeLog('日志管理', '清空' + files[name][0])
        return ok('已清空')

    # ------------------------------- 操作日志类型 --------------------------------

    def logTypes(self):
        rows = mw.M('logs').field('type').group('type').select() or []
        return ok('OK', sorted(set(r['type'] for r in rows if isinstance(r, dict) and r.get('type'))))

    def operationLogs(self, page=1, limit=20, search='', ltype=''):
        try:
            page = max(1, int(page))
            limit = max(1, min(100, int(limit)))
        except ValueError:
            page, limit = 1, 20
        where, params = [], []
        if search:
            where.append('(type like ? or log like ?)')
            params += ['%' + search + '%', '%' + search + '%']
        if ltype:
            where.append('type = ?')
            params.append(ltype)
        cond = ' and '.join(where)
        q = mw.M('logs').field('id,type,log,uid,add_time')
        c = mw.M('logs')
        if cond:
            q = q.where(cond, tuple(params))
            c = c.where(cond, tuple(params))
        rows = q.limit('%d,%d' % ((page - 1) * limit, limit)).order('id desc').select() or []
        return ok('OK', {'list': rows if isinstance(rows, list) else [], 'total': c.count(), 'page': page})

    def exportOperationLogs(self, search='', ltype=''):
        # 导出最多 10000 条
        where, params = [], []
        if search:
            where.append('(type like ? or log like ?)')
            params += ['%' + search + '%', '%' + search + '%']
        if ltype:
            where.append('type = ?')
            params.append(ltype)
        q = mw.M('logs').field('id,type,log,add_time')
        if where:
            q = q.where(' and '.join(where), tuple(params))
        rows = q.limit('0,10000').order('id desc').select() or []
        out = ['时间,类型,详情']
        for row in rows:
            cells = [row['add_time'], row['type'], row['log']]
            # CSV 转义, 并防止以 = + - @ 开头的内容被表格软件当作公式执行
            safe = []
            for c in cells:
                c = str(c).replace('"', '""')
                if c[:1] in ('=', '+', '-', '@'):
                    c = "'" + c
                safe.append('"' + c + '"')
            out.append(','.join(safe))
        return '﻿' + '\n'.join(out) + '\n'

    # ------------------------------- 网站日志 ------------------------------------

    def siteLogPaths(self, name):
        d = mw.getLogsDir()
        return {'access': d + '/' + name + '.log', 'error': d + '/' + name + '.error.log'}

    def siteList(self):
        rows = mw.M('sites').field('id,name,status').order('id desc').select() or []
        res = []
        for r in rows if isinstance(rows, list) else []:
            p = self.siteLogPaths(r['name'])
            res.append({
                'id': r['id'], 'name': r['name'],
                'access_size': os.path.getsize(p['access']) if os.path.exists(p['access']) else 0,
                'error_size': os.path.getsize(p['error']) if os.path.exists(p['error']) else 0,
            })
        return ok('OK', {'list': res, 'dir': mw.getLogsDir()})

    def __checkSite(self, name):
        if not SITE_RE.match(str(name or '')) or '..' in name:
            return False
        return mw.M('sites').where('name=?', (name,)).count() > 0

    def siteLog(self, name, ltype='access', lines=200, search=''):
        if not self.__checkSite(name) or ltype not in ('access', 'error'):
            return fail('网站不存在')
        path = self.siteLogPaths(name)[ltype]
        r = tail(path, lines, search)
        r['path'] = path
        return ok('OK', r)

    def clearSiteLog(self, name, ltype='access'):
        if not self.__checkSite(name) or ltype not in ('access', 'error'):
            return fail('网站不存在')
        truncate(self.siteLogPaths(name)[ltype])
        mw.writeLog('日志管理', '清空网站[%s]%s日志' % (name, '访问' if ltype == 'access' else '错误'))
        return ok('已清空')

    # ------------------------------- 计划任务日志 --------------------------------

    def cronFile(self, echo):
        return mw.getServerDir() + '/cron/' + echo + '.log'

    def cronList(self):
        rows = mw.M('crontab').field('id,name,type,where1,where_hour,where_minute,echo,status').order('id desc').select() or []
        res = []
        for r in rows if isinstance(rows, list) else []:
            f = self.cronFile(r['echo'])
            res.append({'id': r['id'], 'name': r['name'], 'status': r.get('status'),
                        'size': os.path.getsize(f) if os.path.exists(f) else 0,
                        'mtime': int(os.path.getmtime(f)) if os.path.exists(f) else 0})
        return ok('OK', res)

    def __cronEcho(self, cron_id):
        try:
            cron_id = int(cron_id)
        except (TypeError, ValueError):
            return None
        row = mw.M('crontab').field('echo').where('id=?', (cron_id,)).find()
        if not row or not isinstance(row, dict) or not re.match(r'^[A-Za-z0-9_\-]+$', str(row.get('echo', ''))):
            return None
        return row['echo']

    def cronLog(self, cron_id, lines=200, search=''):
        echo = self.__cronEcho(cron_id)
        if not echo:
            return fail('计划任务不存在')
        return ok('OK', tail(self.cronFile(echo), lines, search))

    def clearCronLog(self, cron_id):
        echo = self.__cronEcho(cron_id)
        if not echo:
            return fail('计划任务不存在')
        truncate(self.cronFile(echo))
        mw.writeLog('日志管理', '清空计划任务日志[%s]' % cron_id)
        return ok('已清空')

    # ------------------------------- 软件日志 ------------------------------------

    def softFiles(self):
        s = mw.getServerDir()
        items = []

        def add(key, title, path):
            if path and os.path.isfile(path):
                items.append({'key': key, 'title': title, 'path': path, 'size': os.path.getsize(path)})

        add('openresty_error', 'OpenResty 错误日志', s + '/openresty/nginx/logs/error.log')
        add('openresty_access', 'OpenResty 访问日志', s + '/openresty/nginx/logs/access.log')
        for name, title in (('mysql', 'MySQL'), ('mariadb', 'MariaDB'), ('mysql-community', 'MySQL')):
            conf = mw.readFile(s + '/' + name + '/etc/my.cnf') or ''
            m = re.search(r'^\s*log-error\s*=\s*(\S+)', conf, re.M)
            if m:
                add(name + '_error', title + ' 错误日志', m.group(1))
            m = re.search(r'^\s*slow[_-]query[_-]log[_-]file\s*=\s*(\S+)', conf, re.M)
            if m:
                add(name + '_slow', title + ' 慢查询日志', m.group(1))
        for f in sorted(glob.glob(s + '/php/*/var/log/php-fpm.log')):
            ver = f.split('/php/')[1].split('/')[0]
            add('php%s_fpm' % ver, 'PHP %s FPM 日志' % ver, f)
        for f in sorted(glob.glob(s + '/php/*/var/log/slow.log')):
            ver = f.split('/php/')[1].split('/')[0]
            add('php%s_slow' % ver, 'PHP %s 慢日志' % ver, f)
        for name in ('redis', 'valkey'):
            add(name, name.capitalize() + ' 日志', s + '/' + name + '/data/' + name + '.log')
            add(name + '_log', name.capitalize() + ' 日志', s + '/' + name + '/' + name + '.log')
        add('pureftp', 'Pure-FTPd 日志', '/var/log/pureftpd.log')
        add('pgsql', 'PostgreSQL 日志', s + '/postgresql/logs/server.log')
        add('mongodb', 'MongoDB 日志', s + '/mongodb/log/mongodb.log')
        add('modsecurity', 'ModSecurity 审计日志', s + '/modsecurity/logs/audit.log')
        return items

    def softList(self):
        return ok('OK', [{'key': i['key'], 'title': i['title'], 'path': i['path'], 'size': i['size']} for i in self.softFiles()])

    def softLog(self, key, lines=200, search=''):
        for i in self.softFiles():
            if i['key'] == key:
                r = tail(i['path'], lines, search)
                r['path'] = i['path']
                return ok('OK', r)
        return fail('日志不存在')

    # ------------------------------- 系统日志 ------------------------------------

    def systemFiles(self):
        import utils.adult_log as adult_log
        return adult_log.getAuditLogsFiles()

    def systemLog(self, name, lines=200, search=''):
        files = {f['name']: f for f in self.systemFiles()}
        if name not in files:
            return fail('日志文件不存在')
        base = name.split('/')[-1]
        # 二进制登录记录(wtmp/btmp/lastlog)交给原有的解析函数
        if re.match(r'^(wtmp|btmp|utmp|lastlog)', base):
            import utils.adult_log as adult_log
            data = adult_log.getAuditLogsName(name)
            return ok('OK', {'table': data.get('data') if isinstance(data, dict) else data})
        r = tail(files[name]['log_file'], lines, search)
        r['path'] = files[name]['log_file']
        return ok('OK', r)

    # ------------------------------- 占用与清理 ----------------------------------

    def overview(self):
        site_dir = mw.getLogsDir()
        panel_dir = mw.getPanelDir() + '/logs'
        cron_dir = mw.getServerDir() + '/cron'
        return ok('OK', {
            'site': {'path': site_dir, 'size': dirSize(site_dir)},
            'panel': {'path': panel_dir, 'size': dirSize(panel_dir)},
            'cron': {'path': cron_dir, 'size': sum(os.path.getsize(f) for f in glob.glob(cron_dir + '/*.log'))},
            'operation': mw.M('logs').count(),
        })

    def cleanSiteLogs(self):
        '''清空所有网站日志(保留文件, 不影响 Nginx 写入)'''
        n = 0
        for f in glob.glob(mw.getLogsDir() + '/*.log'):
            if truncate(f):
                n += 1
        mw.writeLog('日志管理', '清空全部网站日志(%d 个文件)' % n)
        return ok('已清空 %d 个网站日志文件' % n)

    def cleanCronLogs(self):
        n = 0
        for f in glob.glob(mw.getServerDir() + '/cron/*.log'):
            if truncate(f):
                n += 1
        mw.writeLog('日志管理', '清空全部计划任务日志(%d 个文件)' % n)
        return ok('已清空 %d 个计划任务日志' % n)
