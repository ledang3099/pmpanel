#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin:/opt/homebrew/bin
export PATH=$PATH:/opt/homebrew/bin

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

VERSION=${2:-1.0}

# cd /Users/dev/Desktop/pmdev/server/pmpanel/plugins/lvs && bash install.sh install 1.0
# cd /www/server/pmpanel/plugins/lvs && bash install.sh install 1.0


Install_LVS(){
    if ! command -v ipvsadm >/dev/null; then
        if command -v apt-get >/dev/null; then
            apt-get install -y ipvsadm || return 1
        elif command -v dnf >/dev/null; then
            dnf install -y ipvsadm || return 1
        elif command -v yum >/dev/null; then
            yum install -y ipvsadm || return 1
        else
            echo '找不到 ipvsadm 或支持的包管理器' >&2
            return 1
        fi
    fi
    command -v ipvsadm >/dev/null || return 1
    mkdir -p "$serverPath/lvs" || return 1
    cd "$rootPath" || return 1
    python3 plugins/lvs/index.py start || return 1
    python3 plugins/lvs/index.py initd_install || return 1
    printf '%s\n' "$VERSION" > "$serverPath/lvs/version.pl"
}

Uninstall_LVS()
{
	# 检测平台命令
	which apt
	if [ "$?" = "0" ];then
		apt remove -y ipvsadm
	fi

	which yum
	if [ "$?" = "0" ];then
		yum uninstall -y ipvsadm
	fi
	echo "卸载LVS完成"

	if [ -d $serverPath/lvs ];then
		rm -rf $serverPath/lvs
	fi
}

action=$1
if [ "${1}" = 'install' ];then
	Install_LVS
else
	Uninstall_LVS
fi
