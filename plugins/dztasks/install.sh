#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin:/opt/homebrew/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

# cd /Users/dev/Desktop/pmdev/server/pmpanel/plugins/dztasks && bash install.sh install 1.0
# cd /wwww/server/pmpanel/plugins/dztasks && bash install.sh install 1.0
VERSION=$2
sysArch=`arch`
sysName=`uname`

DZ_ARCH_NAME=amd64
if [ "$sysArch" = "arm64" ];then
	DZ_ARCH_NAME=arm64
elif [ "$sysArch" = "x86_64" ]; then
	DZ_ARCH_NAME=amd64
elif [ "$sysArch" = "aarch64" ]; then
	DZ_ARCH_NAME=arm64
fi

DZ_NAME=linux
if [ "$sysName" = "Darwin" ];then
	DZ_NAME=darwin
fi
Install_App()
{
	echo '正在安装脚本文件...'
	mkdir -p $serverPath/source
	mkdir -p $serverPath/source/dztasks
	mkdir -p $serverPath/dztasks

    if [ "$VERSION" != 1.2 ]; then return 1; fi
    case "$DZ_NAME-$DZ_ARCH_NAME" in
        darwin-amd64) digest=a00c8071b3e33d445571c87f0239739e66e86d6ff45b2d33b4b36d639239e9ae ;;
        darwin-arm64) digest=693c2bac3c72ac032fad4e5d7582efaa07e5d8c52efda0906fcedbc6614b6d1b ;;
        linux-amd64) digest=ca61cc174d3e151816e529c1119dfeda51aedd25c24c9269c7b9b03ea39151c2 ;;
        linux-arm64) digest=9f930716b84835b92d2f03730dc64c7cc1f3e66cfc2fdaac72579f63676975b2 ;;
        *) return 1 ;;
    esac
    source "$rootPath/scripts/tools/verified-download.sh" || return 1
    file="dztasks_${VERSION}_${DZ_NAME}_${DZ_ARCH_NAME}.tar.gz"
    archive="$serverPath/source/dztasks/$file"
    verified_download "https://github.com/midoks/dztasks/releases/download/$VERSION/$file" "$archive" "$digest" || return 1
    staging=$(mktemp -d "$serverPath/source/dztasks/install.XXXXXX") || return 1
    trap 'rm -rf -- "$staging"' EXIT
    tar -xzf "$archive" -C "$staging" || return 1
    install -m 0755 "$staging/dztasks" "$serverPath/dztasks/dztasks" || return 1
    if [ -d "$staging/plugins" ]; then
        mkdir -p "$serverPath/dztasks/plugins" || return 1
        cp -Rn "$staging/plugins"/. "$serverPath/dztasks/plugins/" || return 1
    fi

	echo "${VERSION}" > $serverPath/dztasks/version.pl
	cd ${rootPath} && python3 ${rootPath}/plugins/dztasks/index.py start
	cd ${rootPath} && python3 ${rootPath}/plugins/dztasks/index.py initd_install

	echo '安装dztasks成功!'
}

Uninstall_App()
{
	if [ -f /usr/lib/systemd/system/dztasks.service ];then
		systemctl stop dztasks
		systemctl disable dztasks
		rm -rf /usr/lib/systemd/system/dztasks.service
		systemctl daemon-reload
	fi

	if [ -f /lib/systemd/system/dztasks.service ];then
		systemctl stop dztasks
		systemctl disable dztasks
		rm -rf /lib/systemd/system/dztasks.service
		systemctl daemon-reload
	fi

	if [ -f $serverPath/dztasks/initd/dztasks ];then
		$serverPath/dztasks/initd/dztasks stop
	fi

	if [ -d $serverPath/dztasks ];then
		rm -rf $serverPath/dztasks
	fi
	
	echo "卸载dztasks成功"
}

action=$1
if [ "${1}" = 'install' ];then
	Install_App
elif [ "$action" = uninstall ]; then
    Uninstall_App
else
    exit 1
fi
