#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

curPath=$(pwd)
rootPath=$(dirname "$(dirname "$curPath")")
serverPath=$(dirname "$rootPath")

if [ "$(uname -s)" != Linux ]; then
    echo 'Swap 插件需要 Linux。' >&2
    exit 1
fi
cd "$rootPath" || exit 1
case "$1" in
    install)
        mkdir -p "$serverPath/swap" || exit 1
        python3 plugins/swap/index.py install || exit 1
        printf '%s\n' "$2" > "$serverPath/swap/version.pl"
        ;;
    uninstall)
        python3 plugins/swap/index.py uninstall || exit 1
        rm -rf -- "$serverPath/swap"
        ;;
    *) exit 1 ;;
esac
