# coding:utf-8

import sys
import io
import json
import os
import subprocess
import time
import re

web_dir = os.getcwd() + "/web"
if os.path.exists(web_dir):
    sys.path.append(web_dir)
    os.chdir(web_dir)

import core.mw as mw

app_debug = False
if mw.isAppleSystem():
    app_debug = True


def getPluginName():
    return 'zabbix'


def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()


def getInitDFile():
    current_os = mw.getOs()
    if current_os == 'darwin':
        return '/tmp/' + getPluginName()

    if current_os.startswith('freebsd'):
        return '/etc/rc.d/' + getPluginName()

    return '/etc/init.d/' + getPluginName()


def getConf():
    path = getServerDir() + "/web_conf/nginx/vhost/zabbix.conf"
    return path


def getInitDTpl():
    path = getPluginDir() + "/init.d/" + getPluginName() + ".tpl"
    return path


def getArgs():
    args = sys.argv[3:]
    tmp = {}
    args_len = len(args)

    if args_len == 1:
        t = args[0].strip('{').strip('}')
        if t.strip() == '':
            tmp = []
        else:
            t = t.split(':')
            tmp[t[0]] = t[1]
        tmp[t[0]] = t[1]
    elif args_len > 1:
        for i in range(len(args)):
            t = args[i].split(':')
            tmp[t[0]] = t[1]
    return tmp

def checkArgs(data, ck=[]):
    for i in range(len(ck)):
        if not ck[i] in data:
            return (False, mw.returnJson(False, '参数:(' + ck[i] + ')没有!'))
    return (True, mw.returnJson(True, 'ok'))

def getPidFile():
    file = getConf()
    content = mw.readFile(file)
    rep = r'pidfile\s*(.*)'
    tmp = re.search(rep, content)
    return tmp.groups()[0].strip()

def status():
    cmd = "ps -ef|grep zabbix_server |grep -v grep | grep -v python | grep -v pmpanel | awk '{print $2}'"
    data = mw.execShell(cmd)
    if data[0] == '':
        return 'stop'
    return 'start'

def getInstallVerion():
    version_pl = getServerDir() + "/version.pl"
    version = mw.readFile(version_pl).strip()
    return version

def contentReplace(content):
    service_path = mw.getServerDir()
    content = content.replace('{$ROOT_PATH}', mw.getFatherDir())
    content = content.replace('{$SERVER_PATH}', service_path)
    frontend = '/usr/share/zabbix/ui' if getInstallVerion() == '8.0' else '/usr/share/zabbix'
    content = content.replace('{$ZABBIX_ROOT}', frontend)
    content = content.replace('{$ZABBIX_PORT}', '18888')

    psdb = pSqliteDb('databases')
    db_pass = psdb.where('name = ?', ('zabbix',)).getField('password')
    content = content.replace('{$ZABBIX_DB_PORT}', getMySQLPort())
    content = content.replace('{$ZABBIX_DB_PASS}', db_pass)
    return content


MYSQL_CLIENT_PATHS = {
    'mysql-apt': 'bin/usr/bin/mysql', 'mysql-yum': 'bin/usr/bin/mysql',
    'mysql': 'bin/mysql', 'mysql-community': 'bin/mysql',
}


def findMySQL(version):
    for plugin in MYSQL_CLIENT_PATHS:
        root = os.path.join(mw.getServerDir(), plugin)
        if not os.path.isfile(os.path.join(root, 'etc', 'my.cnf')):
            continue
        if version == '8.0':
            series = mw.readFile(os.path.join(root, 'version.pl'))
            if not series or not re.match(r'^(8\.4|9\.[0-7])(?:\.|$)', series.strip()):
                continue
        return plugin
    return ''


def getMySQLConf():
    choose_mysql = getServerDir() + '/mysql.pl'
    selected = mw.readFile(choose_mysql)
    plugin = selected.strip() if selected else findMySQL(getInstallVerion())
    if plugin not in MYSQL_CLIENT_PATHS:
        raise RuntimeError('需要安装受支持的 MySQL 版本')
    if not selected:
        mw.writeFile(choose_mysql, plugin)
    return os.path.join(mw.getServerDir(), plugin, 'etc', 'my.cnf')


def getMySQLPort():
    file = getMySQLConf()
    content = mw.readFile(file)
    rep = r'port\s*=\s*(.*)'
    tmp = re.search(rep, content)
    return tmp.groups()[0].strip()

