#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin

# for mac
export PATH=$PATH:/opt/homebrew/bin

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

# cd /Users/dev/Desktop/pmdev/server/pmpanel/plugins/keepalived && bash install.sh install 2.2.8
# cd /www/server/pmpanel/plugins/keepalived && bash install.sh install 2.2.8

# /www/server/keepalived/init.d/keepalived start

# systemctl status keepalived
# systemctl restart keepalived
# ifconfig

VERSION=$2

Install_App()
{
	echo '正在安装keepalived脚本文件...'
    if [ "$VERSION" != 2.4.3 ]; then return 1; fi
    source "$rootPath/scripts/tools/verified-download.sh" || return 1
    sources="$serverPath/source/keepalived"
    mkdir -p "$sources" || return 1
    archive="$sources/keepalived-$VERSION.tar.gz"
    verified_download "https://keepalived.org/software/keepalived-$VERSION.tar.gz" "$archive" \
        a0faef8e401c143487b131b526df7541c1e33d9b8814642fa9dfe8bb250a9632 || return 1
    tar -xzf "$archive" -C "$sources" || return 1
    cd "$sources/keepalived-$VERSION" || return 1
    ./configure --prefix="$serverPath/keepalived" && make && make install || return 1

	# for test
	# mkdir -p $serverPath/keepalived
	if [ -d $serverPath/keepalived ];then
		echo "${VERSION}" > $serverPath/keepalived/version.pl
		echo 'keepalived安装完成'

		cd ${rootPath} && python3 ${rootPath}/plugins/keepalived/index.py start
		cd ${rootPath} && python3 ${rootPath}/plugins/keepalived/index.py initd_install
	fi

	if [ -d $serverPath/source/keepalived/keepalived-${VERSION} ];then
		rm -rf $serverPath/source/keepalived/keepalived-${VERSION}
	fi
}

Uninstall_App()
{
	if [ -f /usr/lib/systemd/system/keepalived.service ];then
		systemctl stop keepalived
		systemctl disable keepalived
		rm -rf /usr/lib/systemd/system/keepalived.service
		systemctl daemon-reload
	fi

	if [ -f /lib/systemd/system/keepalived.service ];then
		systemctl stop keepalived
		systemctl disable keepalived
		rm -rf /lib/systemd/system/keepalived.service
		systemctl daemon-reload
	fi

	if [ -f $serverPath/keepalived/initd/keepalived ];then
		$serverPath/keepalived/initd/keepalived stop
	fi

	rm -rf $serverPath/keepalived
	echo "keepalived卸载完成"
}

action=$1
if [ "${1}" = 'install' ];then
	Install_App
else
	Uninstall_App
fi
