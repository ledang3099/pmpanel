#!/usr/bin/env bash

install_redis() (
    panel=$(cd ../.. && pwd) || return 1
    server=$(dirname "$panel")
    source "$panel/scripts/tools/verified-download.sh" || return 1
    sources="$server/source/redis"
    mkdir -p "$sources" || return 1
    archive="$sources/redis-8.12.0.tar.gz"
    verified_download https://download.redis.io/releases/redis-8.12.0.tar.gz "$archive" \
        b0100a879b2d45dc97d8fda941127609d648f8913008db1b65a2f72a8ae36c8b || return 1
    stage=$(mktemp -d "$sources/install.XXXXXX") || return 1
    trap 'rm -rf -- "$stage"' EXIT
    tar -xzf "$archive" -C "$stage" || return 1
    cd "$stage/redis-8.12.0" || return 1
    make_command=make
    if command -v gmake >/dev/null; then make_command=gmake; fi
    "$make_command" -j2 PREFIX="$server/redis" install || return 1
    test -x "$server/redis/bin/redis-server" || return 1
    mkdir -p "$server/redis/data" || return 1
    if [ ! -f "$server/redis/redis.conf" ]; then
        sed '/^ *#/d' redis.conf > "$server/redis/redis.conf" || return 1
    fi
    printf '8.12\n' > "$server/redis/version.pl"
)

case "$1" in
    install|upgrade) install_redis ;;
    uninstall) exit 0 ;;
    *) exit 1 ;;
esac
