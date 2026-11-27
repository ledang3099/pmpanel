#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin:/opt/homebrew/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")
sysName=`uname`
sysArch=`arch`

# cd /Users/dev/Desktop/pmdev/server/pmpanel/plugins/gorse && bash install.sh install 0.4.15
# cd /www/server/pmpanel/plugins/gorse && bash install.sh install 0.4.15

VERSION=$2

Install_App()
{
	echo '正在安装脚本文件...'
	mkdir -p $serverPath/source
	mkdir -p $serverPath/source/gorse

	SYSNAME=linux
	if [ "$sysName" = "Darwin" ];then
		SYSNAME=darwin
	fi

	ARCH="amd64"
	if [ "$sysArch" = "x86_64" ];then
		ARCH="amd64"
	elif [ "$sysArch" = "aarch64" ];then
		ARCH="arm64"
	elif [ "$sysArch" = "arm64" ];then
		ARCH="arm64"
	else
		ARCH="amd64"
	fi

    file="gorse_${SYSNAME}_${ARCH}.zip"
    sources="$serverPath/source/gorse"
    archive="$sources/${VERSION}-$file"
    url="https://github.com/gorse-io/gorse/releases/download/v$VERSION/$file"
    if [ "$VERSION" = 0.5.11 ]; then
        case "$SYSNAME-$ARCH" in
            linux-amd64) digest=615e1830ec7b0f6f8ef8ccb13adc5a0d80af821e6a4ebcb23673629a8d8590fe ;;
            linux-arm64) digest=5cdb74f0dbc946e54321ff05da4b600593db35b94560aa7675e64f05f38e0c9c ;;
            darwin-arm64) digest=2849ffd1dde10c60ab9a575243d62789e7df784b51ea15b7d4e797ce2ba9ef29 ;;
            *) echo 'Unsupported Gorse platform' >&2; return 1 ;;
        esac
        source "$rootPath/scripts/tools/verified-download.sh" || return 1
        verified_download "$url" "$archive" "$digest" || return 1
    elif [ ! -f "$archive" ]; then
        curl -fsSL --retry 2 "$url" -o "$archive.part" && mv -- "$archive.part" "$archive" || return 1
    fi

    stage=$(mktemp -d "$sources/install.XXXXXX") || return 1
    trap 'rm -rf -- "$stage"' EXIT
    unzip -q "$archive" -d "$stage" || return 1
    test -x "$stage/gorse-in-one" || return 1
    mkdir -p "$serverPath/gorse/"{bin,logs,data} || return 1
    cp -R "$stage"/. "$serverPath/gorse/bin/" || return 1

    printf '%s\n' "$VERSION" > "$serverPath/gorse/version.pl"
    cd "$rootPath" || return 1
    [ "$(python3 plugins/gorse/index.py start)" = ok ] || return 1
    if [ "$sysName" != Darwin ]; then
        [ "$(python3 plugins/gorse/index.py initd_install)" = ok ] || return 1
    fi
    echo '安装Gorse完成'

}

Uninstall_App()
{
	app_name=gorse
	systemctl_dir=/lib/systemd/system
	if [ -d /usr/lib/systemd/system ];then
		systemctl_dir=/usr/lib/systemd/system
	fi

	if [ -f ${systemctl_dir}/${app_name}.service ];then
		systemctl stop ${app_name}
		systemctl disable ${app_name}
		rm -rf ${systemctl_dir}/${app_name}.service
		systemctl daemon-reload
	fi

	if [ -f $serverPath/${app_name}/initd/${app_name} ];then
		$serverPath/${app_name}/initd/${app_name} stop
	fi

	if [ -d $serverPath/${app_name} ];then
		rm -rf $serverPath/${app_name}
	fi
	
	echo "卸载Gorse成功"
}

action=$1
if [ "${1}" = 'install' ];then
	Install_App
else
	Uninstall_App
fi
