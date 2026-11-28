#!/usr/bin/env bash

install_grafana() (
    local root server architecture digest source_dir file stage package
    root=$(cd ../.. && pwd) || return 1
    server=$(dirname "$root")
    case "$(uname -m)" in
        x86_64) architecture=amd64; digest=e6f06cf4ad96a4809294c2e78d3ebe6bc42a79bff36ffe35eefbe502fc19aa87 ;;
        aarch64) architecture=arm64; digest=366f33263bf92a615644b129cb1f465eb32d632e48c6157c1831ca0194385a56 ;;
        *) return 1 ;;
    esac

    source "$root/scripts/tools/verified-download.sh" || return 1
    source_dir="$server/source/grafana"
    mkdir -p "$source_dir" || return 1
    file="grafana_13.3.2_44555861735_linux_$architecture.tar.gz"
    verified_download "https://dl.grafana.com/grafana/release/13.3.2/$file" "$source_dir/$file" "$digest" || return 1
    stage=$(mktemp -d "$source_dir/install.XXXXXX") || return 1
    trap 'rm -rf -- "$stage"' EXIT
    tar -xzf "$source_dir/$file" -C "$stage" || return 1
    package=$(find "$stage" -mindepth 1 -maxdepth 1 -type d) || return 1
    [ -x "$package/bin/grafana" ] && [ -f "$package/conf/defaults.ini" ] || return 1
    mkdir -p "$server/grafana" || return 1
    cp -R "$package"/. "$server/grafana/" || return 1
    chown -R grafana:grafana "$server/grafana"
)

case "$1" in
    install) install_grafana ;;
    uninstall) exit 0 ;;
    *) exit 1 ;;
esac
