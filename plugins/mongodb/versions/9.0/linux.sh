#!/usr/bin/env bash

install_mongodb_linux() (
    panel=$(cd ../.. && pwd) || return 1
    server=$(dirname "$panel")
    . /etc/os-release

    arch=$(uname -m)
    case "$ID:$VERSION_ID" in
        opensuse-leap:15.*) platform=suse15 ;;
        opensuse-leap:16.*) platform=suse16 ;;
        debian:12|debian:13) platform="debian$VERSION_ID" ;;
        ubuntu:22.04|ubuntu:24.04|ubuntu:26.04) platform="ubuntu${VERSION_ID/.}" ;;
        rocky:8.[89]|rocky:8.10|almalinux:8.[89]|almalinux:8.10|rhel:8.[89]|rhel:8.10) platform=rhel88 ;;
        rocky:9.[3-9]|rocky:9.10|almalinux:9.[3-9]|almalinux:9.10|rhel:9.[3-9]|rhel:9.10|centos:9) platform=rhel93 ;;
        rocky:10|rocky:10.*|almalinux:10|almalinux:10.*|rhel:10|rhel:10.*|centos:10) platform=rhel10 ;;
        *)
            echo "MongoDB 9.0 has no configured archive for $ID $VERSION_ID" >&2
            return 1
            ;;
    esac

    manifest="$panel/plugins/mongodb/versions/9.0/linux-archives.tsv"
    pinned=$(awk -v distro="$platform" -v machine="$arch" '$1 == distro && $2 == machine {print $3, $4}' "$manifest")
    if [ -z "$pinned" ]; then
        echo "MongoDB 9.0 has no configured archive for $platform $arch" >&2
        return 1
    fi
    if [ "${1:-}" = --check ]; then
        return 0
    fi
    read -r server_sha tools_sha <<< "$pinned"

    if [[ "$platform" == suse* ]]; then
        dependencies=()
        command -v tar >/dev/null || dependencies+=(tar)
        command -v gzip >/dev/null || dependencies+=(gzip)
        rpm -q --whatprovides 'libgssapi_krb5.so.2()(64bit)' >/dev/null || dependencies+=(krb5)
        if [ "$platform" = suse15 ] && ! rpm -q --whatprovides 'libcrypto.so.1.1()(64bit)' >/dev/null; then
            dependencies+=(libopenssl1_1)
        fi
        if [ "${#dependencies[@]}" -ne 0 ]; then
            zypper --non-interactive install "${dependencies[@]}" || return 1
        fi
    fi

    case "$arch" in
        x86_64)
            shell_arch=x64
            shell_sha=2f9082b19c3daa4469865cb2d13ba64eea9f5b447371ecd25f175bb99320d575
            ;;
        aarch64)
            shell_arch=arm64
            shell_sha=47ce1c6b6aa22c58118416f6423237093bf67886b56998fae4dd8430b369b667
            ;;
        *) return 1 ;;
    esac
    tools_arch=$arch
    if [[ "$platform" == ubuntu* && "$arch" == aarch64 ]]; then
        tools_arch=arm64
    fi

    target="$server/mongodb/bin"
    if [ -x "$target/mongod" ] && ! "$target/mongod" --version | grep -q '^db version v9\.0\.'; then
        echo 'MongoDB 9.0 requires a supported major-version migration before replacing the existing server.' >&2
        return 1
    fi

    source "$panel/scripts/tools/verified-download.sh" || return 1
    sources="$server/source/mongodb"
    mkdir -p "$sources" || return 1
    server_platform=$platform
    if [ "$platform" = rhel88 ]; then
        server_platform=rhel8
    fi
    archive="mongodb-linux-${arch}-${server_platform}-9.0.8.tgz"
    shell="mongosh-2.14.3-linux-${shell_arch}.tgz"
    tools="mongodb-database-tools-${platform}-${tools_arch}-100.20.1.tgz"
    verified_download "https://fastdl.mongodb.org/linux/$archive" "$sources/$archive" "$server_sha" || return 1
    verified_download "https://downloads.mongodb.com/compass/$shell" "$sources/$shell" \
        "$shell_sha" || return 1
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

install_mongodb_linux "$@"