def getMySQLSocketFile():
    file = getMySQLConf()
    content = mw.readFile(file)
    rep = r'socket\s*=\s*(.*)'
    tmp = re.search(rep, content)
    return tmp.groups()[0].strip()

def getMySQLBin():
    plugin = mw.readFile(getServerDir() + '/mysql.pl').strip()
    return os.path.join(mw.getServerDir(), plugin, MYSQL_CLIENT_PATHS[plugin])

def pSqliteDb(dbname='databases'):
    choose_mysql = getServerDir()+'/mysql.pl'
    ver = mw.readFile(choose_mysql).strip()

    mysql_dir = mw.getServerDir() + '/'+ver
    conn = mw.M(dbname).dbPos(mysql_dir, 'mysql')
    return conn


def pMysqlDb():
    # pymysql
    db = mw.getMyORM()
    db.setDbName('zabbix')
    db.setPort(getMySQLPort())
    db.setSocket(getMySQLSocketFile())
    db.setPwd(pSqliteDb('config').where('id=?', (1,)).getField('mysql_root'))
    return db


def getInstalledPhpConfDir(version=None):
    if version is None:
        version = getInstallVerion()
    phpver = ["85", "84", "83", "82"] if version == "8.0" else ["80", "81", "82", "83", "84", "85"]
    server = mw.getServerDir()
    root = os.path.join(server, 'web_conf', 'php', 'conf')
    for ver in phpver:
        dotted = ver[0] + '.' + ver[1]
        candidates = (
            ('php-apt' + dotted, f'/etc/php/{dotted}/fpm/php-fpm.conf'),
            ('php-yum' + ver, f'/etc/opt/remi/php{ver}/php-fpm.conf'),
            ('php-' + ver, os.path.join(server, 'php', ver, 'sbin', 'php-fpm')),
        )
        for name, fpm in candidates:
            if os.path.isfile(fpm) and os.path.isfile(os.path.join(root, 'enable-' + name + '.conf')):
                return name
    return ''


def zabbixNginxConf():
    return mw.getServerDir()+'/web_conf/nginx/vhost/zabbix.conf'

def zabbixPhpConf():
    # ver = getInstallVerion()
    # if ver == '6.0':
    #     return '/usr/share/zabbix/conf/zabbix.conf.php'
    return '/etc/zabbix/web/zabbix.conf.php'

def zabbixServerConf():
    ver = getInstallVerion()
    if ver == '6.0':
        return '/etc/zabbix_server.conf'
    return '/etc/zabbix/zabbix_server.conf'

def zabbixAgentConf():
    return '/etc/zabbix/zabbix_agentd.conf'

def zabbixImportMySQLDataFile():
    tgz_file = getPluginDir()+"/data/server6.0.sql.gz"
    ver = getInstallVerion()
    if ver == '6.0':
        return tgz_file
    if ver == '8.0':
        return '/usr/share/zabbix/sql-scripts/mysql/server.sql.gz'
    return '/usr/share/zabbix-sql-scripts/mysql/server.sql.gz'

