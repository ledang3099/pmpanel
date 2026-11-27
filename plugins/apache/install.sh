#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin:/opt/homebrew/bin
export PATH

# cd /Users/dev/Desktop/pmdev/server/pmpanel/plugins/apache && bash install.sh install 2.4
# cd /www/server/pmpanel/plugins/apache && bash install.sh install 2.4
# cd /www/server/pmpanel/plugins/apache && bash install.sh upgrade 2.4

# curl -I -H "Accept-Encoding: br" http://localhost
# curl -I -H "Accept-Encoding: zstd" http://localhost
# curl --http3 -v https://www.xxx.com

# apt install ncat -y
# nc -u -v www.xx.com 443

# cd /Users/dev/Desktop/pmdev/server/pmpanel/plugins/apache && python3 plugins/apache/index.py start
# cd /www/server/pmpanel && python3 plugins/apache/index.py start
# cd /www/server/pmpanel && python3 plugins/apache/index.py run_info
# ps -ef|grep httpd | grep -v grep | awk '{print $2}'|xargs kill

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

sysName=`uname`
action=$1
type=$2

VERSION=$2
openrestyDir=${serverPath}/source/apache

if id www &> /dev/null ;then 
    echo "www uid is `id -u www`"
    echo "www shell is `grep "^www:" /etc/passwd |cut -d':' -f7 `"
else
    groupadd www
	useradd -g www -s /bin/bash www
fi

if [ "$type" != 2.4 ]; then
    echo '缺少安装脚本版本。' >&2
    exit 1
fi

if [ "${action}" = "uninstall" ];then
	if [ -f /usr/lib/systemd/system/httpd.service ] || [ -f /lib/systemd/system/httpd.service ];then
		systemctl stop httpd
		rm -rf /usr/systemd/system/httpd.service
		rm -rf /lib/systemd/system/httpd.service
		systemctl daemon-reload
	fi

	if [ -f $serverPath/apache/init.d/httpd ];then
		$serverPath/apache/init.d/httpd stop
	fi

	rm -rf $serverPath/apache
fi

bash "$curPath/versions/$type/install.sh" "$action" || exit 1

if [ "$action" = install ] || [ "$action" = upgrade ]; then
    mkdir -p "$serverPath/web_conf/php/conf" || exit 1
    printf 'set $PHP_ENV 0;\n' > "$serverPath/web_conf/php/conf/enable-php-00.conf"
    cd "$rootPath" || exit 1
    result=$(python3 plugins/apache/index.py start) || exit 1
    if [ "$result" != ok ]; then printf '%s\n' "$result" >&2; exit 1; fi
    if [ "$sysName" = Linux ]; then
        if [ "$action" = upgrade ]; then systemctl restart httpd || exit 1; fi
        systemctl is-active --quiet httpd && systemctl enable httpd || exit 1
    fi
    printf '%s\n' "$VERSION" > "$serverPath/apache/version.pl"
fi
