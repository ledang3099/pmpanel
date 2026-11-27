#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

VERSION=0.0.19

# bash install.sh install 0.0.19
## cd /www/server/pmpanel/plugins/imail && bash install.sh install 0.0.19

Install_App()
(
    os=$(uname -s)
    machine=$(uname -m)
    case "$os:$machine" in
        Linux:x86_64) platform=linux_amd64; digest=971d14bc70ed6ab53a74c9588f01a4f8378aafa5ff447213214ca6da6b9e05c2 ;;
        Linux:aarch64) platform=linux_arm64; digest=0c37a53cbc0787101eba48a4e62bc2f13ee265b7a0ef3f4ffbcd52856edf1b8b ;;
        Linux:i386|Linux:i686) platform=linux_386; digest=ef33faf2f46472efdd9dfd61cb9dbfa31710121401e2ae7d4873a796745543ec ;;
        Linux:armv7l|Linux:armv6l) platform=linux_arm; digest=871c8cba662151cef546050284d30db8572a3e7f14d5b1ac48519a0a4e177129 ;;
        Darwin:x86_64) platform=darwin_amd64; digest=34c0d573c3360305d95519d808ba7e0f1ef282782d5bba08d1da46af01a55548 ;;
        *)
            printf 'iMail %s has no package for %s %s\n' "$VERSION" "$os" "$machine" >&2
            return 1
            ;;
    esac

    if [ -f "$rootPath/bin/activate" ]; then
        source "$rootPath/bin/activate" || return 1
    fi

    source "$rootPath/scripts/tools/verified-download.sh" || return 1
    cache="$serverPath/source/imail"
    target="$serverPath/imail"
    mkdir -p "$cache" || return 1
    archive="imail_${VERSION}_$platform.tar.gz"
    verified_download "https://github.com/midoks/imail/releases/download/$VERSION/$archive" "$cache/$archive" "$digest" || return 1
    staging=$(mktemp -d "$cache/install.XXXXXX") || return 1
    trap 'rm -rf -- "$staging"' EXIT
    tar -xzf "$cache/$archive" -C "$staging" || return 1
    test -x "$staging/imail" || return 1
    mkdir -p "$target" || return 1
    cp -Rn "$staging/." "$target/" || return 1
    mv -f -- "$staging/imail" "$target/imail" || return 1

    cd "$rootPath" || return 1
    result=$(python3 plugins/imail/index.py start) || return 1
    if [ "$result" != ok ]; then
        printf '%s\n' "$result" >&2
        return 1
    fi
    if [ "$os" = Linux ]; then
        systemctl restart imail && systemctl enable imail || return 1
    fi
    printf '%s\n' "$VERSION" > "$target/version.pl"
)

Uninstall_App()
{
	cd ${rootPath} && python3 ${rootPath}/plugins/imail/index.py initd_uninstall
	cd ${rootPath} && python3 ${rootPath}/plugins/imail/index.py stop
	rm -rf $serverPath/imail
	echo "install fail"
}

action=$1
if [ "${1}" = 'install' ];then
	Install_App
else
	Uninstall_App
fi
