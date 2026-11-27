#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

sysArch=`arch`
sysName=`uname`


# cd /www/server/pmpanel && python3 plugins/xui/index.py info
# cd /www/server/pmpanel/plugins/xui && /bin/bash install.sh install 1.0

VERSION=$2
Install_app()
{
    if [ "$VERSION" != 1.0 ]; then return 1; fi
    bash "$curPath/install_xui.sh" || return 1
    cd "$rootPath" || return 1
    [ "$(python3 plugins/xui/index.py start)" = ok ] || return 1
    mkdir -p "$serverPath/xui" || return 1
    printf '%s\n' "$VERSION" > "$serverPath/xui/version.pl" || return 1
    echo '安装完成'

}

Uninstall_app()
{
	cd ${rootPath} && python3 plugins/xui/index.py stop
	
	rm -rf $serverPath/xui
	echo 'y' | x-ui uninstall
	rm -rf /usr/bin/x-ui 
	echo '卸载完成'
}

action=$1
case "$action" in
    install) Install_app ;;
    uninstall) Uninstall_app ;;
    *) exit 1 ;;
esac
