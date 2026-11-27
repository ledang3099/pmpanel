#!/usr/bin/env bash
set -e

action=$1
series=$2
case "$series" in
    84) php_version=8.4.28; php_digest=0c8ec360e5dd8154f270b2fd50cd44ecc824e6ee39c85f911312b80d4daecd72 ;;
    85) php_version=8.5.13; php_digest=607602acaf0c3061818e9916ec44a058e8b3d43959a83862b9cd3ec7bf5b785f ;;
    *) exit 1 ;;
esac
rapira_version=0.9.2
rapira_digest=cc5b32fbe0edd11f899bbed18d3980b3a184033469bb0cdfbdce94f6c0ed7cce
panel=$(cd "$(dirname "$0")/../../.." && pwd)
server=$(dirname "$panel")
runtime="$server/rapira/$series"
prefix="$runtime/link"

case "$action" in
    uninstall) rm -rf -- "$runtime"; exit 0 ;;
    install|upgrade) ;;
    *) exit 1 ;;
esac

source "$panel/scripts/tools/verified-download.sh"
sources="$server/source/rapira"
php_archive="$sources/php-$php_version.tar.xz"
php_url="https://www.php.net/distributions/php-$php_version.tar.xz"
release="$rapira_version/$php_version"
if [ -x "$runtime/bin/rapira" ] || [ -e "$prefix" ]; then
    if [ -x "$runtime/bin/rapira" ] && [ -f "$runtime/runtime-version" ] &&
        [ "$(cat "$runtime/runtime-version")" = "$release" ]; then
        # The bundled phpize installers request fresh matching sources here.
        if [ ! -d "$sources/php$series/ext" ]; then
            mkdir -p "$sources"
            verified_download "$php_url" "$php_archive" "$php_digest"
            stage=$(mktemp -d "$sources/ext-$series.XXXXXX")
            trap 'rm -rf -- "$stage"' EXIT
            tar -xJf "$php_archive" -C "$stage"
            mv -- "$stage/php-$php_version" "$sources/php$series"
        fi
        exit 0
    fi
    echo '检测到已有 Rapira 运行时。请先备份配置、站点和扩展，升级需重新安装并验证扩展。' >&2
    exit 1
fi

mkdir -p "$runtime/bin" "$sources"
stage=$(mktemp -d "$sources/install-$series.XXXXXX")
installed_php=0
cleanup() {
    rm -rf -- "$stage"
    if [ "$installed_php" = 1 ] && [ ! -x "$runtime/bin/rapira" ]; then
        rm -rf -- "$prefix"
    fi
}
trap cleanup EXIT

rapira_archive="$sources/rapira-$rapira_version.tar.gz"
verified_download "$php_url" "$php_archive" "$php_digest"
verified_download "https://codeload.github.com/rapira-rs/rapira/tar.gz/refs/tags/v$rapira_version" "$rapira_archive" "$rapira_digest"
tar -xJf "$php_archive" -C "$stage"
tar -xzf "$rapira_archive" -C "$stage"

export PATH="${CARGO_HOME:-$HOME/.cargo}/bin:$PATH"
if ! command -v cargo >/dev/null; then
    curl --proto '=https' --proto-redir '=https' -fsSL https://sh.rustup.rs -o "$stage/rustup-init.sh"
    sh "$stage/rustup-init.sh" -y --profile minimal
fi

cd "$stage/php-$php_version"
options=("--prefix=$prefix" --enable-embed=shared --enable-sockets --without-iconv --with-openssl)
if pkg-config --exists libargon2; then
    options+=(--with-password-argon2)
fi
if [ "$(uname -s)" = Darwin ]; then
    openssl=$(brew --prefix openssl@3)
    export PKG_CONFIG_PATH="$openssl/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
fi
./configure "${options[@]}"
make -j2
installed_php=1
make install

cd "$stage/rapira-$rapira_version"
PHP_CONFIG="$prefix/bin/php-config" CARGO_BUILD_JOBS=2 cargo build --locked --release --bin rapira
install -m 0755 target/release/rapira "$runtime/bin/rapira"
printf '%s\n' "$release" > "$runtime/runtime-version"
