#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

VERSION=$2

# cd /www/server/pmpanel/plugins/supervisor && bash install.sh install 1.0
# /www/server/pmpanel/bin/supervisord -n -c /etc/supervisor/supervisord.conf
# /www/server/pmpanel/bin/supervisorctl  -c /www/server/supervisor/supervisor.conf
# cmd | status
# systemctl status supervisor
# journalctl -u supervisor -f

bash ${rootPath}/scripts/getos.sh
OSNAME=`cat ${rootPath}/data/osname.pl`
OSNAME_ID=`cat /etc/*-release | grep VERSION_ID | awk -F = '{print $2}' | awk -F "\"" '{print $2}'`


if [ -f ${rootPath}/bin/activate ];then
	. ${rootPath}/bin/activate
fi

Install_app()
{
	echo '正在安装[supervisor]...'
	mkdir -p $serverPath/source
	mkdir -p $serverPath/supervisor
	mkdir -p $serverPath/supervisor/log
	mkdir -p $serverPath/supervisor/run

    python3 -m pip install supervisor==4.3.0 || return 1
    cd "$rootPath" || return 1
    [ "$(python3 plugins/supervisor/index.py start)" = ok ] || return 1
    if [ "$(uname)" = Linux ]; then
        systemctl is-active --quiet supervisor && systemctl enable supervisor || return 1
    fi
    printf '%s\n' "$VERSION" > "$serverPath/supervisor/version.pl" || return 1
    echo '安装完成[supervisor]'

}

Uninstall_app()
{

	if [ -f /usr/lib/systemd/system/supervisor.service ] || [ -f /lib/systemd/system/supervisor.service ];then
		systemctl stop supervisor
		systemctl disable supervisor
		rm -rf /usr/lib/systemd/system/supervisor.service
		rm -rf /lib/systemd/system/supervisor.service
		systemctl daemon-reload
	fi

	pip uninstall supervisor -y

	rm -rf $serverPath/supervisor

	echo "卸载完成[supervisor]"
}

action=$1
if [ "${1}" = 'install' ];then
	Install_app
else
	Uninstall_app
fi
