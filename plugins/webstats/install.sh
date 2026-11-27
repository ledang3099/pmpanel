#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH=$PATH:/opt/homebrew/bin


## https://www.yangshuaibin.com/detail/392251
# cd /www/server/pmpanel/plugins/webstats && bash install.sh install 0.2.5
# cd /Users/dev/Desktop/pmdev/server/pmpanel/plugins/webstats && bash install.sh install 0.2.5

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

VERSION=$2

if [ -f ${rootPath}/bin/activate ];then
	. ${rootPath}/bin/activate
fi

Install_App()
{
	echo '正在安装脚本文件...'
	mkdir -p $serverPath/source/webstats
	mkdir -p $serverPath/webstats

    runtime="$serverPath/webstats"
    sources="$serverPath/source/webstats"
    source "$rootPath/scripts/tools/install-lua-sqlite.sh" || return 1
    install_lua_sqlite "$rootPath" "$runtime" "$runtime/lua" || return 1
    python3 -m pip install geoip2 || return 1

    file=GeoLite2-City.mmdb
    if [ ! -s "$runtime/$file" ]; then
        source "$rootPath/scripts/tools/verified-download.sh" || return 1
        verified_download "https://github.com/P3TERX/GeoLite.mmdb/releases/download/2026.11.25/$file" \
            "$sources/$file" d317770c39fdf63c4b7d4914ddb21df581a8be312c047f57539e739c127ce4ef || return 1
        install -m 0644 "$sources/$file" "$runtime/$file" || return 1
    fi

    cd "$rootPath" || return 1
    [ "$(python3 plugins/webstats/index.py start)" = ok ] || return 1
    printf '%s\n' "$VERSION" > "$runtime/version.pl" || return 1
    echo '网站统计安装完成'

}

Uninstall_App()
{
	cd $rootPath && python3 plugins/webstats/index.py stop
	rm -rf $serverPath/webstats
	echo "网站统计卸载完成"
}

action=$1
case "$action" in
    install) Install_App ;;
    uninstall) Uninstall_App ;;
    *) exit 1 ;;
esac
