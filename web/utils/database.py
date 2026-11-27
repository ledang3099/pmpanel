# coding:utf-8

# ---------------------------------------------------------------------------------
# PM-Linux面板
# ---------------------------------------------------------------------------------
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------

# 数据库栏目: 统一调用各数据库插件(MySQL/MariaDB/PostgreSQL/MongoDB), Redis 直接管理
#
# 插件原有的参数协议会把整段参数按 shell 规则拆分, 值中含空格/逗号/冒号时会解析错误,
# 且插件内部多处把参数直接拼进 SQL/shell。这里统一做两件事:
#   1. 只允许白名单中的插件和函数, 每个参数都按名称做严格校验
#   2. 以 key:value 参数列表传给插件(不经过 shell, 也不再二次拆分)

import os
import re
import json

import core.mw as mw

# 引擎 -> 可用插件(按优先顺序)
ENGINES = {
    'mysql': ['mysql', 'mariadb', 'mysql-community'],
    'pgsql': ['postgresql'],
    'mongodb': ['mongodb'],
    'redis': ['redis', 'valkey'],
}

TITLES = {
    'mysql': 'MySQL', 'mariadb': 'MariaDB', 'mysql-community': 'MySQL(官方二进制)',
    'postgresql': 'PostgreSQL', 'mongodb': 'MongoDB', 'redis': 'Redis', 'valkey': 'Valkey',
}

# 各类插件允许调用的函数
MYSQL_FUNCS = {
    'get_db_list', 'add_db', 'del_db', 'set_user_pwd', 'get_db_access', 'set_db_access', 'set_db_ps',
    'get_db_backup_list', 'set_db_backup', 'import_db_backup', 'delete_db_backup',
    'get_db_backup_import_list', 'import_db_external', 'sync_get_databases', 'sync_to_databases',
    'set_root_pwd', 'get_db_info', 'repair_table', 'opt_table', 'alter_table', 'run_info',
    'get_total_statistics', 'import_db_backup_progress_bar', 'import_db_external_progress_bar',
}
FUNCS = {
    'mysql': MYSQL_FUNCS,
    'mariadb': MYSQL_FUNCS,
    'mysql-community': MYSQL_FUNCS,
    'postgresql': {
        'get_db_list', 'add_db', 'del_db', 'set_user_pwd', 'get_db_access', 'set_db_access',
        'get_db_backup_list', 'pg_back', 'delete_db_backup', 'import_db_backup',
        'get_db_backup_import_list', 'import_db_external', 'sync_get_databases',
        'set_postgres_pwd', 'get_db_info', 'run_info',
    },
    'mongodb': {
        'get_db_list', 'add_db', 'del_db', 'set_user_pwd', 'set_db_ps', 'get_db_access', 'set_db_access',
        'get_db_backup_list', 'set_db_backup', 'delete_db_backup', 'import_db_backup',
        'get_db_backup_import_list', 'import_db_external', 'sync_get_databases', 'sync_to_databases',
        'set_root_pwd', 'get_db_info', 'run_info',
    },
}

RE_NAME = re.compile(r'^[A-Za-z0-9_\-]{1,64}$')
RE_USER = re.compile(r'^[A-Za-z0-9_.\-]{1,32}$')
# 密码不允许引号、反斜杠、反引号、空白(插件会把密码拼进 SQL)
RE_PASS = re.compile(r'^[A-Za-z0-9!@#$%^&*()_+\-=\[\]{}|;:,.<>?~]{6,64}$')
RE_FILE = re.compile(r'^[A-Za-z0-9_.\-]{1,255}$')
RE_ACCESS = re.compile(r'^[A-Za-z0-9.:%_\-/,]{1,500}$')
RE_TABLE = re.compile(r'^[A-Za-z0-9_\-$]{1,64}$')


def _json_list(validator):
    def check(v):
        try:
            items = json.loads(v)
        except ValueError:
            return False
        return isinstance(items, list) and len(items) <= 1000 and all(validator(str(i)) for i in items)
    return check


VALIDATORS = {
    'page': lambda v: re.fullmatch(r'\d{1,6}', v) is not None,
    'page_size': lambda v: re.fullmatch(r'\d{1,3}', v) is not None and 0 < int(v) <= 100,
    'search': lambda v: len(v) <= 64 and not re.search(r'[\'"\\`%\x00-\x1f]', v),
    'id': lambda v: re.fullmatch(r'\d{1,10}', v) is not None,
    'name': lambda v: RE_NAME.match(v) is not None,
    'db_name': lambda v: RE_NAME.match(v) is not None,
    'db_user': lambda v: RE_USER.match(v) is not None,
    'username': lambda v: RE_USER.match(v) is not None,
    'password': lambda v: RE_PASS.match(v) is not None,
    'codeing': lambda v: v in ('utf8mb4', 'utf8', 'gbk', 'big5', 'latin1', 'UTF8', 'SQL_ASCII'),
    'dataAccess': lambda v: RE_ACCESS.match(v) is not None,
    'address': lambda v: v == '' or RE_ACCESS.match(v) is not None,
    'access': lambda v: RE_ACCESS.match(v) is not None,
    'ps': lambda v: len(v) <= 200 and not re.search(r'[\x00-\x1f\'"\\`]', v),
    'file': lambda v: RE_FILE.match(v) is not None and '..' not in v,
    'filename': lambda v: RE_FILE.match(v) is not None and '..' not in v,
    'path': lambda v: v == '' or _under_backup(v),
    'tables': _json_list(lambda t: RE_TABLE.match(t) is not None),
    'table_type': lambda v: v in ('InnoDB', 'MyISAM'),
    'type': lambda v: v in ('0', '1'),
    'ids': _json_list(lambda t: re.fullmatch(r'\d{1,10}', t) is not None),
    'force': lambda v: v in ('0', '1', '2'),
    'rw': lambda v: v in ('rw', 'r', 'all'),
}


