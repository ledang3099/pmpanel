#!/usr/bin/env bash
set -e

panel=$(cd ../.. && pwd)
runtime="$(dirname "$panel")/gdrive"

case "$1" in
    install|upgrade)
        if [ -f "$panel/bin/activate" ]; then
            source "$panel/bin/activate"
        fi
        mkdir -p "$runtime"
        python3 -m pip install --upgrade \
            'google-api-python-client>=2.39' google-auth-httplib2 google-auth-oauthlib httplib2
        python3 -c 'import googleapiclient.discovery, google_auth_oauthlib.flow'
        printf '%s\n' "$2" > "$runtime/version.pl"
        echo '安装完成'
        ;;
    uninstall)
        rm -rf -- "$runtime"
        echo '卸载完成'
        ;;
    *) exit 1 ;;
esac
