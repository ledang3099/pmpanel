#!/usr/bin/env bash

install_loki() (
    panel=$(cd ../.. && pwd) || return 1
    server=$(dirname "$panel")
    install_dir="$server/loki"
    case "$(uname -m)" in
        x86_64)
            architecture=amd64
            loki_sha=200e74f7e631969bd0f2a066a2e1d33cdea9b3c0801aaaa7d78947c4ac29bddb
            alloy_sha=62d177feb18c9b6ffd636c8273aa82a6afc75a507d096ff951749df23c3176f9
            ;;
        aarch64)
            architecture=arm64
            loki_sha=13c3f926c8bb020b225b2802fa8e2d4e969186d6d2a8fd15e26f323a71beff83
            alloy_sha=cc2c4d7bc25d3ef7df8c95395759879ba4eb0d016db068c07dcb7aa88f436ad3
            ;;
        *) return 1 ;;
    esac
    source "$panel/scripts/tools/verified-download.sh" || return 1
    sources="$server/source/loki"
    mkdir -p "$sources" || return 1
    loki_file="loki-linux-$architecture.zip"
    alloy_file="alloy-linux-$architecture.zip"
    verified_download "https://github.com/grafana/loki/releases/download/v3.7.10/$loki_file" \
        "$sources/3.7.10-$loki_file" "$loki_sha" || return 1
    verified_download "https://github.com/grafana/alloy/releases/download/v1.22.0/$alloy_file" \
        "$sources/1.22.0-$alloy_file" "$alloy_sha" || return 1
    stage=$(mktemp -d "$sources/build.XXXXXX") || return 1
    trap 'rm -rf -- "$stage"' EXIT
    unzip -q "$sources/3.7.10-$loki_file" -d "$stage" || return 1
    unzip -q "$sources/1.22.0-$alloy_file" -d "$stage" || return 1

    chmod 0755 "$stage/loki-linux-$architecture" "$stage/alloy-linux-$architecture" || return 1

    loki_config="$install_dir/conf/loki-config.yaml"
    if [ ! -f "$loki_config" ]; then
        loki_config="$stage/loki-config.yaml"
        sed "s|{\$APP_PATH}|$install_dir|g" "$panel/plugins/loki/conf/loki-config.yaml" > "$loki_config"
    fi
    "$stage/loki-linux-$architecture" -verify-config=true -config.file="$loki_config" || return 1

    alloy_config="$install_dir/conf/collector.alloy"
    if [ ! -f "$alloy_config" ]; then
        promtail_config="$install_dir/conf/promtail-config.yaml"
        if [ ! -f "$promtail_config" ]; then
            promtail_config="$stage/promtail-config.yaml"
            sed -e "s|{\$APP_PATH}|$install_dir|g" -e "s|{\$LOG_PATH}|$install_dir/logs|g" \
                "$panel/plugins/loki/conf/promtail-config.yaml" > "$promtail_config"
        fi
        "$stage/alloy-linux-$architecture" convert --source-format=promtail \
            --output="$stage/collector.alloy" "$promtail_config" || return 1
        alloy_config="$stage/collector.alloy"
    fi
    "$stage/alloy-linux-$architecture" validate "$alloy_config" || return 1
    mkdir -p "$install_dir/bin" "$install_dir/conf" || return 1
    install -m 0755 "$stage/loki-linux-$architecture" "$install_dir/bin/loki" || return 1
    install -m 0755 "$stage/alloy-linux-$architecture" "$install_dir/bin/alloy" || return 1
    if [ "$alloy_config" = "$stage/collector.alloy" ]; then
        install -m 0600 "$alloy_config" "$install_dir/conf/collector.alloy" || return 1
    fi
)

case "$1" in
    install) install_loki ;;
    uninstall) exit 0 ;;
    *) exit 1 ;;
esac
