#!/usr/bin/env bash

install_mongodb_debian() (
    panel=$(cd ../.. && pwd) || return 1
    server=$(dirname "$panel")
    . /etc/os-release

    if [ "$ID" != debian ] || [ "$(uname -m)" != x86_64 ]; then
        echo 'MongoDB 9.0 Debian builds require Debian x86_64' >&2
        return 1
    fi

    case "$VERSION_ID" in
        12)
            server_sha=a78b3e96379fb447c6045af84b1e6853540048fb1878db20f410720ccc0caa27
            tools_sha=8f25dcd1d769560fae1b5e724dc0c5eba54f2410dd293a9bab62be055507e521
            ;;
        13)
            server_sha=667faae2f310eabb79846507a15bcb8a2888f6a1324bd77eea8b85ddfe7692a5
            tools_sha=5a74b5bebfe1421f338a25ecd80f8e6173f6d47241ea243564b0a1c9f2278b3b
            ;;
        *) return 1 ;;
    esac

    target="$server/mongodb/bin"
    if [ -x "$target/mongod" ] && ! "$target/mongod" --version | grep -q '^db version v9\.0\.'; then
        echo 'MongoDB 9.0 requires a supported major-version migration before replacing the existing server.' >&2
        return 1
    fi

    source "$panel/scripts/tools/verified-download.sh" || return 1
    sources="$server/source/mongodb"
    mkdir -p "$sources" || return 1
    archive="mongodb-linux-x86_64-debian${VERSION_ID}-9.0.8.tgz"
    shell="mongosh-2.14.3-linux-x64.tgz"
    tools="mongodb-database-tools-debian${VERSION_ID}-x86_64-100.20.1.tgz"
    verified_download "https://fastdl.mongodb.org/linux/$archive" "$sources/$archive" "$server_sha" || return 1
    verified_download "https://downloads.mongodb.com/compass/$shell" "$sources/$shell" \
        2f9082b19c3daa4469865cb2d13ba64eea9f5b447371ecd25f175bb99320d575 || return 1
    verified_download "https://fastdl.mongodb.org/tools/db/$tools" "$sources/$tools" "$tools_sha" || return 1

    stage=$(mktemp -d "$sources/install.XXXXXX") || return 1
    trap 'rm -rf -- "$stage"' EXIT
    for package in "$archive" "$shell" "$tools"; do
        tar -xzf "$sources/$package" -C "$stage" || return 1
    done
    "$stage/${archive%.tgz}/bin/mongod" --version >/dev/null || return 1
    "$stage/${shell%.tgz}/bin/mongosh" --version >/dev/null || return 1
    "$stage/${tools%.tgz}/bin/mongodump" --version >/dev/null || return 1
    mkdir -p "$target" || return 1
    for package in "$archive" "$shell" "$tools"; do
        for binary in "$stage/${package%.tgz}/bin/"*; do
            candidate=$(mktemp "$target/.install.XXXXXX") || return 1
            if ! install -m 0755 "$binary" "$candidate" || ! mv -f -- "$candidate" "$target/${binary##*/}"; then
                rm -f -- "$candidate"
                return 1
            fi
        done
    done
)

install_mongodb_debian
