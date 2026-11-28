#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

# pip install pyinotify
if [ -f ${rootPath}/bin/activate ];then
	. ${rootPath}/bin/activate
fi
# cd /www/server/pmpanel/plugins/tamper_proof_py && bash install.sh install 1.0

# cd /www/server/pmpanel && python3 plugins/tamper_proof_py/index.py start 1.0
# cd /www/server/pmpanel && python3 plugins/tamper_proof_py/index.py service_admin  {"serviceStatus":"start"}
# systemctl start tamper_proof_py
# systemctl status tamper_proof_py

SYSOS=`uname`
VERSION=$2
APP_NAME=tamper_proof_py

Install_App()
{
    python3 -m pip install pyinotify==0.9.6 'pyasyncore==1.0.5; python_version >= "3.12"' || return 1
    python3 -c 'import pyinotify' || return 1
	echo '正在安装脚本文件...'
	mkdir -p $serverPath/tamper_proof_py
    cd "$rootPath" || return 1
    python3 plugins/tamper_proof_py/index.py start "$VERSION" || return 1
    python3 plugins/tamper_proof_py/index.py initd_install "$VERSION" || return 1
    if [ "$SYSOS" = Linux ]; then systemctl is-active --quiet tamper_proof_py || return 1; fi
    printf '%s\n' "$VERSION" > "$serverPath/tamper_proof_py/version.pl" || return 1
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

	rm -rf $serverPath/tamper_proof_py
	echo "uninstall completed"
}

action=$1
if [ "${1}" = 'install' ];then
	Install_App
else
	Uninstall_App
fi
