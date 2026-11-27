#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin:/opt/homebrew/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

# cd /Users/dev/Desktop/pmdev/server/pmpanel/plugins/cloudreve && bash install.sh install 3.8.3
# cd /www/server/pmpanel/plugins/cloudreve && bash install.sh install 3.8.3

VERSION=$2

sysArch=`arch`
sysName=`uname`

ALIST_ARCH_NAME=amd64
if [ "$sysArch" = "arm64" ];then
	ALIST_ARCH_NAME=arm64
elif [ "$sysArch" = "x86_64" ]; then
	ALIST_ARCH_NAME=amd64
elif [ "$sysArch" = "aarch64" ]; then
	ALIST_ARCH_NAME=aarch64
fi

ALIST_NAME=linux
if [ "$sysName" = "Darwin" ];then
	ALIST_NAME=darwin
fi

Install_App()
{
	echo '正在安装脚本文件...'

	mkdir -p $serverPath/source
	mkdir -p $serverPath/source/cloudreve

    FILE_TGZ="cloudreve_${VERSION}_${ALIST_NAME}_${ALIST_ARCH_NAME}.tar.gz"
    CLOUDREVE_DIR="$serverPath/source/cloudreve"
    url="https://github.com/cloudreve/Cloudreve/releases/download/${VERSION}/${FILE_TGZ}"
    destination="$serverPath/cloudreve/cloudreve"
    if [ "$VERSION" = 4.19.1 ]; then
        installed=
        if [ -f "$serverPath/cloudreve/version.pl" ]; then
            read -r installed < "$serverPath/cloudreve/version.pl"
        fi
        if [[ "$installed" == 3.* ]] || [ -f "$serverPath/cloudreve/cloudreve.db" ] || [ -f "$serverPath/cloudreve/conf.ini" ]; then
            echo 'Cloudreve V3 data detected. Use the upstream V3-to-V4 migration first.' >&2
            return 1
        fi
        case "$ALIST_NAME-$ALIST_ARCH_NAME" in
            linux-amd64) digest=287a1f59adb1249af15cd550b191d2fa71132bfd125fead8578f20152c4b99de ;;
            linux-arm64) digest=f55d77e0e5eb8bc699a9a6bb1216b0ee3afa3bfe8d7c9d405ca9845339ae7b0e ;;
            darwin-amd64) digest=f4dd69731ca52e39399a54dada5a8ec8a6bcb939ae70a70441f11882a6e270a0 ;;
            darwin-arm64) digest=a67577da69a77fd11246fc663604b6edabf3392149db764243bfcf496f581620 ;;
            *) return 1 ;;
        esac
        source "$rootPath/scripts/tools/verified-download.sh" || return 1
        source "$rootPath/scripts/tools/install-release-binary.sh" || return 1
        install_release_binary "$url" "$digest" "$CLOUDREVE_DIR/$FILE_TGZ" "$destination" || return 1
    else
        mkdir -p "$serverPath/cloudreve" || return 1
        curl -fsSL "$url" -o "$CLOUDREVE_DIR/$FILE_TGZ" || return 1
        tar -xzf "$CLOUDREVE_DIR/$FILE_TGZ" -C "$serverPath/cloudreve" || return 1
    fi
    printf '%s\n' "$VERSION" > "$serverPath/cloudreve/version.pl"
    cd "$rootPath" || return 1
    python3 plugins/cloudreve/index.py start || return 1
    python3 plugins/cloudreve/index.py initd_install || return 1

	echo '安装cloudreve完成'
}

Uninstall_App()
{
	if [ -f /usr/lib/systemd/system/cloudreve.service ];then
		systemctl stop cloudreve
		systemctl disable cloudreve
		rm -rf /usr/lib/systemd/system/cloudreve.service
		systemctl daemon-reload
	fi

	if [ -f /lib/systemd/system/cloudreve.service ];then
		systemctl stop cloudreve
		systemctl disable cloudreve
		rm -rf /lib/systemd/system/cloudreve.service
		systemctl daemon-reload
	fi

	if [ -f $serverPath/cloudreve/initd/cloudreve ];then
		$serverPath/cloudreve/initd/cloudreve stop
	fi

	if [ -d $serverPath/cloudreve ];then
		rm -rf $serverPath/cloudreve
	fi
	
	echo "卸载cloudreve成功"
}

action=$1
if [ "${1}" = 'install' ];then
	Install_App
else
	Uninstall_App
fi
