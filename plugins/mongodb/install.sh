#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin:/opt/homebrew/bin
export PATH

# https://www.mongodb.com/try/download/community

# cd /Users/dev/Desktop/pmdev/server/pmpanel/plugins/mongodb && /bin/bash install.sh install 7.0
# cd /www/server/pmpanel/plugins/mongodb && /bin/bash install.sh install 7.0
# cd /www/server/pmpanel/plugins/mongodb && /bin/bash install.sh install 9.0
# cd /www/server/pmpanel/plugins/mongodb && /bin/bash install.sh install 3.0
# cd /www/server/pmpanel && . bin/activate && python3 plugins/mongodb/index.py start


# db.createUser({
#     user: "demo", 
#     pwd: "123123", 
#     roles: [{role: "dbOwner", db: "demo"}]
# })

# db.auth("demo", "123123");
# import
# /www/server/mongodb/bin/mongorestore -h localhost -d demo --dir /tmp/*.json


curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

action=$1
VERSION=$2

sysName=`uname`
echo "use system: ${sysName}"

if [ "$sysName" = Darwin ]; then
    OSNAME=macos
else
    OSNAME=$(bash "$rootPath/scripts/getos.sh")
    if [ -z "$OSNAME" ]; then
        OSNAME=$(cat "$rootPath/data/osname.pl")
    fi
fi

if [ "macos" != "$OSNAME" ];then
	SYS_VERSION_ID=`cat /etc/*-release | grep VERSION_ID | awk -F = '{print $2}' | awk -F "\"" '{print $2}'`
fi

if [ -f ${rootPath}/bin/activate ];then
	. ${rootPath}/bin/activate
fi
Install_app()
{
	echo '正在安装脚本文件...'
	mkdir -p $serverPath/source

	if [ "$VERSION" != 9.0 ]; then
        cd "${rootPath}/plugins/php/lib" && bash openssl_11.sh
    fi
    cd "$curPath" || return 1
	shell_file=${curPath}/versions/${VERSION}/${OSNAME}.sh
	if [ "$VERSION" = 9.0 ]; then
		case "$OSNAME" in
			alma|rocky|rhel) shell_file="$curPath/versions/9.0/linux.sh" ;;
		esac
	fi

	if [ -f $shell_file ];then
		bash -x $shell_file

		if [ "$?" != "0" ];then
			echo '不支持...'
			exit 1
		fi
	else
		echo '不支持...'
		exit 1
	fi

	if [ "$?" = "0" ];then
		mkdir -p "$serverPath/mongodb" || return 1
		cd "$rootPath" || return 1
        local result
        if [ "$action" = upgrade ]; then
            result=$(PMPANEL_MONGODB_INSTALL_VERSION="$VERSION" python3 plugins/mongodb/index.py restart) || return 1
        else
            result=$(PMPANEL_MONGODB_INSTALL_VERSION="$VERSION" python3 plugins/mongodb/index.py start) || return 1
        fi
        if [ "$result" != ok ]; then
            printf '%s\n' "$result" >&2
            return 1
        fi
        if [ "$OSNAME" != macos ]; then
            python3 plugins/mongodb/index.py initd_install || return 1
        fi
        printf '%s\n' "$VERSION" > "$serverPath/mongodb/version.pl" || return 1
        echo 'mongodb安装完成'
	fi

	if [ "${VERSION}" = "3.0" ];then
		# 降低版本
		pip install pymongo==3.12.0
	else
		pip install pymongo
	fi
}

Uninstall_app()
{
	cd ${rootPath} && python3 ${rootPath}/plugins/mongodb/index.py stop
	rm -rf $serverPath/mongodb


	if [ -f /usr/lib/systemd/system/mongodb.service ] || [ -f /lib/systemd/system/mongodb.service ];then
		systemctl stop mongodb
		systemctl disable mongodb
		rm -rf /usr/lib/systemd/system/mongodb.service
		rm -rf /lib/systemd/system/mongodb.service
		systemctl daemon-reload
	fi

	echo 'mongodb卸载完成'
}

if [ "${action}" = 'install' ] || [ "$action" = "upgrade" ];then
	Install_app
elif [ "${action}" = 'uninstall' ];then
	Uninstall_app
else
	echo "OPTIONS ERROR"
fi
