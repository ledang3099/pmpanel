#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

VERSION=$2

if [ -f ${rootPath}/bin/activate ];then
	. ${rootPath}/bin/activate	
fi

Install_App()
{
    python3 -m pip install 'pyTelegramBotAPI==4.37.1' || return 1
    python3 -c 'from telebot import TeleBot; from telebot.util import quick_markup' || return 1
	echo '正在安装脚本文件...'
	mkdir -p $serverPath/source
	mkdir -p $serverPath/tgbot
    cp -R "$rootPath/plugins/tgbot/startup"/. "$serverPath/tgbot/" || return 1
    cd "$rootPath" || return 1
    result=$(python3 plugins/tgbot/index.py start) || return 1
    if [ "$result" != ok ]; then printf '%s\n' "$result" >&2; return 1; fi
    if [ "$(uname)" = Linux ]; then
        systemctl is-active --quiet tgbot && systemctl enable tgbot || return 1
    fi
    printf '%s\n' "$VERSION" > "$serverPath/tgbot/version.pl" || return 1
	echo '安装完成'
}

Uninstall_App()
{
	if [ -f /usr/lib/systemd/system/tgbot.service ];then
		systemctl stop tgbot
		systemctl disable tgbot
		rm -rf /usr/lib/systemd/system/tgbot.service
		systemctl daemon-reload
	fi

	if [ -f $serverPath/tgbot/initd/tgbot ];then
		$serverPath/tgbot/initd/tgbot stop
	fi

	rm -rf $serverPath/tgbot
	echo "Uninstall_redis"
}

action=$1
if [ "${1}" = 'install' ];then
	Install_App
else
	Uninstall_App
fi
