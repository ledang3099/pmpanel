# coding:utf-8

import sys
import io
import os
import time
import re
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

web_dir = os.getcwd() + "/web"
if os.path.exists(web_dir):
    sys.path.append(web_dir)
    os.chdir(web_dir)

import core.mw as mw
import thisdb
from utils.site import sites as MwSites

app_debug = False
if mw.isAppleSystem():
    app_debug = True


def getPluginName():
    return 'lam'


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
    return mw.getServerDir() + '/web_conf/nginx/vhost/lam.conf'


def getConfInc():
    return getServerDir() + "/" + getCfg()['path'] + '/config/config.cfg'


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
        rand_path = cfg['path']
        url = 'http://' + auth + '@' + ip + ':' + port + '/' + rand_path + '/templates/login.php'
        return mw.returnJson(True, 'OK', url)
    except Exception as e:
        return mw.returnJson(False, '插件未启动!')


def getPhpVer():
    versions = MwSites.instance().getPhpVersion()
    if isinstance(versions, dict):
        versions = versions['data']
    conf_dir = mw.getServerDir() + '/web_conf/php/conf'
    enabled = []
    for version in versions:
        name = str(version['version'])
        match = re.search(r'(?:^|\D)(8)\.?([0-9])(?:\D|$)', name)
        if match and tuple(map(int, match.groups())) >= (8, 2):
            if os.path.isfile(os.path.join(conf_dir, f'enable-php-{name}.conf')):
                enabled.append((tuple(map(int, match.groups())), name))
    return max(enabled, default=((), ''))[1]


def getCachePhpVer():
    cacheFile = getServerDir() + '/php.pl'
    v = ''
    if os.path.exists(cacheFile):
        v = mw.readFile(cacheFile).strip()
    conf = mw.getServerDir() + '/web_conf/php/conf/enable-php-' + v + '.conf'
    if not v or not os.path.isfile(conf):
        v = getPhpVer()
        mw.writeFile(cacheFile, v)
    return v


def contentReplace(content):
    service_path = mw.getServerDir()
    php_ver = getCachePhpVer()
    tmp = mw.execShell('cat /dev/urandom | head -n 32 | md5sum | head -c 16')
    blowfish_secret = tmp[0].strip()
    # print php_ver
    php_conf_dir = mw.getServerDir() + '/web_conf/php/conf'
    content = content.replace('{$ROOT_PATH}', mw.getFatherDir())
    content = content.replace('{$SERVER_PATH}', service_path)
    content = content.replace('{$PHP_CONF_PATH}', php_conf_dir)
    content = content.replace('{$PHP_VER}', php_ver)
    content = content.replace('{$BLOWFISH_SECRET}', blowfish_secret)

    cfg = getCfg()
    content = content.replace('{$PMA_PATH}', cfg['path'])

    port = cfg["port"]
    rep = r'listen\s*(.*);'
    content = re.sub(rep, "listen " + port + ';', content)
    return content


def initCfg():
    cfg = getServerDir() + "/cfg.json"
    if not os.path.exists(cfg):
        data = {}
        data['port'] = '987'
        data['path'] = ''
        data['username'] = 'admin'
        data['password'] = 'admin'
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


def status():
    conf = getConf()
    conf_inc = getServerDir() + "/" + getCfg()["path"] + '/config/config.cfg'
    # 两个文件都在，才算启动成功
    if os.path.exists(conf) and os.path.exists(conf_inc):
        return 'start'
    return 'stop'


def __release_port(port):
    from collections import namedtuple
    try:
        from utils.firewall import Firewall as MwFirewall
        MwFirewall.instance().addAcceptPort(port, 'LAM默认端口', 'port')
        return port
    except Exception as e:
        return "Release failed {}".format(e)


def __delete_port(port):
    from collections import namedtuple
    try:
        from utils.firewall import Firewall as MwFirewall
        MwFirewall.instance().delAcceptPortCmd(port, 'tcp')
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


