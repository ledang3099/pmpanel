#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

# cd /www/server/pmpanel && . /www/server/pmpanel/bin/activate && python3 /www/server/pmpanel/plugins/ollama/index.py get_ai_model_list 1.0

action=$1
type=$2

if [ "${2}" = "" ];then
	echo '缺少安装脚本...'
	exit 0
fi 

if [ "$type" != 0.40.18 ] && [ ! -d "$curPath/versions/$type" ]; then
	echo '缺少安装脚本2...'
	exit 0
fi

if [ "$type" = 0.40.18 ]; then type=1.0; fi
bash "$curPath/versions/$type/install.sh" "$1" || exit $?

if [ "${action}" = "uninstall" ];then
	if [ -f /usr/lib/systemd/system/ollama.service ] || [ -f /lib/systemd/system/ollama.service ] ;then
		systemctl stop ollama
		systemctl disable ollama
		rm -rf /usr/lib/systemd/system/ollama.service
		rm -rf /lib/systemd/system/ollama.service
		systemctl daemon-reload
	fi
fi
