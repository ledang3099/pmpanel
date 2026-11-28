#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin:/opt/homebrew/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

# cd /www/server/pmpanel/plugins/phpmyadmin && bash install.sh install 4.4.15
# cd /www/server/pmpanel/plugins/phpmyadmin && bash install.sh install 5.2.3
# cd /www/server/pmpanel && python3 plugins/phpmyadmin/index.py start

if [ -f ${rootPath}/bin/activate ];then
	. ${rootPath}/bin/activate
fi

if [ "$sys_os" = "Darwin" ];then
	BAK='_bak'
else
	BAK=''
fi

sysName=`uname`
echo "use system: ${sysName}"

if [ "${sysName}" = "Darwin" ]; then
	OSNAME='macos'
elif grep -Eqi "CentOS" /etc/issue || grep -Eq "CentOS" /etc/*-release; then
	OSNAME='centos'
elif grep -Eqi "Fedora" /etc/issue || grep -Eq "Fedora" /etc/*-release; then
	OSNAME='fedora'
elif grep -Eqi "Debian" /etc/issue || grep -Eq "Debian" /etc/*-release; then
	OSNAME='debian'
elif grep -Eqi "Ubuntu" /etc/issue || grep -Eq "Ubuntu" /etc/*-release; then
	OSNAME='ubuntu'
elif grep -Eqi "Raspbian" /etc/issue || grep -Eq "Raspbian" /etc/*-release; then
	OSNAME='raspbian'
else
	OSNAME='unknow'
fi

Install_phpmyadmin()
{
    if [ -d "$serverPath/phpmyadmin" ]; then
        if [ "$(cat "$serverPath/phpmyadmin/version.pl" 2>/dev/null)" = "$1" ]; then
            cd "$rootPath" || return 1
            result=$(python3 plugins/phpmyadmin/index.py start) || return 1
            if [ "$result" != ok ]; then printf '%s\n' "$result" >&2; return 1; fi
            return 0
        fi
        echo '检测到已安装的 phpMyAdmin。请备份现有配置之后再安装所选版本。' >&2
        return 1
    fi

    version=$1
    case "$version" in
        4.4.15|4.9.11|5.2.3) ;;
        *) return 1 ;;
    esac
    sources="$serverPath/source/phpmyadmin"
    mkdir -p "$sources" || return 1
    dir="phpMyAdmin-$version-all-languages"
    archive="$sources/$dir.tar.gz"
    url="https://files.phpmyadmin.net/phpMyAdmin/$version/$dir.tar.gz"
    if [ "$version" = 5.2.3 ]; then
        source "$rootPath/scripts/tools/verified-download.sh" || return 1
        verified_download "$url" "$archive" 12ba1c425fa4071abbd4e7668c9ebdeac0b0755a467a6d6d5026122bb47c102b || return 1
    elif [ ! -s "$archive" ]; then
        curl -fsSL "$url" -o "$archive.part" && mv -f -- "$archive.part" "$archive" || return 1
    fi
    stage=$(mktemp -d "$sources/install.XXXXXX") || return 1
    trap 'rm -rf -- "$stage"' EXIT
    tar -xzf "$archive" -C "$stage" || return 1
    test -f "$stage/$dir/index.php" || return 1
    mkdir -p "$serverPath/phpmyadmin" || return 1
    mv -- "$stage/$dir" "$serverPath/phpmyadmin/phpmyadmin" || return 1
    printf '%s\n' "$version" > "$serverPath/phpmyadmin/version.pl" || return 1
    cd "$rootPath" || return 1
    result=$(python3 plugins/phpmyadmin/index.py start) || return 1
    if [ "$result" != ok ]; then printf '%s\n' "$result" >&2; return 1; fi
    echo '安装完成'

}

Uninstall_phpmyadmin()
{
	cd ${rootPath} && python3 ${rootPath}/plugins/phpmyadmin/index.py stop
	
	rm -rf ${serverPath}/phpmyadmin
	echo '卸载完成'
}

action=$1
case "$action" in
    install) Install_phpmyadmin "$2" ;;
    uninstall) Uninstall_phpmyadmin ;;
    *) exit 1 ;;
esac