def _under_backup(path):
    root = os.path.realpath(mw.getBackupDir())
    real = os.path.realpath(path)
    return real == root or real.startswith(root + '/')


def ok(msg='OK', data=None):
    return mw.returnData(True, msg, data)


def fail(msg, data=None):
    return mw.returnData(False, msg, data)


class Database(object):

    __instance = None

    @classmethod
    def instance(cls):
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    # ------------------------------- 插件信息 -----------------------------------

    def pluginInstalled(self, name):
        return os.path.exists(mw.getServerDir() + '/' + name + '/version.pl')

    def pluginVersion(self, name):
        return (mw.readFile(mw.getServerDir() + '/' + name + '/version.pl') or '').strip()

    def runPlugin(self, name, func, args=None):
        from utils.plugin import plugin as MwPlugin
        argv = ['%s:%s' % (k, v) for k, v in (args or {}).items()]
        # 插件 getArgs 只有在参数个数大于 1 时才逐个按 key:value 解析, 补一个占位参数
        argv.append('_pm:1')
        out, err = MwPlugin.instance().run(name, func, argv_list=argv)
        return out, err

    def pluginStatus(self, name):
        out, err = self.runPlugin(name, 'status')
        return out.strip() == 'start'

    def getInfo(self):
        res = {}
        for engine, plugins in ENGINES.items():
            items = []
            for p in plugins:
                if not os.path.isdir(mw.getPluginDir() + '/' + p):
                    continue
                installed = self.pluginInstalled(p)
                items.append({
                    'name': p,
                    'title': TITLES.get(p, p),
                    'installed': installed,
                    'version': self.pluginVersion(p) if installed else '',
                    'status': self.pluginStatus(p) if installed else False,
                })
            res[engine] = items
        res['phpmyadmin'] = self.pluginInstalled('phpmyadmin')
        res['backup_dir'] = mw.getBackupDir()
        return ok('OK', res)

    # ------------------------------- 统一调用 -----------------------------------

    def call(self, name, func, args):
        if name not in FUNCS:
            return fail('不支持的数据库插件')
        if func not in FUNCS[name]:
            return fail('不支持的操作')
        if not self.pluginInstalled(name):
            return fail('%s 未安装, 请先在应用市场中安装' % TITLES.get(name, name))
        if not isinstance(args, dict):
            return fail('参数格式不正确')
        clean = {}
        for k, v in args.items():
            k = str(k)
            v = '' if v is None else str(v).strip()
            if k not in VALIDATORS:
                return fail('不支持的参数: %s' % k[:30])
            if not VALIDATORS[k](v):
                return fail(self.paramError(k))
            clean[k] = v
        if func in ('add_db',) and clean.get('db_user', '').lower() in ('root', 'mysql', 'postgres', 'admin'):
            return fail('数据库用户名不能使用系统保留名称')
        out, err = self.runPlugin(name, func, clean)
        if err and not out.strip():
            return fail('执行失败: ' + err.strip()[-300:])
        out = out.strip()
        try:
            data = json.loads(out)
        except ValueError:
            return ok('OK', out)
        # 列表接口不返回 root 密码明文, 需要时单独获取
        if func == 'get_db_list' and isinstance(data, dict):
            if isinstance(data.get('info'), dict):
                data['info'].pop('root_pwd', None)
            m = re.search(r'(\d+)\s*条', str(data.get('page', '')))
            data['count'] = int(m.group(1)) if m else len(data.get('data') or [])
        return ok('OK', data)

    def paramError(self, key):
        return {
            'name': '数据库名只能包含字母、数字、下划线和连字符(最长 64 位)',
            'db_name': '数据库名只能包含字母、数字、下划线和连字符(最长 64 位)',
            'db_user': '用户名只能包含字母、数字、下划线、点和连字符(最长 32 位)',
            'username': '用户名只能包含字母、数字、下划线、点和连字符(最长 32 位)',
            'password': '密码长度 6-64 位, 不能包含引号、反斜杠、反引号和空格',
            'dataAccess': '访问权限格式不正确',
            'access': '访问权限格式不正确, 多个 IP 用逗号分隔',
            'ps': '备注最长 200 字, 不能包含引号和换行',
            'search': '搜索内容不能包含引号和特殊字符',
            'file': '文件名只能包含字母、数字、下划线、点和连字符',
            'filename': '文件名只能包含字母、数字、下划线、点和连字符',
            'path': '只能操作备份目录中的文件',
        }.get(key, '参数 %s 不正确' % key)

    def rootPassword(self, name):
        '''需要时才返回 root 密码(aaPanel 的"root 密码"按钮)'''
        if name not in FUNCS:
            return fail('不支持')
        if not self.pluginInstalled(name):
            return fail('未安装')
        out, err = self.runPlugin(name, 'get_db_list', {'page': '1', 'page_size': '1'})
        try:
            data = json.loads(out)
            return ok('OK', {'password': data['info']['root_pwd']})
        except (ValueError, KeyError, TypeError):
            return fail('获取失败')

    def importDir(self):
        path = mw.getBackupDir() + '/import'
        if not os.path.isdir(path):
            os.makedirs(path, mode=0o755, exist_ok=True)
        return path
