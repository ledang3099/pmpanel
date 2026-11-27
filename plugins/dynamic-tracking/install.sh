#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

# cd /www/server/pmpanel/plugins/dynamic-tracking && /bin/bash install.sh uninstall 1.0
# cd /www/server/pmpanel/plugins/dynamic-tracking && /bin/bash install.sh install 1.0

VERSION=$2

if [ -f ${rootPath}/bin/activate ];then
	. ${rootPath}/bin/activate
fi


OSNAME=`bash ${rootPath}/scripts/getos.sh`

if [ "" = "$OSNAME" ];then
	OSNAME=`cat ${rootPath}/data/osname.pl`
fi

if [ "macos" != "$OSNAME" ];then
	SYS_VERSION_ID=`cat /etc/*-release | grep VERSION_ID | awk -F = '{print $2}' | awk -F "\"" '{print $2}'`
fi

Install_App()
{

	echo '正在安装脚本文件...'
	mkdir -p $serverPath/source
	mkdir -p $serverPath/dynamic-tracking

    commit=41fee1f99f9276008b7cd112fca19dc3ea84ac32
    source "$rootPath/scripts/tools/verified-download.sh" || return 1
    archive="$serverPath/source/FlameGraph-$commit.tar.gz"
    verified_download "https://codeload.github.com/brendangregg/FlameGraph/tar.gz/$commit" "$archive" \
        b1ba3aaaf296ab72ced4dca84514377a4b2c8122831d743f726c106d3d339c2a || return 1
    staging=$(mktemp -d "$serverPath/source/flamegraph.XXXXXX") || return 1
    trap 'rm -rf -- "$staging"' EXIT
    tar -xzf "$archive" -C "$staging" || return 1
    mkdir -p "$serverPath/dynamic-tracking/FlameGraph" || return 1
    cp -R "$staging/FlameGraph-$commit"/. "$serverPath/dynamic-tracking/FlameGraph/" || return 1

	# apt install linux-tools-$(uname -r) linux-tools-generic -y
	# apt install linux-tools-$(uname -r) linux-tools-generic -y --fix-missing

	

	shell_file=${curPath}/versions/${OSNAME}.sh
	echo $shell_file
	if [ ! -f $shell_file ];then
		echo '不支持...' 
		exit 1
	fi
	
	bash -x "$shell_file" || return 1

	echo "cp -R "$curPath/shell" "$serverPath/dynamic-tracking/" || return 1"
	cp -R "$curPath/shell" "$serverPath/dynamic-tracking/" || return 1

	echo "${VERSION}" > $serverPath/dynamic-tracking/version.pl
	echo '安装完成'

	cd ${rootPath} && python3 ${rootPath}/plugins/dynamic-tracking/index.py start
	# cd ${rootPath} && python3 ${rootPath}/plugins/dynamic-tracking/index.py initd_install

}

Uninstall_App()
{
	rm -rf $serverPath/dynamic-tracking
	echo "Uninstall_App"
}

action=$1
if [ "${1}" = 'install' ];then
	Install_App
elif [ "$action" = uninstall ]; then
    Uninstall_App
else
    exit 1
fi
