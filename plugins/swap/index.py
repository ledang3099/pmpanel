# coding:utf-8

import fcntl
import sys
import os
import subprocess
import tempfile

web_dir = os.getcwd() + "/web"
if os.path.exists(web_dir):
    sys.path.append(web_dir)
    os.chdir(web_dir)

import core.mw as mw

def getPluginName():
    return 'swap'


def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()


def getInitDTpl():
    path = getPluginDir() + "/init.d/" + getPluginName() + ".tpl"
    return path


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


def swapFile():
    return getServerDir() + '/swapfile'


def status():
    with open('/proc/swaps', encoding='utf-8') as swaps:
        next(swaps, None)
        return 'start' if any(line.split()[0] == swapFile() for line in swaps) else 'stop'


def systemUnit():
    if os.path.isdir('/run/systemd/system'):
        return mw.systemdCfgDir() + '/swap.service'
    return None


def initDreplace():
    app_dir = getServerDir() + '/init.d'
    os.makedirs(app_dir, exist_ok=True)
    script = app_dir + '/swap'
    template = mw.readFile(getInitDTpl())
    content = template.replace('{$SERVER_PATH}', swapFile())
    if not os.path.isfile(script) or mw.readFile(script) != content:
        mw.writeFile(script, content)
        os.chmod(script, 0o755)

    unit = systemUnit()
    if not unit:
        return script
    if os.path.isfile(unit):
        if 'ExecStart=' + script + ' start' not in mw.readFile(unit).splitlines():
            raise OSError('swap.service 已被其他服务占用。')
    else:
        unit_template = getPluginDir() + '/init.d/swap.service.tpl'
        mw.writeFile(unit, mw.readFile(unit_template).replace('{$SERVER_PATH}', mw.getServerDir()))
        subprocess.run(['systemctl', 'daemon-reload'], check=True)
    return script


def swapOp(method):
    script = initDreplace()
    if not systemUnit():
        subprocess.run([script, method], check=True)
        return
    subprocess.run(['systemctl', method, 'swap.service'], check=True)
    expected = 'stop' if method == 'stop' else 'start'
    if status() != expected:
        subprocess.run([script, method], check=True)


def serviceAction(method):
    try:
        swapOp(method)
    except (OSError, subprocess.CalledProcessError):
        return 'fail'
    return 'ok'


def start():
    return serviceAction('start')


def stop():
    return serviceAction('stop')


def restart():
    return serviceAction('restart')


def reload():
    return 'ok'


def initdStatus():
    if not systemUnit():
        return 'fail'
    result = subprocess.run(['systemctl', 'is-enabled', '--quiet', 'swap.service'])
    return 'ok' if result.returncode == 0 else 'fail'


def initdInstall():
    if not systemUnit():
        return 'fail'
    initDreplace()
    subprocess.run(['systemctl', 'enable', 'swap.service'], check=True)
    return 'ok'


def initdUinstall():
    if not systemUnit():
        return 'fail'
    initDreplace()
    subprocess.run(['systemctl', 'disable', 'swap.service'], check=True)
    return 'ok'


def swapStatus():
    file = swapFile()
    size = os.path.getsize(file) / 1024 / 1024 if os.path.isfile(file) else 0
    return mw.returnJson(True, "ok", {'size': size})


def resizeSwap(size):
    file = swapFile()
    disk = os.statvfs(getServerDir())
    if size * 1024 * 1024 > disk.f_bavail * disk.f_frsize:
        raise OSError('可用磁盘空间不足。')
    with tempfile.TemporaryDirectory(dir=getServerDir()) as temp_dir:
        staging = os.path.join(temp_dir, 'new')
        previous = os.path.join(temp_dir, 'old')
        fd = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
        subprocess.run(
            ['dd', 'if=/dev/zero', 'of=' + staging, 'bs=1M', 'count=' + str(size), 'status=none'],
            check=True,
        )
        subprocess.run(['mkswap', staging], check=True, stdout=subprocess.DEVNULL)
        was_active = status() == 'start'
        if was_active:
            swapOp('stop')
        if os.path.isfile(file):
            try:
                os.link(file, previous)
            except OSError:
                if was_active:
                    swapOp('start')
                raise
        try:
            os.replace(staging, file)
            swapOp('start')
        except (OSError, subprocess.CalledProcessError):
            if os.path.isfile(previous):
                os.replace(previous, file)
                if was_active:
                    swapOp('start')
            elif not os.path.exists(staging):
                os.unlink(file)
            raise


def changeSwap():
    size = getArgs().get('size', '').strip()
    if not size.isascii() or not size.isdecimal() or len(size) > 9 or int(size) < 1:
        return mw.returnJson(False, '请输入大于 0 的整数（MB）。')
    try:
        resizeSwap(int(size))
    except (OSError, subprocess.CalledProcessError) as exc:
        return mw.returnJson(False, '调整交换空间失败。' + str(exc))
    return mw.returnJson(True, '修改成功。')


def installSwap():
    if not os.path.isfile(swapFile()):
        resizeSwap(1024)
    else:
        swapOp('start')
    if systemUnit():
        initdInstall()


def uninstallSwap():
    unit = systemUnit()
    if unit and os.path.isfile(unit):
        initDreplace()
        swapOp('stop')
        initdUinstall()
        os.unlink(unit)
        subprocess.run(['systemctl', 'daemon-reload'], check=True)
    elif status() == 'start':
        subprocess.run(['swapoff', swapFile()], check=True)


if __name__ == "__main__":
    func = sys.argv[1]
    if func in {'start', 'stop', 'restart', 'install', 'uninstall', 'initd_install',
                'initd_uninstall', 'change_swap'}:
        lock = open(getServerDir() + '/.lock', 'a', encoding='utf-8')
        fcntl.flock(lock, fcntl.LOCK_EX)
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
    elif func == 'install':
        installSwap()
    elif func == 'uninstall':
        uninstallSwap()
    elif func == "swap_status":
        print(swapStatus())
    elif func == "change_swap":
        print(changeSwap())
    else:
        print('error')
