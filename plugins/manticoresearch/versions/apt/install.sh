#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin:/opt/homebrew/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")
sysName=`uname`
sysArch=`arch`

if [ -f ${rootPath}/bin/activate ];then
	. ${rootPath}/bin/activate
fi

VERSION=$2
action=$1

Install_App()
{
	echo '正在安装manticoresearch...'
    repo_package=$(mktemp --suffix=.deb) || return 1
    trap 'rm -f -- "$repo_package"' EXIT
    curl --proto '=https' --proto-redir '=https' -fsSL --retry 2 \
        https://repo.manticoresearch.com/manticore-repo.noarch.deb -o "$repo_package" || return 1
    apt-get update || return 1
    # APT installs dependencies of the local repository package as well.
    chmod 0644 "$repo_package" || return 1
    apt-get install -y "$repo_package" || return 1
    apt-get update || return 1
    apt-get install -y manticore || return 1
    mkdir -p "$serverPath/manticoresearch" || return 1

	echo "${VERSION}" > $serverPath/manticoresearch/version.pl

	cd ${rootPath} && python3 plugins/manticoresearch/index.py start ${VERSION}
	cd ${rootPath} && python3 plugins/manticoresearch/index.py initd_install ${VERSION}

	# if [ -d ${MC_DIR} ];then
	# 	rm -rf ${MC_DIR}
	# fi
}

Uninstall_App()
{
	cd ${rootPath} && python3 plugins/manticoresearch/index.py stop ${VERSION}
	cd ${rootPath} && python3 plugins/manticoresearch/index.py initd_uninstall ${VERSION}

	apt -y remove manticore
	apt -y remove manticore-extra
	apt -y autoremove

	if [ -d $serverPath/manticoresearch ];then
		rm -rf $serverPath/manticoresearch
	fi
	
	if [ -f /usr/lib/systemd/system/manticore.service ] || [ -f /lib/systemd/system/manticore.service ];then
		systemctl stop manticore
		systemctl disable manticore
		rm -rf /usr/lib/systemd/system/manticore.service
		rm -rf /lib/systemd/system/manticore.service
		systemctl daemon-reload
	fi

	echo "卸载manticoresearch成功"
}


if [ "${1}" = 'install' ] || [ "$action" = "upgrade" ];then
	Install_App
elif [ "${1}" = 'uninstall' ];then
	Uninstall_App
else
	echo "OPTIONS ERROR"
fi
