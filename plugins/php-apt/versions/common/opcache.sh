#!/usr/bin/env bash
set -e

version=$2
runtime=$(cd ../../../../.. && pwd)/php-apt
conf_dir="/etc/php/$version/fpm/conf.d"
panel_conf="$conf_dir/99-pmpanel-opcache.ini"
blacklist="$runtime/opcache-blacklist.txt"

case "$1" in
    install)
        if "/usr/bin/php$version" -n -r 'exit(extension_loaded("Zend OPcache") ? 0 : 1);'; then
            old_conf="$conf_dir/10-opcache.ini"
            if [ -f "$old_conf" ] && grep -q '^opcache.blacklist_filename=.*php-apt/opcache-blacklist.txt$' "$old_conf"; then
                sed -i '/^[[:space:]]*zend_extension[[:space:]]*=[[:space:]]*opcache\.so[[:space:]]*$/d' "$old_conf"
            fi
        else
            apt-get install -y "php$version-opcache"
        fi
        mkdir -p "$runtime" "$conf_dir"
        touch "$blacklist"
        if [ ! -e "$panel_conf" ]; then
            cat >"$panel_conf" <<INI
opcache.enable=1
opcache.memory_consumption=128
opcache.interned_strings_buffer=8
opcache.max_accelerated_files=4000
opcache.revalidate_freq=60
opcache.enable_cli=1
opcache.jit=1205
opcache.jit_buffer_size=64M
opcache.save_comments=0
opcache.blacklist_filename=$blacklist
INI
        fi
        ;;
    uninstall)
        if [ -e "$panel_conf" ]; then unlink "$panel_conf"; fi
        ;;
    *) exit 1 ;;
esac
