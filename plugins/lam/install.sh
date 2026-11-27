#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin:/opt/homebrew/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

# cd /www/server/pmpanel/plugins/lam && bash install.sh install 9.0
# cd /www/server/pmpanel && python3 plugins/lam/index.py start

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

Install_App()
{
    if [ -d "$serverPath/lam" ]; then
        cd "$rootPath" || return 1
        [ "$(python3 plugins/lam/index.py start)" = ok ]
        return $?
    fi

	mkdir -p ${serverPath}/source/lam
	
	VER=$1

	# https://github.com/LDAPAccountManager/lam/releases/download/9.0/ldap-account-manager-9.0.tar.bz2
	FDIR=ldap-account-manager-${VER}
	FILE=ldap-account-manager-${VER}.tar.bz2
	DOWNLOAD=https://github.com/LDAPAccountManager/lam/releases/download/${VER}/${FILE}
	

    archive="$serverPath/source/lam/$FILE"
    if [ "$VER" = 9.7 ]; then
        source "$rootPath/scripts/tools/verified-download.sh" || return 1
        verified_download "$DOWNLOAD" "$archive" b3535f91afa09ba49f59d8a7fdfbb0a4f5aae2b9ed17aac7b8bfae36e834d9e0 || return 1
    elif [ ! -f "$archive" ]; then
        curl -fsSL --retry 2 "$DOWNLOAD" -o "$archive.part" && mv -- "$archive.part" "$archive" || return 1
    fi
    staging=$(mktemp -d "$serverPath/source/lam/install.XXXXXX") || return 1
    trap 'rm -rf -- "$staging"' EXIT
    tar -xjf "$archive" -C "$staging" || return 1

	mkdir -p "$serverPath/lam" && cp -R "$staging/$FDIR" "$serverPath/lam/lam" || return 1
	printf "%s\n" "$VER" > "$serverPath/lam/version.pl"
	# rm -rf $serverPath/source/lam/$FDIR
	
	cd "$rootPath" || return 1
    [ "$(python3 plugins/lam/index.py start)" = ok ] || return 1
	echo '安装完成'
		
}

Uninstall_App()
{
	cd ${rootPath} && python3 ${rootPath}/plugins/lam/index.py stop
	
	rm -rf ${serverPath}/lam
	echo '卸载完成'
}

action=$1
if [ "${1}" = 'install' ];then
	Install_App $2
else
	Uninstall_App $2
fi
