#!/usr/bin/env bash

set -e

panel=$(cd "$(dirname "$0")/../../../.." && pwd)
server=$(dirname "$panel")
sources="$server/source/mongodb"
target="$server/mongodb/bin"

case "$(uname -m)" in
    arm64)
        arch=arm64
        shell_arch=arm64
        server_sha=8e057ec463a52cfdea4b1b8f5d5108a622d9116dfff76332854b3627db772833
        shell_sha=d1a226a2fa1eb6c68c7203aea933d2283b1430481fbd68e08967e51feb596ff5
        tools_sha=2d49b4bd58477ce7ffbad2c4d1a686f2befa3ce27e8c7cf8fcd2869d8f73063a
        ;;
    x86_64)
        arch=x86_64
        shell_arch=x64
        server_sha=8e8d7d147ff5cca0ece5acd2097b2ac21cbe096df75a737f756cf4bf99a71d4c
        shell_sha=06891d5c7d8a1d24845badab5e4398e63022a12bad5863b25e16ea959d67b2a3
        tools_sha=de677258cb2dd2f8dfce714021dcf5ebdd812b07f391118d3af5200370d2f67c
        ;;
    *) exit 1 ;;
esac

if [ -x "$target/mongod" ] && ! "$target/mongod" --version | grep -q '^db version v9\.0\.'; then
    echo 'MongoDB 9.0 requires a supported major-version migration before replacing the existing server.' >&2
    exit 1
fi

archive="mongodb-macos-$arch-9.0.8.tgz"
shell="mongosh-2.14.3-darwin-$shell_arch.zip"
tools="mongodb-database-tools-macos-$arch-100.20.1.zip"

source "$panel/scripts/tools/verified-download.sh"
mkdir -p "$sources"
verified_download "https://fastdl.mongodb.org/osx/$archive" "$sources/$archive" "$server_sha"
verified_download "https://downloads.mongodb.com/compass/$shell" "$sources/$shell" "$shell_sha"
verified_download "https://fastdl.mongodb.org/tools/db/$tools" "$sources/$tools" "$tools_sha"

stage=$(mktemp -d "$sources/install.XXXXXX")
trap 'rm -rf -- "$stage"' EXIT
mkdir "$stage/server"
tar -xzf "$sources/$archive" --strip-components=1 -C "$stage/server"
unzip -q "$sources/$shell" -d "$stage"
unzip -q "$sources/$tools" -d "$stage"
server_bin="$stage/server/bin"
shell_bin="$stage/${shell%.zip}/bin"
tools_bin="$stage/${tools%.zip}/bin"
"$server_bin/mongod" --version >/dev/null
"$shell_bin/mongosh" --version >/dev/null
"$tools_bin/mongodump" --version >/dev/null

mkdir -p "$target"
for binary in "$server_bin/"* "$shell_bin/"* "$tools_bin/"*; do
    candidate=$(mktemp "$target/.install.XXXXXX")
    if ! install -m 0755 "$binary" "$candidate" || ! mv -f -- "$candidate" "$target/${binary##*/}"; then
        rm -f -- "$candidate"
        exit 1
    fi
done
