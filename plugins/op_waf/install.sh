#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin:/opt/homebrew/bin
export PATH

# cd /www/server/pmpanel/plugins/op_waf && bash install.sh install 0.4.1
# cd /www/server/pmpanel && python3 plugins/op_waf/index.py start
# cd /www/server/pmpanel && python3 plugins/op_waf/index.py stop
# cd /www/server/pmpanel && python3 plugins/op_waf/tool_task.py run

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

action=$1
version=$2

if [ -f ${rootPath}/bin/activate ];then
	. ${rootPath}/bin/activate
fi

# /www/server/openresty/luajit/bin/luajit /www/server/op_waf/waf/lua/waf_common.lua
# /www/server/openresty/luajit/bin/luajit -bl /www/server/op_waf/waf/lua/waf_common.lua
# /www/server/openresty/luajit/bin/luajit /www/server/web_conf/nginx/lua/access_by_lua_file.lua


Install_App(){
	
	echo '正在安装脚本文件...'
	mkdir -p $serverPath/source/op_waf
	mkdir -p $serverPath/op_waf

    runtime="$serverPath/op_waf"
    sources="$serverPath/source/op_waf"
    source "$rootPath/scripts/tools/install-lua-sqlite.sh" || return 1
    install_lua_sqlite "$rootPath" "$runtime" "$runtime/waf/conf" || return 1
    source "$rootPath/scripts/tools/verified-download.sh" || return 1

    geo_release=https://github.com/P3TERX/GeoLite.mmdb/releases/download/2026.11.25
    for edition in City Country; do
        case "$edition" in
            City) digest=d317770c39fdf63c4b7d4914ddb21df581a8be312c047f57539e739c127ce4ef ;;
            Country) digest=e256d9c92775f33b57579df55765c2fa1ea656c03c2461861e0f34260816be14 ;;
        esac
        file="GeoLite2-$edition.mmdb"
        if [ ! -s "$runtime/$file" ]; then
            verified_download "$geo_release/$file" "$sources/$file" "$digest" || return 1
            install -m 0644 "$sources/$file" "$runtime/$file" || return 1
        fi
    done

    lib_file=libmaxminddb-1.14.1.tar.gz
    archive="$sources/$lib_file"
    verified_download "https://github.com/maxmind/libmaxminddb/releases/download/1.14.1/$lib_file" "$archive" \
        ca5c87d41339f8bc4daabb53e8a9356b3c995f2d2419b85d7bff823b2ecc252d || return 1
    stage=$(mktemp -d "$sources/build.XXXXXX") || return 1
    trap 'rm -rf -- "$stage"' EXIT
    tar -xzf "$archive" -C "$stage" || return 1
    cd "$stage/libmaxminddb-1.14.1" || return 1
    ./configure --prefix="$runtime/waf/mmdb" && make && make install || return 1

    cd "$rootPath" || return 1
    [ "$(python3 plugins/op_waf/index.py start)" = ok ] || return 1
    python3 plugins/op_waf/index.py reload || return 1
    printf '%s\n' "$version" > "$runtime/version.pl" || return 1
    echo '安装OP防火墙成功!'

}

Uninstall_App(){
	cd ${rootPath} && python3 ${rootPath}/plugins/op_waf/index.py stop
	if [ "$?" = "0" ];then
		rm -rf $serverPath/op_waf
	fi
}


action=$1
case "$action" in
    install) Install_App ;;
    uninstall) Uninstall_App ;;
    *) exit 1 ;;
esac
