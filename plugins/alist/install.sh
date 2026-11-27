#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin:/opt/homebrew/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

# cd /Users/dev/Desktop/pmdev/server/pmpanel/plugins/alist && bash install.sh install 3.37.4
# cd /www/server/pmpanel/plugins/alist && bash install.sh install 3.45.0

VERSION=$2

sysArch=`arch`
sysName=`uname`

ALIST_ARCH_NAME=amd64
if [ "$sysArch" = "arm64" ];then
	ALIST_ARCH_NAME=arm64
elif [ "$sysArch" = "x86_64" ]; then
	ALIST_ARCH_NAME=amd64
elif [ "$sysArch" = "aarch64" ]; then
	ALIST_ARCH_NAME=arm64
fi

ALIST_NAME=linux
if [ "$sysName" = "Darwin" ];then
	ALIST_NAME=darwin
fi

Install_App()
{
	echo '正在安装脚本文件...'

	mkdir -p $serverPath/source
	mkdir -p $serverPath/source/alist

    FILE_TGZ="alist-${ALIST_NAME}-${ALIST_ARCH_NAME}.tar.gz"
    ALIST_DIR="$serverPath/source/alist"
    url="https://github.com/alist-org/alist/releases/download/v${VERSION}/${FILE_TGZ}"
    destination="$serverPath/alist/alist"
    if [ "$VERSION" = 3.66.0 ]; then
        case "$ALIST_NAME-$ALIST_ARCH_NAME" in
            linux-amd64) digest=06a2ab394c1bce4d29b84021192aa75350f556bd1a1e98d321ad760170b5ed31 ;;
            linux-arm64) digest=675d8cb633830ebeefc8d172ccad3f17ea85b9d28daa4d969cfb73e9d01f83d3 ;;
            darwin-amd64) digest=21bef6a127788a4b3903860493337a9c4b472e776a5f8414f87f0207f5a1d288 ;;
            darwin-arm64) digest=b9657f62df0f9648a309fe6db7ad6fef806b228df98076c363af9390d57f1bb4 ;;
            *) return 1 ;;
        esac
        source "$rootPath/scripts/tools/verified-download.sh" || return 1
        source "$rootPath/scripts/tools/install-release-binary.sh" || return 1
        install_release_binary "$url" "$digest" "$ALIST_DIR/$VERSION/$FILE_TGZ" "$destination" || return 1
    else
        mkdir -p "$ALIST_DIR/$VERSION" "$serverPath/alist" || return 1
        curl -fsSL "$url" -o "$ALIST_DIR/$VERSION/$FILE_TGZ" || return 1
        tar -xzf "$ALIST_DIR/$VERSION/$FILE_TGZ" -C "$serverPath/alist" || return 1
    fi
    printf '%s\n' "$VERSION" > "$serverPath/alist/version.pl"
    cd "$rootPath" || return 1
    python3 plugins/alist/index.py start || return 1
    python3 plugins/alist/index.py initd_install || return 1

	echo '安装完成'
}

Uninstall_App()
{
	if [ -f /usr/lib/systemd/system/alist.service ];then
		systemctl stop alist
		systemctl disable alist
		rm -rf /usr/lib/systemd/system/alist.service
		systemctl daemon-reload
	fi

	if [ -f /lib/systemd/system/alist.service ];then
		systemctl stop alist
		systemctl disable alist
		rm -rf /lib/systemd/system/alist.service
		systemctl daemon-reload
	fi

	if [ -f $serverPath/alist/initd/alist ];then
		$serverPath/alist/initd/alist stop
	fi

	if [ -d $serverPath/alist ];then
		rm -rf $serverPath/alist
	fi
	
	echo "卸载alist成功"
}

action=$1
if [ "${1}" = 'install' ];then
	Install_App
elif [ "$action" = uninstall ]; then
    Uninstall_App
else
    exit 1
fi
