#!/usr/bin/env bash

install_lua_sqlite() (
    panel=$1
    runtime=$2
    module_dir=$3
    server=$(dirname "$panel")
    luajit="$server/openresty/luajit"
    if [ ! -x "$luajit/bin/luajit" ]; then
        echo '请先安装 OpenResty 和 LuaJIT。' >&2
        return 1
    fi
    source "$panel/scripts/tools/verified-download.sh" || return 1
    sources="$server/source/lua-sqlite"
    mkdir -p "$sources" "$module_dir" || return 1
    luarocks="$sources/luarocks-3.13.0.tar.gz"
    rock="$sources/lsqlite3-0.9.7-1.src.rock"
    verified_download https://luarocks.org/releases/luarocks-3.13.0.tar.gz "$luarocks" \
        245bf6ec560c042cb8948e3d661189292587c5949104677f1eecddc54dbe7e37 || return 1
    verified_download https://luarocks.org/manifests/javierguerragiraldez/lsqlite3-0.9.7-1.src.rock "$rock" \
        29889cd8366849128d02e6080178af91b776b01ffb22564b9508a0a4e4888af1 || return 1
    stage=$(mktemp -d "$sources/build.XXXXXX") || return 1
    trap 'rm -rf -- "$stage"' EXIT
    tar -xzf "$luarocks" -C "$stage" || return 1
    cd "$stage/luarocks-3.13.0" || return 1
    ./configure --prefix="$runtime/luarocks" --lua-version=5.1 \
        --with-lua="$luajit" --with-lua-interpreter=luajit \
        --with-lua-include="$luajit/include/luajit-2.1" || return 1
    make && make install || return 1

    sqlite_args=()
    if [ "$(uname -s)" = Darwin ] && command -v brew >/dev/null; then
        sqlite_prefix=$(brew --prefix sqlite) || return 1
        sqlite_args+=("SQLITE_DIR=$sqlite_prefix")
    fi
    "$runtime/luarocks/bin/luarocks" --tree="$stage/rocks" install \
        --deps-mode=none "$rock" "${sqlite_args[@]}" || return 1
    module="$stage/rocks/lib/lua/5.1/lsqlite3.so"
    LUA_CPATH="$stage/rocks/lib/lua/5.1/?.so" "$luajit/bin/luajit" \
        -e 'local sqlite = require "lsqlite3"; local db = sqlite.open_memory(); assert(db:exec("SELECT 1") == sqlite.OK); db:close()' || return 1
    install -m 0644 "$module" "$module_dir/lsqlite3.so.new" || return 1
    mv -f -- "$module_dir/lsqlite3.so.new" "$module_dir/lsqlite3.so"
)
