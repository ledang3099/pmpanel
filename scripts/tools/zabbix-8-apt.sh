# Used by both pmpanel Zabbix plugins so they select the same package series.
install_zabbix_8_apt() (
    . /etc/os-release
    case "$ID:$VERSION_ID" in
        debian:12|debian:13|ubuntu:22.04|ubuntu:24.04) ;;
        *) echo "Zabbix 8.0 has no configured APT source for $ID $VERSION_ID" >&2; return 1 ;;
    esac

    deb=$(mktemp --suffix=.deb) || return 1
    trap 'rm -f -- "$deb"' EXIT
    base="https://repo.zabbix.com/zabbix/8.0/release/$ID/pool/main/z/zabbix-release"
    curl --proto '=https' --proto-redir '=https' -fsSL --retry 2 \
        "$base/zabbix-release_latest+${ID}${VERSION_ID}_all.deb" -o "$deb" || return 1
    installed=$(dpkg-query -W -f='${Version}' zabbix-release 2>/dev/null || true)
    target=$(dpkg-deb --field "$deb" Version) || return 1
    if [ "$installed" != "$target" ]; then
        dpkg -i "$deb" || return 1
    fi
    apt-get update || return 1
    for package in "$@"; do
        candidate=$(LC_ALL=C apt-cache policy "$package" | awk '/Candidate:/ {print $2}')
        # Debian package versions may carry an epoch.
        upstream=${candidate#*:}
        case "$upstream" in
            8.0.*) ;;
            *) echo "No Zabbix 8.0 candidate for $package" >&2; return 1 ;;
        esac
    done
    apt-get install -y -- "$@"
)