def start():
    if not getCachePhpVer():
        return '请先安装并配置 PHP 8.2 或更高版本。'
    initCfg()
    openPort()

    pma_dir = getServerDir() + "/lam"
    if os.path.exists(pma_dir):
        rand_str = mw.getRandomString(6)
        rand_str = rand_str.lower()
        pma_dir_dst = pma_dir + "_" + rand_str
        mw.execShell("mv " + pma_dir + " " + pma_dir_dst)
        mw.execShell("chown -R www:www " + pma_dir_dst)
        mw.execShell("chmod -R 777 " + pma_dir_dst+'/sess')
        mw.execShell("chmod -R 777 " + pma_dir_dst+'/tmp')
        setCfg('path', 'lam_' + rand_str)

    file_tpl = getPluginDir() + '/conf/lam.conf'
    file_run = getConf()
    if not os.path.exists(file_run):
        centent = mw.readFile(file_tpl)
        centent = contentReplace(centent)
        mw.writeFile(file_run, centent)

    pma_path = getServerDir() + '/pma.pass'
    if not os.path.exists(pma_path):
        username = mw.getRandomString(8)
        password = mw.getRandomString(10)
        pass_cmd = username + ':' + mw.hasPwd(password)
        setCfg('username', username)
        setCfg('password', password)
        mw.writeFile(pma_path, pass_cmd)

    tmp = getServerDir() + "/" + getCfg()["path"] + '/tmp'
    if not os.path.exists(tmp):
        os.mkdir(tmp)
        mw.execShell("chown -R www:www " + tmp)

    conf_run = getServerDir() + "/" + getCfg()["path"] + '/config/config.cfg'
    if not os.path.exists(conf_run):
        conf_tpl = getPluginDir() + '/conf/config.cfg'
        centent = mw.readFile(conf_tpl)
        centent = contentReplace(centent)
        mw.writeFile(conf_run, centent)

    log_a = accessLog()
    log_e = errorLog()

    for i in [log_a, log_e]:
        if os.path.exists(i):
            cmd = "echo '' > " + i
            mw.execShell(cmd)

    mw.restartWeb()
    return 'ok'


def stop():
    conf = getConf()
    if os.path.exists(conf):
        os.remove(conf)
    delPort()
    mw.restartWeb()
    return 'ok'


def restart():
    return start()


def reload():
    file_tpl = getPluginDir() + '/conf/lam.conf'
    file_run = getConf()
    if os.path.exists(file_run):
        centent = mw.readFile(file_tpl)
        centent = contentReplace(centent)
        mw.writeFile(file_run, centent)
    return start()


def setPhpVer():
    args = getArgs()

    if not 'phpver' in args:
        return 'phpver missing'

    cacheFile = getServerDir() + '/php.pl'
    mw.writeFile(cacheFile, args['phpver'])

    file_tpl = getPluginDir() + '/conf/lam.conf'
    file_run = getConf()

    content = mw.readFile(file_tpl)
    content = contentReplace(content)
    mw.writeFile(file_run, content)

    mw.restartWeb()
    return 'ok'


def getSetPhpVer():
    cacheFile = getServerDir() + '/php.pl'
    if os.path.exists(cacheFile):
        return mw.readFile(cacheFile).strip()
    return ''


def getPmaOption():
    data = getCfg()
    return mw.returnJson(True, 'ok', data)


def getPmaPort():
    try:
        port = getPort()
        return mw.returnJson(True, 'OK', port)
    except Exception as e:
        # print(e)
        return mw.returnJson(False, '插件未启动!')


def setPmaPort():
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


def setPmaUsername():
    args = getArgs()
    data = checkArgs(args, ['username'])
    if not data[0]:
        return data[1]

    username = args['username']
    setCfg('username', username)

    cfg = getCfg()
    pma_path = getServerDir() + '/pma.pass'
    username = mw.getRandomString(10)
    pass_cmd = cfg['username'] + ':' + mw.hasPwd(cfg['password'])
    mw.writeFile(pma_path, pass_cmd)

    mw.restartWeb()
    return mw.returnJson(True, '修改成功!')


def setPmaPassword():
    args = getArgs()
    data = checkArgs(args, ['password'])
    if not data[0]:
        return data[1]

    password = args['password']
    setCfg('password', password)

    cfg = getCfg()
    pma_path = getServerDir() + '/pma.pass'
    username = mw.getRandomString(10)
    pass_cmd = cfg['username'] + ':' + mw.hasPwd(cfg['password'])
    mw.writeFile(pma_path, pass_cmd)

    mw.restartWeb()
    return mw.returnJson(True, '修改成功!')


def setPmaPath():
    args = getArgs()
    data = checkArgs(args, ['path'])
    if not data[0]:
        return data[1]

    path = args['path']

    if len(path) < 5:
        return mw.returnJson(False, '不能小于5位!')

    old_path = getServerDir() + "/" + getCfg()['path']
    new_path = getServerDir() + "/" + path

    mw.execShell("mv " + old_path + " " + new_path)
    setCfg('path', path)
    return mw.returnJson(True, '修改成功!')


