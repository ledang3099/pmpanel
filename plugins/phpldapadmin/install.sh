#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin:/opt/homebrew/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

# cd /www/server/pmpanel/plugins/phpldapadmin && bash install.sh install 1.2.6.7
# cd /www/server/pmpanel && python3 plugins/phpldapadmin/index.py start

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

Install_Modern()
{
    runtime="$serverPath/phpldapadmin"
    if [ -d "$runtime" ]; then
        if [ -f "$runtime/phpldapadmin-v2/artisan" ]; then
            cd "$rootPath" || return 1
            [ "$(python3 plugins/phpldapadmin/index.py start)" = ok ] || return 1
            printf '2.3.13\n' > "$runtime/version.pl"
            return
        fi
        echo '检测到 phpLDAPadmin 1.x。请先备份配置和目录数据，再安装 2.x。' >&2
        return 1
    fi

    composer=$(command -v composer) || { echo '请先安装 Composer。' >&2; return 1; }
    command -v npm >/dev/null || { echo '请先安装 Node.js 和 npm。' >&2; return 1; }
    php=
    for candidate in php "$serverPath/php/86/bin/php" "$serverPath/php/85/bin/php" "$serverPath/php/84/bin/php"; do
        if "$candidate" -r 'exit(PHP_VERSION_ID >= 80400 && extension_loaded("ldap") && extension_loaded("mbstring") && extension_loaded("xml") ? 0 : 1);' 2>/dev/null; then
            php=$candidate
            break
        fi
    done
    if [ -z "$php" ]; then
        echo '请先安装 PHP 8.4 或更高版本及 LDAP、mbstring、XML 扩展。' >&2
        return 1
    fi

    sources="$serverPath/source/phpldapadmin"
    mkdir -p "$sources" || return 1
    source "$rootPath/scripts/tools/verified-download.sh" || return 1
    archive="$sources/2.3.13.tar.gz"
    verified_download https://codeload.github.com/leenooks/phpLDAPadmin/tar.gz/refs/tags/2.3.13 "$archive" \
        fd359c6305e49b632f11d6210b3f2328d6cb953d29a08092b250aee86adc1dde || return 1
    staging=$(mktemp -d "$sources/install.XXXXXX") || return 1
    trap 'rm -rf -- "$staging"' EXIT
    tar -xzf "$archive" -C "$staging" || return 1
    cd "$staging/phpLDAPadmin-2.3.13" || return 1
    COMPOSER_ALLOW_SUPERUSER=1 "$php" "$composer" install --no-dev --no-interaction --prefer-dist || return 1
    npm ci --no-audit --no-fund && npm run production || return 1
    rm -rf -- node_modules
    cp .env.example .env && chmod 0640 .env || return 1
    "$php" artisan key:generate --force || return 1
    if [ "$sysName" = Linux ]; then
        chown root:www .env && chown -R www:www storage bootstrap/cache || return 1
    fi
    mkdir -p "$runtime" || return 1
    mv -- "$staging/phpLDAPadmin-2.3.13" "$runtime/phpldapadmin-v2" || return 1
    cd "$rootPath" || return 1
    [ "$(python3 plugins/phpldapadmin/index.py start)" = ok ] || return 1
    printf '2.3.13\n' > "$runtime/version.pl"
}

Install_App()
{
	if [ -d $serverPath/phpldapadmin ];then
		exit 0
	fi

	mkdir -p ${serverPath}/phpldapadmin
	mkdir -p ${serverPath}/source/phpldapadmin
	echo "${1}" > ${serverPath}/phpldapadmin/version.pl
	
	VER=$1

	# https://github.com/leenooks/phpLDAPadmin/archive/refs/tags/1.2.6.7.tar.gz
	FDIR=phpLDAPadmin-${VER}
	FILE=${VER}.tar.gz
	DOWNLOAD=https://github.com/leenooks/phpLDAPadmin/archive/refs/tags/${FILE}
	

	if [ ! -f $serverPath/source/phpmyadmin/$FILE ];then
		wget --no-check-certificate -O $serverPath/source/phpldapadmin/$FILE $DOWNLOAD
	fi

	if [ ! -d $serverPath/source/phpldapadmin/$FDIR ];then
		cd $serverPath/source/phpldapadmin  && tar zxvf $FILE
	fi

	cp -r $serverPath/source/phpldapadmin/$FDIR $serverPath/phpldapadmin/
	cd $serverPath/phpldapadmin/ && mv $FDIR phpldapadmin
	# rm -rf $serverPath/source/phpldapadmin/$FDIR
	
	cd ${rootPath} && python3 ${rootPath}/plugins/phpldapadmin/index.py start
	echo '安装完成'
		
}

Uninstall_App()
{
	cd ${rootPath} && python3 ${rootPath}/plugins/phpldapadmin/index.py stop
	
	rm -rf ${serverPath}/phpldapadmin
	echo '卸载完成'
}

action=$1
case "$action:$2" in
    install:2.3.13) Install_Modern ;;
    install:1.2.6.7) Install_App "$2" ;;
    uninstall:*) Uninstall_App ;;
    *) exit 1 ;;
esac
