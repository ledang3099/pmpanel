#!/usr/bin/env bash
set -e

server=$(cd ../../.. && pwd)
runtime="$server/php-apt/86"
case "$1" in
    install)
        apt-get install -y php8.6 php8.6-fpm php8.6-dev
        mkdir -p "$runtime"
        ;;
    upgrade)
        apt-get install -y --only-upgrade php8.6 php8.6-fpm php8.6-dev
        ;;
    uninstall)
        apt-get remove -y 'php8.6*'
        rm -rf -- "$runtime"
        ;;
    *) exit 1 ;;
esac
