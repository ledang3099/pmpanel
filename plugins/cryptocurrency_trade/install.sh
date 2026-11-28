#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

# cd /www/server/pmpanel/plugins/cryptocurrency_trade && bash install.sh install

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")


VERSION=$2

if [ -f "$rootPath/bin/activate" ]; then
    source "$rootPath/bin/activate"
fi

Install_App()
{
	    echo '正在安装脚本文件...'
    python3 -m pip install --only-binary=TA-Lib ccxt==4.5.94 TA-Lib==0.8.3.post1 pandas \
        'pandas-ta==0.4.71b0; python_version >= "3.12"' || return 1

    runtime="$serverPath/cryptocurrency_trade"
    mkdir -p "$runtime" || return 1
    cd "$rootPath" || return 1
    python3 plugins/cryptocurrency_trade/index.py status >/dev/null || return 1
    printf '%s\n' "$VERSION" > "$runtime/version.pl" || return 1
    echo '安装完成'

}

Uninstall_App()
{
	rm -rf $serverPath/cryptocurrency_trade
	cd ${rootPath} && python3 ${rootPath}/plugins/cryptocurrency_trade/index.py stop
	echo "卸载完成"
}

action=$1
case "$action" in
    install) Install_App ;;
    uninstall) Uninstall_App ;;
    *) exit 1 ;;
esac
