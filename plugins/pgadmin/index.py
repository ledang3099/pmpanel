# coding:utf-8

import sys
import io
import os
import time
import re
import json
import secrets
import sqlite3
import subprocess
from pathlib import Path

web_dir = os.getcwd() + "/web"
if os.path.exists(web_dir):
    sys.path.append(web_dir)
    os.chdir(web_dir)

import core.mw as mw

app_debug = False
if mw.isAppleSystem():
    app_debug = True


def getPluginName():
    return 'pgadmin'


def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()


def getArgs():
    args = sys.argv[2:]
    tmp = {}
    args_len = len(args)

    if args_len == 1:
        t = args[0].strip('{').strip('}')
        t = t.split(':')
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


def getConf():
    return mw.getServerDir() + '/web_conf/nginx/vhost/pgadmin.conf'


def getPort():
    file = getConf()
    content = mw.readFile(file)
    rep = r'listen\s*(.*);'
    tmp = re.search(rep, content)
    return tmp.groups()[0].strip()



def getHomePage():
    try:
        port = getPort()
        ip = '127.0.0.1'
        if not mw.isAppleSystem():
            ip = mw.getLocalIp()

        cfg = getCfg()
        auth = cfg['username']+':'+cfg['password']
        url = 'http://' + auth + '@' + ip + ':' + port + '/'
        return mw.returnJson(True, 'OK', url)
    except Exception as e:
        return mw.returnJson(False, '插件未启动!')



def contentReplace(content):
    cfg = getCfg()
    service_path = mw.getServerDir()

    content = content.replace('{$ROOT_PATH}', mw.getFatherDir())
    content = content.replace('{$SERVER_PATH}', service_path)
    content = content.replace('{$APP_PATH}', service_path+'/'+getPluginName()+'/data')

    port = cfg["port"]
    rep = r'listen\s*(.*);'
    content = re.sub(rep, "listen " + port + ';', content)
    return content


def initCfg():
    cfg = getServerDir() + "/cfg.json"
    if not os.path.exists(cfg):
        data = {}
        data['port'] = '5051'
        data['path'] = ''
        data['username'] = 'admin'
        data['password'] = 'admin'

        data['web_pg_username'] = 'pmpanel@gmail.com'
        data['web_pg_password'] = 'admin'
        mw.writeFile(cfg, json.dumps(data))


def setCfg(key, val):
    cfg = getServerDir() + "/cfg.json"
    data = mw.readFile(cfg)
    data = json.loads(data)
    data[key] = val
    mw.writeFile(cfg, json.dumps(data))


def getCfg():
    cfg = getServerDir() + "/cfg.json"
    data = mw.readFile(cfg)
    data = json.loads(data)
    return data


def returnCfg():
    cfg = getServerDir() + "/cfg.json"
    data = mw.readFile(cfg)
    return data


def __release_port(port):
    from collections import namedtuple
    try:
        from utils.firewall import Firewall as MwFirewall
        MwFirewall.instance().addAcceptPort(port, 'pgAdmin默认端口', 'port')
        return port
    except Exception as e:
        return "Release failed {}".format(e)


def __delete_port(port):
    from collections import namedtuple
    try:
        from utils.firewall import Firewall as MwFirewall
        MwFirewall.instance().delAcceptPort(port, 'tcp')
        return port
    except Exception as e:
        return "Release failed {}".format(e)


def openPort():
    conf = getCfg()
    port = conf['port']
    for i in [port]:
        __release_port(i)
    return True


def delPort():
    conf = getCfg()
    port = conf['port']
    for i in [port]:
        __delete_port(i)
    return True


def cleanNginxLog():
    log_a = accessLog()
    log_e = errorLog()

    for i in [log_a, log_e]:
        if os.path.exists(i):
            cmd = "echo '' > " + i
            mw.execShell(cmd)

def pgAdminPath():
    python = getServerDir() + '/run/bin/python'
    purelib = subprocess.check_output(
        [python, '-c', "from sysconfig import get_path; print(get_path('purelib'))"],
        text=True,
    ).strip()
    return Path(purelib) / 'pgadmin4'


def initPgConfFile(package):
    template = getPluginDir() + '/conf/config_local.py'
    destination = package / 'config_local.py'
    if not destination.exists():
        content = mw.readFile(template).replace('{$DATA_PATH}', getServerDir() + '/data')
        destination.write_text(content)


def initPgDatabase(package):
    database = Path(getServerDir()) / 'data/pgadmin4/pgadmin4.db'
    if database.is_file():
        with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as connection:
            has_users = connection.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'user'").fetchone()
            if has_users and connection.execute('SELECT 1 FROM "user" LIMIT 1').fetchone():
                return

    cfg = getCfg()
    email = cfg.get('web_pg_username') or 'pmpanel.' + secrets.token_hex(6) + '@example.com'
    password = cfg.get('web_pg_password') or secrets.token_urlsafe(18)
    env = dict(os.environ, PGADMIN_SETUP_EMAIL=email, PGADMIN_SETUP_PASSWORD=password)
    subprocess.run(
        [getServerDir() + '/run/bin/python', str(package / 'setup.py'), 'setup-db'],
        env=env, cwd=package, stdin=subprocess.DEVNULL, check=True,
    )
    setCfg('web_pg_username', email)
    setCfg('web_pg_password', password)


