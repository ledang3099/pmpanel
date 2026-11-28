# coding:utf-8

import sys
import io
import os
import time
import re

web_dir = os.getcwd() + "/web"
if os.path.exists(web_dir):
    sys.path.append(web_dir)
    os.chdir(web_dir)

import core.mw as mw


def runSystemctl(cmd):
    """
    执行 systemctl(参数列表, 不经过 shell), 按退出码判断成败: 成功返回 '', 失败返回错误信息。
    注意 systemctl enable 会把 "Created symlink ..." 写到 stderr, 不能把 stderr 非空当作失败。
    """
    import shlex
    import subprocess
    p = subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode == 0:
        return ''
    return (p.stderr or p.stdout).strip() or ('%s 执行失败(%d)' % (cmd, p.returncode))

app_debug = False
if mw.isAppleSystem():
    app_debug = True


def getPluginName():
    return 'loki'


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
    path = getServerDir() + "/conf/loki-config.yaml"
    return path

def collectorService():
    if getInstallVerion() == '3.7.10':
        return 'pmpanel-loki-alloy'
    return 'promtail'


def getPromtailConf():
    if collectorService() == 'pmpanel-loki-alloy':
        return getServerDir() + '/conf/collector.alloy'
    return getServerDir() + '/conf/promtail-config.yaml'


def getConfTpl():
    path = getPluginDir() + "/conf/loki-config.yaml"
    return path

def getPromtailConfTpl():
    path = getPluginDir() + "/conf/promtail-config.yaml"
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
    cmd = "ps -ef|grep loki |grep -v grep | grep -v python | grep -v pmpanel | awk '{print $2}'"
    data = mw.execShell(cmd)
    if data[0] == '':
        return 'stop'
    return 'start'

def getInstallVerion():
    version_pl = getServerDir() + "/version.pl"
    version = (mw.readFile(version_pl) or "").strip()
    return version

def contentReplace(content):
    service_path = mw.getServerDir()
    content = content.replace('{$ROOT_PATH}', mw.getFatherDir())
    content = content.replace('{$SERVER_PATH}', service_path)
    content = content.replace('{$APP_PATH}', service_path+"/loki")
    content = content.replace('{$LOG_PATH}', service_path+"/loki/logs")
    return content


# def openPort():
#     try:
#         from utils.firewall import Firewall as MwFirewall
#         MwFirewall.instance().addAcceptPort('3000', 'grafana', 'port')
#         return port
#     except Exception as e:
#         return "Release failed {}".format(e)
#     return True


def initDreplace():
    # 初始化OP配置
    init_file = getServerDir() + '/init.pl'
    if not os.path.exists(init_file):
        # openPort()
        mw.writeFile(init_file, 'ok')

    conf_dir = getServerDir()+'/conf'
    if not os.path.exists(conf_dir):
        mw.execShell('mkdir -p ' + conf_dir)

    file_tpl = getConfTpl()
    dst_file = getConf()
    if not os.path.exists(dst_file):
        content = mw.readFile(file_tpl)
        content = contentReplace(content)
        mw.writeFile(dst_file, content)


    file_tpl = getPromtailConfTpl()
    dst_file = getPromtailConf()
    if collectorService() == "promtail" and not os.path.exists(dst_file):
        content = mw.readFile(file_tpl)
        content = contentReplace(content)
        mw.writeFile(dst_file, content)

    # systemd
    systemDir = mw.systemdCfgDir()
    systemService = systemDir + '/' + getPluginName() + '.service'
    if os.path.exists(systemDir) and not os.path.exists(systemService):
        systemServiceTpl = getPluginDir() + '/init.d/' + getPluginName() + '.service.tpl'
        service_path = mw.getServerDir()
        content = mw.readFile(systemServiceTpl)
        content = content.replace('{$SERVER_PATH}', service_path)
        mw.writeFile(systemService, content)
        mw.execShell('systemctl daemon-reload')

    # systemd
    systemDir = mw.systemdCfgDir()
    collector = collectorService()
    systemService = systemDir + '/' + collector + '.service'
    if os.path.exists(systemDir) and not os.path.exists(systemService):
        systemServiceTpl = getPluginDir() + '/init.d/' + collector + '.service.tpl'
        service_path = mw.getServerDir()
        content = mw.readFile(systemServiceTpl)
        content = content.replace('{$SERVER_PATH}', service_path)
        mw.writeFile(systemService, content)
        mw.execShell('systemctl daemon-reload')

    return True


def gOp(method):
    initDreplace()

    err = runSystemctl('systemctl ' + method + ' '+getPluginName())
    if err:
        return err

    err = runSystemctl('systemctl ' + method + ' ' + collectorService())
    if err:
        return err
    return 'ok'


def start():
    return gOp('start')

def stop():
    return gOp('stop')

def restart():
    return gOp('restart')

def reload():
    return gOp('reload')

def initdStatus():
    current_os = mw.getOs()
    if current_os == 'darwin':
        return "Apple Computer does not support"

    shell_cmd = 'systemctl status loki|grep loaded|grep "enabled;"'
    data = mw.execShell(shell_cmd)
    if data[0] == '':
        return 'fail'

    shell_cmd = 'systemctl status ' + collectorService() + '|grep loaded|grep "enabled;"'
    data = mw.execShell(shell_cmd)
    if data[0] == '':
        return 'fail'
    return 'ok'


def initdInstall():
    current_os = mw.getOs()
    if current_os == 'darwin':
        return "Apple Computer does not support"

    err = runSystemctl('systemctl enable loki')
    if err:
        return err

    err = runSystemctl('systemctl enable ' + collectorService())
    if err:
        return err
    return 'ok'


def initdUinstall():
    current_os = mw.getOs()
    if current_os == 'darwin':
        return "Apple Computer does not support"

    err = runSystemctl('systemctl disable loki')
    if err:
        return err

    err = runSystemctl('systemctl disable ' + collectorService())
    if err:
        return err
    return 'ok'

def grafanaUrl():
    ip = mw.getLocalIp()
    return 'http://'+ip+':'+"3100"

def installPreInspection():
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
        print(installPreInspection())
    elif func == 'uninstall_pre_inspection':
        print(uninstallPreInspection())
    elif func == 'conf':
        print(getConf())
    elif func == 'promtail_conf':
        print(getPromtailConf())
    elif func == 'grafana_url':
        print(grafanaUrl())
    else:
        print('error')
