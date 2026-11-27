#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin:/opt/homebrew/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

# https://www.cnblogs.com/zlonger/p/16177595.html
# https://www.cnblogs.com/BNTang/articles/15841688.html

# ps -ef|grep valkey |grep -v grep | awk '{print $2}' | xargs kill

# cd /Users/dev/Desktop/pmdev/server/pmpanel/plugins/valkey && bash install.sh install 7.2.2

# cmd查看| info replication
# /Users/dev/Desktop/pmdev/server/valkey/bin/valkey-cli -h 127.0.0.1 -p 6399
# /www/server/valkey/bin/valkey-cli -h 127.0.0.1 -p 6399

VERSION=$2

Install_App()
{
	echo '正在安装脚本文件...'
    sources="$serverPath/source/valkey"
    mkdir -p "$sources" || return 1
    archive="$sources/$VERSION.tar.gz"
    url="https://codeload.github.com/valkey-io/valkey/tar.gz/refs/tags/$VERSION"
    if [ "$VERSION" = 9.2.1 ]; then
        source "$rootPath/scripts/tools/verified-download.sh" || return 1
        verified_download "$url" "$archive" fec5d34ac6f5c7f35cddcaae368734d8a789f1af2f7c29853e790f093d848d71 || return 1
    elif [ ! -f "$archive" ]; then
        curl -fsSL "$url" -o "$archive.part" && mv -f -- "$archive.part" "$archive" || return 1
    fi

    stage=$(mktemp -d "$sources/install.XXXXXX") || return 1
    trap 'rm -rf -- "$stage"' EXIT
    tar -xzf "$archive" -C "$stage" || return 1
    cd "$stage/valkey-$VERSION" || return 1
    make_command=make
    if command -v gmake >/dev/null; then make_command=gmake; fi
    "$make_command" -j2 PREFIX="$serverPath/valkey" install || return 1
    test -x "$serverPath/valkey/bin/valkey-server" || return 1
    mkdir -p "$serverPath/valkey/data" || return 1
    if [ ! -f "$serverPath/valkey/valkey.conf" ]; then
        sed '/^ *#/d' valkey.conf > "$serverPath/valkey/valkey.conf" || return 1
    fi

    printf '%s\n' "$VERSION" > "$serverPath/valkey/version.pl"
    cd "$rootPath" || return 1
    python3 plugins/valkey/index.py start || return 1
    python3 plugins/valkey/index.py initd_install || return 1

}

Uninstall_App()
{
	if [ -f /usr/lib/systemd/system/valkey.service ];then
		systemctl stop valkey
		systemctl disable valkey
		rm -rf /usr/lib/systemd/system/valkey.service
		systemctl daemon-reload
	fi

	if [ -f /lib/systemd/system/valkey.service ];then
		systemctl stop valkey
		systemctl disable valkey
		rm -rf /lib/systemd/system/valkey.service
		systemctl daemon-reload
	fi

	if [ -f $serverPath/valkey/initd/valkey ];then
		$serverPath/valkey/initd/valkey stop
	fi

	if [ -d $serverPath/valkey ];then
		rm -rf $serverPath/valkey
	fi
	
	echo "卸载valkey成功"
}

action=$1
if [ "${1}" = 'install' ];then
	Install_App
elif [ "$action" = uninstall ]; then
    Uninstall_App
else
    exit 1
fi
