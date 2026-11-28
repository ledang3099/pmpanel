#!/usr/bin/env bash
set -e

panel=$(cd ../.. && pwd)
server=$(dirname "$panel")
runtime="$server/apache"
sources="$server/source/apache"

case "$1" in
    install) if [ -x "$runtime/httpd/bin/httpd" ]; then exit 0; fi ;;
    upgrade) ;;
    uninstall) exit 0 ;;
    *) exit 1 ;;
esac

source "$panel/scripts/tools/verified-download.sh"
mkdir -p "$sources"
apr=apr-1.7.6
apu=apr-util-1.6.6
httpd=httpd-2.4.71
download=https://dlcdn.apache.org
verified_download "$download/apr/$apr.tar.gz" "$sources/$apr.tar.gz" \
    6a10e7f7430510600af25fabf466e1df61aaae910bf1dc5d10c44a4433ccc81d
verified_download "$download/apr/$apu.tar.gz" "$sources/$apu.tar.gz" \
    acd5f38440eda830e40c4fe35c2a6b8119493cfdba9c9d73d985c317beb4e4f8
verified_download "$download/httpd/$httpd.tar.bz2" "$sources/$httpd.tar.bz2" \
    2bc5da5a33c247341de082717d4ebcb5cb49e8b73a05b7fddf7d5d6dc2f8de62
stage=$(mktemp -d "$sources/build.XXXXXX")
trap 'rm -rf -- "$stage"' EXIT

apr_prefix="$runtime/$apr"
apu_prefix="$runtime/$apu"
if [ ! -x "$apr_prefix/bin/apr-1-config" ]; then
    tar -xzf "$sources/$apr.tar.gz" -C "$stage"
    cd "$stage/$apr"
    ./configure --prefix="$apr_prefix"
    make -j2
    make install
fi
if [ ! -x "$apu_prefix/bin/apu-1-config" ]; then
    tar -xzf "$sources/$apu.tar.gz" -C "$stage"
    cd "$stage/$apu"
    ./configure --prefix="$apu_prefix" --with-apr="$apr_prefix/bin/apr-1-config"
    make -j2
    make install
fi
tar -xjf "$sources/$httpd.tar.bz2" -C "$stage"
cd "$stage/$httpd"
options=("--prefix=$runtime/httpd" "--with-apr=$apr_prefix/bin/apr-1-config"
    "--with-apr-util=$apu_prefix/bin/apu-1-config" --with-mpm=event --enable-mods-shared=most)
if pkg-config --exists libbrotlienc; then options+=(--enable-brotli=shared); fi
./configure "${options[@]}"
make -j2
make install
"$runtime/httpd/bin/httpd" -v
