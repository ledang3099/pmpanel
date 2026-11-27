#!/usr/bin/env bash
set -e

server=$(cd ../../.. && pwd)
runtime="$server/php-yum/86"
case "$1" in
    install)
        yum install -y php86 php86-php-fpm
        mkdir -p "$runtime"
        ;;
    uninstall)
        yum remove -y 'php86*'
        rm -rf -- "$runtime"
        ;;
    *) exit 1 ;;
esac
