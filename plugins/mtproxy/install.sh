#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

Install_app()
{
    local arch digest filename
    [ "$(uname -s)" = Linux ] || return 1
    case "$(uname -m)" in
        x86_64) arch=amd64; digest=11c038ea5eeebd5d49148048975c24f7b0c4fa4c1cf4f15a2410203e2da01812 ;;
        aarch64) arch=arm64; digest=86e0fc6f50bfb453b7a6e8b91497c6661a7d64a3f607828e0e42f534d795ac5a ;;
        armv7l) arch=armv7; digest=4be262a4099807700f1a62b11d993c096a6011a510975d82ea86ca72e49ccb89 ;;
        i386|i686) arch=386; digest=4f8fffa94bf4cad75a6b059d4a543efda62fc77921f4321186b6795269f3fe8e ;;
        *) return 1 ;;
    esac
    filename="mtg-2.3.0-linux-$arch.tar.gz"
    source "$rootPath/scripts/tools/verified-download.sh" || return 1
    source "$rootPath/scripts/tools/install-release-binary.sh" || return 1
    install_release_binary "https://github.com/9seconds/mtg/releases/download/v2.3.0/$filename" \
        "$digest" "$serverPath/source/mtproxy/$filename" "$serverPath/mtproxy/mtg/mtg" || return 1
    cd "$rootPath" || return 1
    [ "$(python3 plugins/mtproxy/index.py restart)" = ok ] || return 1
    [ "$(python3 plugins/mtproxy/index.py initd_install)" = ok ] || return 1
    printf '2.3.0\n' > "$serverPath/mtproxy/version.pl"
}

Uninstall_app()
{
	if [ -f /usr/lib/systemd/system/mtproxy.service ];then
		systemctl stop mtproxy
		rm -rf /usr/lib/systemd/system/mtproxy.service
		systemctl daemon-reload
	fi
	rm -rf ${serverPath}/mtproxy
	echo '卸载完成'
}

action=$1
case "$action" in
    install|upgrade) Install_app ;;
    uninstall) Uninstall_app ;;
    *) exit 1 ;;
esac
