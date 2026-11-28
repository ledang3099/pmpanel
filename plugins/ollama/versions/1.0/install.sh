#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

VERSION=0.40.18

Install_App()
{
    [ "$(uname -s)" = Linux ] || return 1
    source "$rootPath/scripts/tools/verified-download.sh" || return 1
    sources="$serverPath/source/ollama"
    mkdir -p "$sources" || return 1
    installer="$sources/install-$VERSION.sh"
    verified_download "https://github.com/ollama/ollama/releases/download/v$VERSION/install.sh" "$installer" \
        17659c2456c9e65a3b11056b76da51774911cb822f47bf44f7f3ecc0c40528a8 || return 1
    OLLAMA_VERSION="$VERSION" sh "$installer" || return 1
    command -v ollama >/dev/null || return 1
    mkdir -p "$serverPath/ollama" || return 1
    printf '%s\n' "$VERSION" > "$serverPath/ollama/version.pl"
    cd "$rootPath" || return 1
    [ "$(python3 plugins/ollama/index.py start)" = ok ]
}

Uninstall_App()
{
	cd ${rootPath} && python3 ${rootPath}/plugins/ollama/index.py stop

	systemctl stop ollama.service
	systemctl disable ollama.service
	rm -rf /etc/systemd/system/ollama.service
	systemctl daemon-reload
	rm -rf $(which ollama)
	rm -rf /usr/share/ollama
	rm -rf ~/.ollama

	userdel ollama
	groupdel ollama

	if command -v apt &> /dev/null; then
		apt remove -y ollama
	fi

	rm -rf $serverPath/ollama
	echo "install fail"
}

action=$1
if [ "${1}" = 'install' ];then
	Install_App
elif [ "$action" = uninstall ]; then
    Uninstall_App
else
    exit 1
fi
