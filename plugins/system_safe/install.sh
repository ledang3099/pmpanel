#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

SYSOS=`uname`
VERSION=$2
APP_NAME=system_safe

# cd /www/server/pmpanel && python3 plugins/system_safe/system_safe.py stop 1.0

if [ -f "$rootPath/bin/activate" ]; then
    source "$rootPath/bin/activate"
fi

Install_App()
{
    echo '正在安装脚本文件...'
    if [ "$SYSOS" = Linux ] && { ! command -v chattr >/dev/null || ! command -v lsattr >/dev/null; }; then
        if command -v apt-get >/dev/null; then
            apt-get install -y e2fsprogs || return 1
        elif command -v dnf >/dev/null; then
            dnf install -y e2fsprogs || return 1
        elif command -v yum >/dev/null; then
            yum install -y e2fsprogs || return 1
        else
            echo 'System Safe requires chattr and lsattr from e2fsprogs.' >&2
            return 1
        fi
    fi
    mkdir -p "$serverPath/system_safe" || return 1
    cd "$rootPath" || return 1
    python3 plugins/system_safe/system_safe.py start "$VERSION" || return 1
    python3 plugins/system_safe/system_safe.py initd_install "$VERSION" || return 1
    printf '%s\n' "$VERSION" > "$serverPath/system_safe/version.pl" || return 1
    echo 'install complete'

}

Uninstall_App()
{
	
	if [ -f /usr/lib/systemd/system/${APP_NAME}.service ] || [ -f /lib/systemd/system/${APP_NAME}.service ] ;then
		systemctl stop ${APP_NAME}
		systemctl disable ${APP_NAME}
		rm -rf /usr/lib/systemd/system/${APP_NAME}.service
		rm -rf /lib/systemd/system/${APP_NAME}.service
		systemctl daemon-reload
	fi

	rm -rf $serverPath/system_safe
	echo "uninstall completed"
}

action=$1
if [ "${1}" = 'install' ];then
	Install_App
else
	Uninstall_App
fi
