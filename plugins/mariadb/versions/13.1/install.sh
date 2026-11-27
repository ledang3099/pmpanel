#!/usr/bin/env bash
set -e

panel=$(cd ../.. && pwd)
server=$(dirname "$panel")
runtime="$server/mariadb"
case "$1" in
    uninstall) rm -rf -- "$runtime"; exit 0 ;;
    install) ;;
    *) exit 1 ;;
esac

if [ "$(uname -s)-$(uname -m)" != Linux-x86_64 ]; then
    echo 'MariaDB 13.1 官方二进制需要 Linux x86_64。' >&2
    exit 1
fi
if [ -e "$runtime" ]; then
    if [ -x "$runtime/bin/mariadbd" ] && [ "$(cat "$runtime/version.pl" 2>/dev/null)" = 13.1 ]; then
        exit 0
    fi
    echo '检测到已安装的 MariaDB。请使用官方迁移流程升级数据库。' >&2
    exit 1
fi

source "$panel/scripts/tools/verified-download.sh"
sources="$server/source/mariadb"
mkdir -p "$sources"
file=mariadb-13.1.2-linux-systemd-x86_64.tar.gz
archive="$sources/$file"
verified_download "https://downloads.mariadb.org/rest-api/mariadb/13.1.2/$file" "$archive" \
    649ae1ea36f381cdcb8e11694637eca3106ec81ac4cd7e3c813d6192b2d6de38
stage=$(mktemp -d "$server/.mariadb-install.XXXXXX")
trap 'rm -rf -- "$stage"' EXIT
tar -xzf "$archive" -C "$stage" --strip-components=1
"$stage/bin/mariadbd" --no-defaults --version
test -x "$stage/scripts/mariadb-install-db"
mkdir -p /var/log/mariadb
printf '13.1\n' > "$stage/version.pl"
chmod 0755 "$stage"
mv -T -- "$stage" "$runtime"