def initReplace():
    package = pgAdminPath()
    initPgConfFile(package)
    initPgDatabase(package)

    file_tpl = getPluginDir() + '/conf/pgadmin.conf'
    file_run = getConf()
    if not os.path.exists(file_run):
        content = mw.readFile(file_tpl)
        content = contentReplace(content)
        mw.writeFile(file_run, content)

    pass_path = getServerDir() + '/pg.pass'
    if not os.path.exists(pass_path):
        username = mw.getRandomString(8)
        password = mw.getRandomString(10)
        pass_cmd = username + ':' + mw.hasPwd(password)
        setCfg('username', username)
        setCfg('password', password)
        mw.writeFile(pass_path, pass_cmd)

    # systemd
    systemDir = mw.systemdCfgDir()
    systemService = systemDir + '/pgadmin.service'

    if os.path.exists(systemDir) and not os.path.exists(systemService):
        systemServiceTpl = getPluginDir() + '/init.d/pgadmin.service.tpl'
        service_path = mw.getServerDir()
        content = mw.readFile(systemServiceTpl)
        content = content.replace('{$SERVER_PATH}', service_path)
        content = content.replace('{$PGADMIN_PATH}', str(package))

        
        mw.writeFile(systemService, content)
        mw.execShell('systemctl daemon-reload')


def pgOp(method):
    file = initReplace()

    current_os = mw.getOs()
    if current_os == "darwin":
        return 'ok'

    if current_os.startswith("freebsd"):
        data = mw.execShell('service' + getPluginName() + ' ' + method)
        if data[1] == '':
            return 'ok'
        return data[1]

    data = mw.execShell('systemctl ' + method+ ' ' + getPluginName())
    if data[1] == '':
        return 'ok'
    return data[1]

def status():
    sock = '/tmp/pgadmin4.sock'
    if os.path.exists(sock):
        return 'start'
    return 'stop'


def start():
    initCfg()
    openPort()

    status = pgOp('start')
    if status != 'ok':
        return status
    mw.restartWeb()
    return 'ok'


def stop():
    pgOp('stop')

    conf = getConf()
    if os.path.exists(conf):
        os.remove(conf)

    delPort()
    mw.restartWeb()
    return 'ok'


def restart():
    cleanNginxLog()
    state = pgOp('restart')
    mw.restartWeb()
    return state


def reload():
    cleanNginxLog()
    return pgOp('reload')

def getPgOption():
    data = getCfg()
    return mw.returnJson(True, 'ok', data)


def getPgPort():
    try:
        port = getPort()
        return mw.returnJson(True, 'OK', port)
    except Exception as e:
        # print(e)
        return mw.returnJson(False, '插件未启动!')


def setPgPort():
    args = getArgs()
    data = checkArgs(args, ['port'])
    if not data[0]:
        return data[1]

    port = args['port']
    if port == '80':
        return mw.returnJson(False, '80端不能使用!')

    file = getConf()
    if not os.path.exists(file):
        return mw.returnJson(False, '插件未启动!')
    content = mw.readFile(file)
    rep = r'listen\s*(.*);'
    content = re.sub(rep, "listen " + port + ';', content)
    mw.writeFile(file, content)

    setCfg("port", port)
    mw.restartWeb()
    return mw.returnJson(True, '修改成功!')


def setPgUsername():
    args = getArgs()
    data = checkArgs(args, ['username'])
    if not data[0]:
        return data[1]

    username = args['username']
    setCfg('username', username)

    cfg = getCfg()
    pma_path = getServerDir() + '/pg.pass'
    username = mw.getRandomString(10)
    pass_cmd = cfg['username'] + ':' + mw.hasPwd(cfg['password'])
    mw.writeFile(pma_path, pass_cmd)

    mw.restartWeb()
    return mw.returnJson(True, '修改成功!')


def setPgPassword():
    args = getArgs()
    data = checkArgs(args, ['password'])
    if not data[0]:
        return data[1]

    password = args['password']
    setCfg('password', password)

    cfg = getCfg()
    pma_path = getServerDir() + '/pg.pass'
    username = mw.getRandomString(10)
    pass_cmd = cfg['username'] + ':' + mw.hasPwd(cfg['password'])
    mw.writeFile(pma_path, pass_cmd)

    mw.restartWeb()
    return mw.returnJson(True, '修改成功!')


def accessLog():
    return getServerDir() + '/access.log'

def errorLog():
    return getServerDir() + '/error.log'


def installVersion():
    return mw.readFile(getServerDir() + '/version.pl')

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
    elif func == 'conf':
        print(getConf())
    elif func == 'version':
        print(installVersion())
    elif func == 'get_cfg':
        print(returnCfg())
    elif func == 'get_home_page':
        print(getHomePage())
    elif func == 'get_pg_port':
        print(getPgPort())
    elif func == 'set_pg_port':
        print(setPgPort())
    elif func == 'get_pg_option':
        print(getPgOption())
    elif func == 'set_pg_username':
        print(setPgUsername())
    elif func == 'set_pg_password':
        print(setPgPassword())
    elif func == 'access_log':
        print(accessLog())
    elif func == 'error_log':
        print(errorLog())
    else:
        print('error')