def accessLog():
    return getServerDir() + '/access.log'


def errorLog():
    return getServerDir() + '/error.log'


def installVersion():
    return mw.readFile(getServerDir() + '/version.pl')

def deployedApp():
    name = getCfg()['path']
    if not name or name in ('.', '..') or Path(name).name != name:
        raise ValueError('LAM 应用目录无效。')
    app = Path(getServerDir()) / name
    if not app.is_dir() or app.is_symlink():
        raise ValueError('未找到 LAM 应用目录。')
    return app


def upgradeApp(source):
    active = deployedApp()
    if (active / 'VERSION').read_text().strip() != '9.0' or (source / 'VERSION').read_text().strip() != '9.7':
        raise ValueError('此升级仅支持 LAM 9.0 到 9.7。')

    old_cfg = active / 'config'
    if old_cfg.is_symlink():
        raise ValueError('请先按上游说明备份并迁移外部配置目录。')
    configs = [old_cfg / 'config.cfg'] + [path for path in old_cfg.glob('*.conf') if not path.name.endswith('.sample.conf')]
    for path in configs:
        try:
            if path.is_symlink() or not isinstance(json.loads(path.read_text(encoding='utf-8')), dict):
                raise ValueError
        except (OSError, ValueError) as exc:
            raise ValueError(f'{path.name} 需先在 LAM 9.0 中重新保存为 JSON。') from exc

    backup_root = Path(mw.getServerDir()) / '.lam-upgrades'
    backup_root.mkdir(mode=0o700, exist_ok=True)
    if backup_root.is_symlink():
        raise ValueError('LAM 升级备份目录异常。')
    backup = Path(tempfile.mkdtemp(prefix='from-9.0-', dir=backup_root))
    previous, staged = backup / 'previous', backup / 'staged'
    try:
        shutil.copytree(source, staged)
        for path in configs:
            shutil.copy2(path, staged / 'config' / path.name)
        for name in ('pdf', 'profiles'):
            path = old_cfg / name
            if path.exists():
                if path.is_symlink() or any(entry.is_symlink() for entry in path.rglob('*')):
                    raise ValueError(f'{name} 含符号链接，需手动迁移。')
                shutil.copytree(path, staged / 'config' / name, dirs_exist_ok=True)
        if not mw.isAppleSystem():
            subprocess.run(['chown', '-R', 'www:www', str(staged)], check=True)
        marker = backup / 'version.pl'
        marker.write_text('9.7\n', encoding='utf-8')
        active.rename(previous)
        try:
            staged.rename(active)
            marker.replace(active.parent / 'version.pl')
        except OSError:
            if active.exists():
                active.rename(staged)
            previous.rename(active)
            raise
    finally:
        shutil.rmtree(staged, ignore_errors=True)
    print(f'旧版应用已保存到 {previous}')


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
    elif func == 'upgrade_check':
        update = (installVersion() or '').strip() == '9.0'
        print(mw.returnJson(update, 'ok', '9.7' if update else ''))
    elif func == 'deployed_version':
        print((deployedApp() / 'VERSION').read_text(encoding='utf-8').strip())
    elif func == 'upgrade_app':
        try:
            upgradeApp(Path(sys.argv[2]))
        except (OSError, ValueError, subprocess.CalledProcessError) as exc:
            print(str(exc), file=sys.stderr)
            sys.exit(1)
    elif func == 'get_cfg':
        print(returnCfg())
    elif func == 'config_inc':
        print(getConfInc())
    elif func == 'get_home_page':
        print(getHomePage())
    elif func == 'set_php_ver':
        print(setPhpVer())
    elif func == 'get_set_php_ver':
        print(getSetPhpVer())
    elif func == 'get_pma_port':
        print(getPmaPort())
    elif func == 'set_pma_port':
        print(setPmaPort())
    elif func == 'get_pma_option':
        print(getPmaOption())
    elif func == 'set_pma_username':
        print(setPmaUsername())
    elif func == 'set_pma_password':
        print(setPmaPassword())
    elif func == 'set_pma_path':
        print(setPmaPath())
    elif func == 'access_log':
        print(accessLog())
    elif func == 'error_log':
        print(errorLog())
    else:
        print('error')
