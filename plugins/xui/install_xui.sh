#!/usr/bin/env bash
set -e

panel=$(cd "$(dirname "$0")/../.." && pwd)
server=$(dirname "$panel")
source "$panel/scripts/tools/verified-download.sh"
release=0.3.4.4

if [ "$(uname -s)" != Linux ]; then
    echo 'x-ui 需要 Linux 和 systemd。' >&2
    exit 1
fi
case "$(uname -m)" in
    x86_64) architecture=amd64; digest=a210908eedf717627dcc8d409f9fa3783748ca080acae131815a0c55d3883bd9 ;;
    aarch64|arm64) architecture=arm64; digest=51b54a0199d037f100f60a4fe2ceca4634182e17f701fb76ba11ca13a6f82af0 ;;
    s390x) architecture=s390x; digest=7cf5220140fe9f3d356b1353acba5d8f9cf13128f6b4c2d438e4aa9ea6c275e7 ;;
    *) echo '不支持当前 CPU 架构。' >&2; exit 1 ;;
esac

sources="$server/source/xui"
mkdir -p "$sources"
file="x-ui-linux-$architecture.tar.gz"
archive="$sources/$release-$file"
verified_download "https://github.com/FranzKafkaYu/x-ui/releases/download/$release/$file" "$archive" "$digest"
stage=$(mktemp -d /usr/local/x-ui-install.XXXXXX)
unit=/etc/systemd/system/x-ui.service
cli=/usr/bin/x-ui
install_started=0
was_active=0
cleanup() {
    status=$?
    if [ "$status" != 0 ] && [ "$install_started" = 1 ]; then
        set +e
        systemctl stop x-ui
        rm -rf -- /usr/local/x-ui
        if [ -d "$stage/prior" ]; then mv "$stage/prior" /usr/local/x-ui; fi
        if [ -e "$stage/prior.service" ]; then mv "$stage/prior.service" "$unit"; else rm -f -- "$unit"; fi
        if [ -e "$stage/prior.cli" ]; then mv "$stage/prior.cli" "$cli"; else rm -f -- "$cli"; fi
        systemctl daemon-reload
        if [ "$was_active" = 1 ]; then systemctl start x-ui; fi
    fi
    rm -rf -- "$stage"
}
trap cleanup EXIT
tar -xzf "$archive" -C "$stage"
chmod 0755 "$stage/x-ui/"{x-ui,x-ui.sh,"bin/xray-linux-$architecture"}

if [ -e "$unit" ]; then cp -a "$unit" "$stage/prior.service"; fi
if [ -e "$cli" ]; then cp -a "$cli" "$stage/prior.cli"; fi
if systemctl is-active --quiet x-ui; then
    was_active=1
    systemctl stop x-ui
fi
if [ -e /usr/local/x-ui ]; then
    mv /usr/local/x-ui "$stage/prior"
fi
install_started=1
mv "$stage/x-ui" /usr/local/x-ui
install -m 0644 /usr/local/x-ui/x-ui.service "$unit"
install -m 0755 /usr/local/x-ui/x-ui.sh "$cli"

if [ ! -e /etc/x-ui/x-ui.db ]; then
    username=$(openssl rand -hex 8)
    password=$(openssl rand -hex 16)
    port=$(python3 -c 'import socket; s = socket.socket(); s.bind(("", 0)); print(s.getsockname()[1])')
    /usr/local/x-ui/x-ui setting -username "$username" -password "$password" > /dev/null
    /usr/local/x-ui/x-ui setting -port "$port" > /dev/null
fi

systemctl daemon-reload
systemctl start x-ui
systemctl is-active --quiet x-ui
systemctl enable x-ui
