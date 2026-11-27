#!/usr/bin/env bash
set -e

panel=$(cd ../.. && pwd)
runtime="$(dirname "$panel")/gdrive"

case "$1" in
    install)
        if [ ! -x "$runtime/bin/python" ]; then
            python3 -m venv "$runtime"
        fi
        "$runtime/bin/python" -m pip install --upgrade \
            'google-api-python-client>=2.39' google-auth-httplib2 google-auth-oauthlib httplib2
        printf '%s\n' "$2" > "$runtime/version.pl"
        echo '安装完成'
        ;;
    uninstall)
        rm -rf -- "$runtime"
        echo '卸载完成'
        ;;
    *) exit 1 ;;
esac
