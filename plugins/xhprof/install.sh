#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

sys_os=`uname`
Install_xh()
{
    version=$1
    target="$serverPath/xhprof"
    if [ "$version" = 2.3.10 ]; then
        source "$rootPath/scripts/tools/verified-download.sh" || return 1
        sources="$serverPath/source/xhprof"
        mkdir -p "$sources" || return 1
        archive="$sources/xhprof-$version.tgz"
        verified_download "https://pecl.php.net/get/xhprof-$version.tgz" "$archive" \
            251aee99c2726ebc6126e1ff0bb2db6e2d5fd22056aa335e84db9f1055d59d95 || return 1
        staging=$(mktemp -d "$sources/install.XXXXXX") || return 1
        trap 'rm -rf -- "$staging"' EXIT
        tar -xzf "$archive" -C "$staging" || return 1
        mkdir -p "$target" || return 1
        cp -R "$staging/xhprof-$version/xhprof_html" "$staging/xhprof-$version/xhprof_lib" "$target/" || return 1
    else
        mkdir -p "$target" || return 1
        if [ ! -d "$target/xhprof_lib" ]; then
            cp -R "$curPath/lib"/. "$target/" || return 1
        fi
    fi
    printf '%s\n' "$version" > "$target/version.pl"
	echo '安装完成'

	if [ "$sys_os" != "Darwin" ];then
		cd $rootPath && python3 ${rootPath}/plugins/xhprof/index.py start
	fi	
}

Uninstall_xh()
{
	if [ "$sys_os" != "Darwin" ];then
		cd $rootPath && python3 ${rootPath}/plugins/xhprof/index.py stop
	fi	

	rm -rf ${serverPath}/xhprof
	cd /tmp/xhprof && rm -rf *.xhprof

	if [ -f ${serverPath}/web_conf/nginx/vhost/xhprof.conf ];then
		rm -f ${serverPath}/web_conf/nginx/vhost/xhprof.conf
	fi
	echo '卸载完成'
}

action=$1
if [ "${1}" = 'install' ];then
	Install_xh $2
elif [ "$action" = uninstall ]; then
    Uninstall_xh
else
    exit 1
fi
