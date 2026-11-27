#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

# cd /www/server/pmpanel/plugins/php-apt && bash install.sh install 56

if id www &> /dev/null ;then 
    echo "www uid is `id -u www`"
    echo "www shell is `grep "^www:" /etc/passwd |cut -d':' -f7 `"
else
    groupadd www
	useradd -g www -s /sbin/nologin www
	# useradd -g www -s /bin/bash www
fi

_os=`uname`
if [ ${_os} = "Darwin" ]; then
    OSNAME='macos'
elif grep -Eqi "Debian" /etc/issue || grep -Eq "Debian" /etc/*-release; then
    OSNAME='debian'
elif grep -Eqi "Ubuntu" /etc/issue || grep -Eq "Ubuntu" /etc/*-release; then
    OSNAME='ubuntu'
else
    OSNAME='unknow'
fi

action=$1
type=$2
apt_ver=${type:0:1}.${type:1:2}

if [ "${2}" = "" ];then
	echo '缺少安装脚本...'
	exit 0
fi 

if [ ! -d $curPath/versions/$2 ];then
	echo '缺少安装脚本2...'
	exit 0
fi


if [ "$OSNAME" = "ubuntu" ];then
	find_source=`ls /etc/apt/sources.list.d | grep ondrej-ubuntu-php`
	if [ "$find_source" = "" ];then
		echo "y" | LC_ALL=C.UTF-8 add-apt-repository ppa:ondrej/php && apt update -y
	fi
fi
# apt install $(grep-aptavail -S PHP-defaults -s Package -n)


if [ "$action" != uninstall ] && [ "$OSNAME" = debian ] && [ ! -f /etc/apt/sources.list.d/php.list ]; then
    apt-get install -y lsb-release ca-certificates curl || exit 1
    keyring=$(mktemp --suffix=.deb) || exit 1
    curl --proto '=https' --proto-redir '=https' -fsSL https://packages.sury.org/debsuryorg-archive-keyring.deb -o "$keyring" &&
        dpkg -i "$keyring"
    status=$?
    unlink "$keyring"
    [ "$status" = 0 ] || exit "$status"
    codename=$(lsb_release -sc) || exit 1
    printf 'deb [signed-by=/usr/share/keyrings/debsuryorg-archive-keyring.gpg] https://packages.sury.org/php/ %s main\n' "$codename" \
        > /etc/apt/sources.list.d/php.list || exit 1
    apt-get update || exit 1
fi

if [ "${action}" = "uninstall" ] && [ -d ${serverPath}/php-apt/${type} ];then
	#初始化 
	cd ${rootPath} && python3 ${rootPath}/plugins/php-apt/index.py stop ${type}
	cd ${rootPath} && python3 ${rootPath}/plugins/php-apt/index.py initd_uninstall ${type}

	if [ -f /lib/systemd/system/php${apt_ver}-fpm.service ];then
		rm -rf /lib/systemd/system/php${apt_ver}-fpm.service
	fi

	if [ -f /lib/systemd/system/system/php${apt_ver}-fpm.service ];then
		rm -rf /lib/systemd/system/php${apt_ver}-fpm.service
	fi


	rm -rf /etc/php/${apt_ver}/fpm/php-fpm.conf

	systemctl daemon-reload
fi

if [ "${action}" = "upgrade" ];then
	apt-get update || exit $?
	cd "${curPath}" && bash -x "$curPath/versions/$2/install.sh" upgrade || exit $?
	if command -v systemctl >/dev/null; then systemctl restart "php${apt_ver}-fpm"; fi
	exit $?
fi

cd "$curPath" && bash -x "$curPath/versions/$type/install.sh" "$action" || exit 1

if [ "${action}" = "install" ] && [ -d ${serverPath}/php-apt/${type} ];then
	apt update -y
	
	#初始化 
	cd ${rootPath} && python3 ${rootPath}/plugins/php-apt/index.py start ${type}
	cd ${rootPath} && python3 ${rootPath}/plugins/php-apt/index.py restart ${type}
	cd ${rootPath} && python3 ${rootPath}/plugins/php-apt/index.py initd_install ${type}

	# 安装通用扩展
	echo "install PHP-APT[${type}] extend start"
	cd ${rootPath}/plugins/php-apt/versions && bash common.sh ${apt_ver} install curl
	cd ${rootPath}/plugins/php-apt/versions && bash common.sh ${apt_ver} install gd
	cd ${rootPath}/plugins/php-apt/versions && bash common.sh ${apt_ver} install iconv
	cd ${rootPath}/plugins/php-apt/versions && bash common.sh ${apt_ver} install exif
	cd ${rootPath}/plugins/php-apt/versions && bash common.sh ${apt_ver} install intl
	cd ${rootPath}/plugins/php-apt/versions && bash common.sh ${apt_ver} install xml
	cd ${rootPath}/plugins/php-apt/versions && bash common.sh ${apt_ver} install mcrypt
	cd ${rootPath}/plugins/php-apt/versions && bash common.sh ${apt_ver} install bcmath
	cd ${rootPath}/plugins/php-apt/versions && bash common.sh ${apt_ver} install mysqlnd
	cd ${rootPath}/plugins/php-apt/versions && bash common.sh ${apt_ver} install mysql
	cd ${rootPath}/plugins/php-apt/versions && bash common.sh ${apt_ver} install gettext
	cd ${rootPath}/plugins/php-apt/versions && bash common.sh ${apt_ver} install redis
	cd ${rootPath}/plugins/php-apt/versions && bash common.sh ${apt_ver} install memcached
	cd ${rootPath}/plugins/php-apt/versions && bash common.sh ${apt_ver} install mbstring
	cd ${rootPath}/plugins/php-apt/versions && bash common.sh ${apt_ver} install zip
	cd ${rootPath}/plugins/php-apt/versions && bash common.sh ${apt_ver} install mongodb
	cd ${rootPath}/plugins/php-apt/versions && bash common.sh ${apt_ver} install opcache
	echo "install PHP-APT[${type}] extend end"

	if [ ! -f /usr/local/bin/composer ];then
		cd /tmp
		curl -sS https://getcomposer.org/installer | /usr/bin/php${apt_ver}
		mv composer.phar /usr/local/bin/composer
	fi

	systemctl restart php${apt_ver}-fpm
fi


