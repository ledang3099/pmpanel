#!/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

# cd /www/server/pmpanel/plugins/pureftp && bash install.sh install 1.0.49

if [ -f ${rootPath}/bin/activate ];then
	. ${rootPath}/bin/activate
fi

sysName=`uname`
echo "use system: ${sysName}"

if [ ${sysName} = "Darwin" ]; then
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




Install_pureftp()
{
	if id ftp &> /dev/null ;then 
	    echo "ftp UID is `id -u ftp`"
	    echo "ftp Shell is `grep "^ftp:" /etc/passwd |cut -d':' -f7 `"
	else
	    groupadd ftp
		useradd -g ftp -s /sbin/nologin ftp
	fi

    VERSION=$1
    if [ "$VERSION" != 1.0.54 ]; then
        echo "Unsupported Pure-FTPd release: $VERSION" >&2
        return 1
    fi
    source "$rootPath/scripts/tools/verified-download.sh" || return 1
    source_dir="$serverPath/source/pureftp"
    mkdir -p "$source_dir" || return 1
    archive="$source_dir/pure-ftpd-${VERSION}.tar.gz"
    verified_download "https://download.pureftpd.org/pub/pure-ftpd/releases/pure-ftpd-${VERSION}.tar.gz" \
        "$archive" dc9140420ec44f7829579591ff378aa6396b4604b9c6aeae847368e0f35bd7b2 || return 1
    build_root=$(mktemp -d "$source_dir/build.XXXXXX") || return 1
    trap 'rm -rf -- "$build_root"' EXIT
    tar -xzf "$archive" -C "$build_root" || return 1
    cd "$build_root/pure-ftpd-${VERSION}" || return 1
    CFLAGS=-O2 ./configure --prefix="$serverPath/pureftp" \
		--with-puredb \
		--with-quotas \
		--with-cookie \
		--with-virtualhosts \
		--with-diraliases \
		--with-sysquotas \
		--with-ratios \
		--with-altlog \
		--with-paranoidmsg \
		--with-shadow \
		--with-welcomemsg \
		--with-throttling \
		--with-uploadscript \
		--with-language=english \
		--with-ftpwho \
		--with-tls || return 1
    make && make install || return 1
    cd "$rootPath" || return 1
    if [ "$action" = upgrade ]; then
        [ "$(python3 plugins/pureftp/index.py restart)" = ok ] || return 1
    else
        [ "$(python3 plugins/pureftp/index.py start)" = ok ] || return 1
        python3 plugins/pureftp/index.py initd_install || return 1
    fi
    printf '%s\n' "$VERSION" > "$serverPath/pureftp/version.pl"
}

Uninstall_pureftp()
{
	if [ -f /usr/lib/systemd/system/pureftp.service ];then
		systemctl stop pureftp
		systemctl disable pureftp
		rm -rf /usr/lib/systemd/system/pureftp.service
		systemctl daemon-reload
	fi

	if [ -f $serverPath/pureftp/initd/pureftp ];then
		$serverPath/pureftp/initd/pureftp stop
	fi

	rm -rf ${serverPath}/pureftp
	userdel ftp
	groupdel ftp
	echo '卸载完成'
}

action=$1
case "$action" in
    install) Install_pureftp "$2" ;;
    upgrade) Install_pureftp 1.0.54 ;;
    uninstall) Uninstall_pureftp ;;
    *) exit 1 ;;
esac