def zabbixImportMySQLData():
    mysql_conf = getMySQLConf()
    if not os.path.exists(mysql_conf):
        exit("需要安装MySQL")

    choose_mysql = getServerDir()+'/mysql.pl'
    ver = mw.readFile(choose_mysql).strip()

    pmdb = pMysqlDb()
    psdb = pSqliteDb('databases')
    find_ps_zabbix = psdb.field('id').where('name = ?', ('zabbix',)).select()
    if len(find_ps_zabbix) < 1:
        db_pass = mw.getRandomString(16)
        # 创建数据
        args = {'name': 'zabbix', 'codeing': 'utf8mb4', 'db_user': 'zabbix',
                'password': db_pass, 'dataAccess': '127.0.0.1', 'ps': 'zabbix',
                'address': '127.0.0.1'}
        result = subprocess.run(
            [sys.executable, 'plugins/' + ver + '/index.py', 'add_db',
             *[f'{name}:{value}' for name, value in args.items()]],
            cwd=mw.getPanelDir(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        try:
            created = not result.returncode and json.loads(result.stdout)['status']
        except (ValueError, KeyError):
            created = False
        if not created:
            raise RuntimeError('Zabbix database creation failed')
        pmdb.query("ALTER DATABASE `zabbix` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_bin")
        pmdb.query("grant all privileges on zabbix.* to zabbix@127.0.0.1")


    db_pass = psdb.where('name = ?', ('zabbix',)).getField('password')
    find_zabbix_version = pmdb.query("show tables like 'dbversion'")
    if len(find_zabbix_version) == 0:
        # 初始化导入数据
        tgz_file = zabbixImportMySQLDataFile()
        import gzip
        import shutil

        command = [getMySQLBin(), '--no-defaults', '--protocol=TCP', '-h', '127.0.0.1',
                   '-P', getMySQLPort(), '--default-character-set=utf8mb4', '-uzabbix', 'zabbix']
        trust = pmdb.query("show global variables like 'log_bin_trust_function_creators'")
        restore_trust = bool(trust and trust[0]['Value'] == 'OFF')
        if restore_trust:
            pmdb.execute('set global log_bin_trust_function_creators=1')
        try:
            with gzip.open(tgz_file, 'rb') as schema, subprocess.Popen(
                command, stdin=subprocess.PIPE, env=dict(os.environ, MYSQL_PWD=db_pass),
            ) as database:
                with database.stdin:
                    shutil.copyfileobj(schema, database.stdin)
                if database.wait():
                    raise RuntimeError('Zabbix database schema import failed')
        finally:
            if restore_trust:
                pmdb.execute('set global log_bin_trust_function_creators=0')


    ver = getInstallVerion()
    if ver == '6.0':
        pmdb.query("update dbversion set mandatory=6000000")

    return True

def initOpConf():
    nginx_src_tpl = getPluginDir()+'/conf/zabbix.nginx.conf'
    nginx_dst_vhost = zabbixNginxConf()

    logs = mw.getLogsDir()
    os.makedirs(logs, exist_ok=True)
    if not os.path.exists(nginx_dst_vhost):
        phpver = getInstalledPhpConfDir()
        if not phpver:
            raise RuntimeError('需要安装受支持的 PHP-FPM 版本')
        content = mw.readFile(nginx_src_tpl)
        content = contentReplace(content)
        content = content.replace('{$PHP_VER}', phpver).replace('{$ZABBIX_LOG_DIR}', logs)
        mw.writeFile(nginx_dst_vhost, content)

def initZsConf():
    ver = getInstallVerion()
    zs_src_tpl = getPluginDir()+'/conf/zabbix_server.conf'
    if ver == '6.0':
        zs_src_tpl = getPluginDir()+'/conf/zabbix_server6.conf'

    zs_dst_path = zabbixServerConf()

    # zabbix_server配置
    content = mw.readFile(zs_src_tpl)
    content = contentReplace(content)
    mw.writeFile(zs_dst_path, content)

def initPhpConf():
    php_src_tpl = getPluginDir()+'/conf/zabbix.conf.php'
    php_dst_path = zabbixPhpConf()
    # php配置
    # if not os.path.exists(php_dst_path):
    content = mw.readFile(php_src_tpl)
    content = contentReplace(content)
    mw.writeFile(php_dst_path, content)

def initAgentConf():
    za_src_tpl = getPluginDir()+'/conf/zabbix_agentd.conf'
    za_dst_path = zabbixAgentConf()

    # zabbix_agent配置
    content = mw.readFile(za_src_tpl)
    content = contentReplace(content)
    mw.writeFile(za_dst_path, content)

def openPort():
    try:
        from utils.firewall import Firewall as MwFirewall
        MwFirewall.instance().addAcceptPort('18888', 'zabbix-web', 'port')
        MwFirewall.instance().addAcceptPort('10051', 'zabbix-server', 'port')
        MwFirewall.instance().addAcceptPort('10050', 'zabbix-agent', 'port')
        return port
    except Exception as e:
        return "Release failed {}".format(e)
    return True


def initDreplace():
    # 导入MySQL配置
    zabbixImportMySQLData()

    # 初始化OP配置
    initOpConf()
    

    init_file = getServerDir() + '/init.pl'
    if not os.path.exists(init_file):
        initZsConf()
        initAgentConf()
        initPhpConf()
        openPort()
        mw.writeFile(init_file, 'ok')
    return True


def zOp(method):

    initDreplace()

    data = mw.execShell('systemctl ' + method + ' zabbix-server')
    mw.execShell('systemctl ' + method + ' zabbix-agent')
    if data[1] == '':
        return 'ok'
    return data[1]


def start():
    val = zOp('start')
    mw.restartWeb()
    return val


def stop():
    val = zOp('stop')

    # 删除nginx配置
    nginx_dst_vhost = zabbixNginxConf()
    if os.path.exists(nginx_dst_vhost):
        os.remove(nginx_dst_vhost)

    mw.restartWeb()

    return val

def restart():
    status = zOp('restart')
    return status

def reload():
    initZsConf()
    initAgentConf()
    initPhpConf()
    return zOp('reload')

def initdStatus():
    current_os = mw.getOs()
    if current_os == 'darwin':
        return "Apple Computer does not support"

    shell_cmd = 'systemctl status zabbix-server | grep loaded | grep "enabled;"'
    data = mw.execShell(shell_cmd)
    if data[0] == '':
        return 'fail'
    return 'ok'


def initdInstall():
    current_os = mw.getOs()
    if current_os == 'darwin':
        return "Apple Computer does not support"

    data = mw.execShell('systemctl enable zabbix-server')
    if data[1] != '':
        return data[1]
    return 'ok'


def initdUinstall():
    current_os = mw.getOs()
    if current_os == 'darwin':
        return "Apple Computer does not support"

    data = mw.execShell('systemctl disable zabbix-server')
    if data[1] != '':
        return data[1]
    return 'ok'

def runLog():
    zs_conf = zabbixServerConf()
    content = mw.readFile(zs_conf)

    rep = r'LogFile=\s*(.*)'
    tmp = re.search(rep, content)

    if tmp.groups():
        return tmp.groups()[0].strip()
    return '/var/log/zabbix/zabbix_server.log'

def zabbixAgentLog():
    za_conf = zabbixAgentConf()
    content = mw.readFile(za_conf)

    rep = r'LogFile=\s*(.*)'
    tmp = re.search(rep, content)

    if tmp.groups():
        return tmp.groups()[0].strip()
    return '/var/log/zabbix/zabbix_agentd.log'


def installPreInspection(version=''):
    if version == '8.0':
        try:
            with open('/etc/os-release', encoding='utf-8') as release_file:
                release = dict(line.strip().replace('"', '').split('=', 1)
                               for line in release_file if '=' in line and not line.startswith('#'))
        except OSError:
            release = {}
        supported = {'debian': ('12', '13'), 'ubuntu': ('22.04', '24.04')}
        if release.get('VERSION_ID') not in supported.get(release.get('ID'), ()):
            return 'Zabbix 8.0 当前支持 Debian 12/13 和 Ubuntu 22.04/24.04'

    cmd = "cat /etc/*-release | grep PRETTY_NAME |awk -F = '{print $2}' | awk -F '\"' '{print $2}'| awk '{print $1}'"
    sys = mw.execShell(cmd)


    cmd = "cat /etc/*-release | grep VERSION_ID | awk -F = '{print $2}' | awk -F '\"' '{print $2}'"
    sys_id = mw.execShell(cmd)

    sysName = sys[0].strip().lower()
    sysId = sys_id[0].strip().lower()

    # opensuse
    if not sysName in ['debian','centos','ubuntu','almalinux','rocky']:
        return '不支持该系统'

    if version != '8.0' and sysName == 'debian' and sysId != '12':
        return '不支持,'+sysName+'['+sysId+'],仅支持debian12!'

    openresty_dir = mw.getServerDir() + "/openresty"
    if not os.path.exists(openresty_dir):
        return '需要安装Openresty插件'

    if not getInstalledPhpConfDir(version):
        return 'Zabbix 8.0 需要 PHP 8.2–8.5' if version == '8.0' else '需要安装 PHP-FPM 8.0–8.5'


    if not findMySQL(version):
        return 'Zabbix 8.0 需要 MySQL 8.4–9.7' if version == '8.0' else '需要安装 MySQL 插件'

    return 'ok'


def uninstallPreInspection():
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
    elif func == 'initd_status':
        print(initdStatus())
    elif func == 'initd_install':
        print(initdInstall())
    elif func == 'initd_uninstall':
        print(initdUinstall())
    elif func == 'install_pre_inspection':
        print(installPreInspection(sys.argv[2] if len(sys.argv) > 2 else ''))
    elif func == 'uninstall_pre_inspection':
        print(uninstallPreInspection())
    elif func == 'conf':
        print(zabbixNginxConf())
    elif func == 'php_conf':
        print(zabbixPhpConf())
    elif func == 'zabbix_server_conf':
        print(zabbixServerConf())
    elif func == 'zabbix_agent_conf':
        print(zabbixAgentConf())
    elif func == 'run_log':
        print(runLog())
    elif func == 'zabbix_agent_log':
        print(zabbixAgentLog())
    else:
        print('error')
