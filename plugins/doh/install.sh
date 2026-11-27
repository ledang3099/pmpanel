#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

if [ -f ${rootPath}/bin/activate ];then
	. ${rootPath}/bin/activate
fi


# cd /www/server/pmpanel/plugins/doh && bash install.sh install 0.9.15

# /www/server/doh/doh-proxy --config /www/server/doh/config.toml
# /www/server/doh/doh-proxy --config /www/server/doh/config.toml --check


# /www/server/doh/doh-proxy -u 127.0.0.1:53 -l 127.0.0.1:3000

# 详细状态信息
# sudo systemctl status doh -l
# 查看完整日志
# sudo journalctl -u doh -n 100
# 实时日志跟踪
# sudo journalctl -u doh -f


URL_DOWNLOAD=https://github.com/DNSCrypt/doh-server/releases/download


bash ${rootPath}/scripts/getos.sh
OSNAME=`cat ${rootPath}/data/osname.pl`
OSNAME_ID=`cat /etc/*-release | grep VERSION_ID | awk -F = '{print $2}' | awk -F "\"" '{print $2}'`

Install_App()
{

    [ "$(uname -s)" = Linux ] || return 1
    local version="$1"
    local architecture digest file archive url
    case "$(uname -m)" in
        x86_64) architecture=x86_64; digest=7ce97a4ed3d9deee9d2b1de71bb60013f46188f5d2a085fbf230bf4c8e3c8b25 ;;
        aarch64) architecture=aarch64; digest=579f63372b23e904761d3b12aeb5aa3031403dda1d03f95288b0ef5b21e8c36c ;;
        *) return 1 ;;
    esac
    file="doh-proxy_${version}_linux-${architecture}.tar.bz2"
    archive="$serverPath/source/doh/$file"
    url="$URL_DOWNLOAD/$version/$file"
    if [ "$version" = 0.11.1 ]; then
        source "$rootPath/scripts/tools/verified-download.sh" || return 1
        source "$rootPath/scripts/tools/install-release-binary.sh" || return 1
        install_release_binary "$url" "$digest" "$archive" "$serverPath/doh/doh-proxy" || return 1
    else
        mkdir -p "$serverPath/source/doh" "$serverPath/doh" || return 1
        curl -fsSL "$url" -o "$archive" || return 1
        tar -xjf "$archive" -C "$serverPath/doh" || return 1
    fi
    printf '%s\n' "$version" > "$serverPath/doh/version.pl"
    cd "$rootPath" || return 1
    python3 plugins/doh/index.py start || return 1
    python3 plugins/doh/index.py initd_install || return 1

	echo 'install doh success'
}

Uninstall_App()
{

	if [ -f /usr/lib/systemd/system/doh.service ];then
		systemctl stop doh
		systemctl disable doh
		rm -rf /usr/lib/systemd/system/doh.service
		systemctl daemon-reload
	fi

	rm -rf $serverPath/doh
	echo 'uninstall doh success'
}


action=$1
version=$2
if [ "${1}" = 'install' ];then
	Install_App $version
else
	Uninstall_App $version
fi
