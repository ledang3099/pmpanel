#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin:/opt/homebrew/bin
export PATH

# cd /Users/dev/Desktop/pmdev/server/pmpanel/plugins/openresty && bash install.sh upgrade 1.31

# cd /www/server/pmpanel/plugins/openresty && bash install.sh install 1.21.4
# cd /www/server/pmpanel/plugins/openresty && bash install.sh upgrade 1.31
# cd /www/server/pmpanel && . ./bin/activate && python3 plugins/openresty/index.py upgrade_check 1.31

# curl -I -H "Accept-Encoding: br" http://localhost
# curl -I -H "Accept-Encoding: zstd" http://localhost
# curl --http3 -v https://www.xxx.com

# apt install ncat -y
# nc -u -v www.xx.com 443

# /www/server/openresty/bin/openresty -v
# service openresty restart

# cd /www/server/pmpanel && python3 plugins/openresty/index.py run_info

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

action=$1
type=$2

VERSION=$2
openrestyDir=${serverPath}/source/openresty

if id www &> /dev/null ;then 
    echo "www uid is `id -u www`"
    echo "www shell is `grep "^www:" /etc/passwd |cut -d':' -f7 `"
else
    groupadd www
	useradd -g www -s /bin/bash www
fi

if [ "${action}" = "upgrade" ];then
	bash -x $curPath/versions/$2/install.sh $1 || exit 1

	# 已安装 ModSecurity 防火墙时, 按新的 OpenResty 版本重新编译防火墙模块(旧模块与新版本不兼容)
	if [ -f $serverPath/modsecurity/version.pl ] && [ -f ${rootPath}/plugins/modsecurity/install.sh ];then
		cd "$rootPath/plugins/modsecurity" && bash install.sh rebuild_module || exit 1
		cd "$curPath" || exit 1
	fi

	mkdir -p $serverPath/web_conf/php/conf
	echo 'set $PHP_ENV 0;' > $serverPath/web_conf/php/conf/enable-php-00.conf

	#初始化 
    cd "$rootPath" || exit 1
    result=$(python3 plugins/openresty/index.py restart_for_upgrade) || exit 1
    if [ "$result" != ok ]; then printf '%s\n' "$result" >&2; exit 1; fi
    printf '%s\n' "$VERSION" > "$serverPath/openresty/version.pl" || exit 1
    exit 0
fi


if [ "${2}" = "" ];then
	echo '缺少安装脚本版本...'
	exit 0
fi 

if [ "${action}" = "uninstall" ];then
	if [ -f /usr/lib/systemd/system/openresty.service ] || [ -f /lib/systemd/system/openresty.service ];then
		systemctl stop openresty
		rm -rf /usr/systemd/system/openresty.service
		rm -rf /lib/systemd/system/openresty.service
		systemctl daemon-reload
	fi

	if [ -f $serverPath/openresty/init.d/openresty ];then
		$serverPath/openresty/init.d/openresty stop
	fi

	rm -rf $serverPath/openresty
fi

if [ "${action}" = "install" ];then
	bash -x $curPath/versions/$2/install.sh $1 || exit 1

	# 已安装 ModSecurity 防火墙时, 按新的 OpenResty 版本重新编译防火墙模块(旧模块与新版本不兼容)
	if [ -f $serverPath/modsecurity/version.pl ] && [ -f ${rootPath}/plugins/modsecurity/install.sh ];then
		cd "$rootPath/plugins/modsecurity" && bash install.sh rebuild_module || exit 1
		cd "$curPath" || exit 1
	fi
else
	bash -x $curPath/versions/$2/install.sh $1
fi

if [ "${action}" = "install" ] && [ -d $serverPath/openresty ];then
	echo "${VERSION}" > $serverPath/openresty/version.pl

	mkdir -p $serverPath/web_conf/php/conf
	echo 'set $PHP_ENV 0;' > $serverPath/web_conf/php/conf/enable-php-00.conf

	#初始化 
	cd ${rootPath} && python3 ${rootPath}/plugins/openresty/index.py start
	cd ${rootPath} && python3 ${rootPath}/plugins/openresty/index.py initd_install
fi
