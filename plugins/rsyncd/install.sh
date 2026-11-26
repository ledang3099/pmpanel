#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

# cd /www/server/pmpanel/plugins/rsyncd && bash install.sh install 3.5

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")
sysName=`uname`

# rsync 源码: 官方仓库的 v3.5.2 标签, 并校验提交哈希, 防止源码被篡改
RSYNC_VERSION=3.5.2
RSYNC_COMMIT=41bbd895668767e155b2eb6da64f37afa9cb8724
RSYNC_REPO=https://github.com/RsyncProject/rsync

bash ${rootPath}/scripts/getos.sh
OSNAME=`cat ${rootPath}/data/osname.pl`

if [ -f ${rootPath}/bin/activate ];then
	. ${rootPath}/bin/activate
fi

if ! id www &> /dev/null ;then
	groupadd www
	useradd -g www -s /usr/sbin/nologin www
fi

Install_Deps()
{
	if [ "$OSNAME" = "debian" ] || [ "$OSNAME" = "ubuntu" ];then
		apt install -y rsync lsyncd git gcc make autoconf automake
		apt install -y libssl-dev libxxhash-dev libzstd-dev liblz4-dev libacl1-dev libattr1-dev
	elif [ "$OSNAME" = "arch" ]; then
		echo y | pacman -Sy rsync lsyncd git gcc make autoconf automake openssl xxhash zstd lz4 acl attr
	elif [ "$OSNAME" = "opensuse" ]; then
		zypper install -y rsync lsyncd git gcc make autoconf automake libopenssl-devel libxxhash-devel libzstd-devel liblz4-devel libacl-devel libattr-devel
	elif [ "$OSNAME" = "macos" ]; then
		echo "macos: skip"
	else
		yum install -y epel-release
		yum install -y rsync lsyncd git gcc make autoconf automake openssl-devel xxhash-devel libzstd-devel lz4-devel libacl-devel libattr-devel
	fi
}

# 编译安装 rsync 到插件目录(不覆盖系统自带的 rsync); 失败时使用系统 rsync
Build_Rsync()
{
	local src=$serverPath/source/rsyncd
	local dst=$serverPath/rsyncd
	mkdir -p $src
	rm -rf $src/rsync-${RSYNC_VERSION}

	git clone -q --depth 1 --branch v${RSYNC_VERSION} ${RSYNC_REPO} $src/rsync-${RSYNC_VERSION} || return 1
	local head=$(git -C $src/rsync-${RSYNC_VERSION} rev-parse HEAD)
	if [ "$head" != "$RSYNC_COMMIT" ];then
		echo "rsync 源码校验失败: $head"
		rm -rf $src/rsync-${RSYNC_VERSION}
		return 1
	fi

	cd $src/rsync-${RSYNC_VERSION} || return 1
	./configure --prefix=$dst --disable-md2man --disable-idn --with-included-popt --with-included-zlib || \
	./configure --prefix=$dst --disable-md2man --disable-idn --disable-xxhash --disable-zstd --disable-lz4 --with-included-popt --with-included-zlib || return 1
	make -j$(nproc 2>/dev/null || echo 2) && make install || return 1
	cd $curPath
	rm -rf $src/rsync-${RSYNC_VERSION}
	$dst/bin/rsync --version | head -1
	return 0
}

Install_rsyncd()
{
	echo '正在安装依赖...'
	Install_Deps

	mkdir -p $serverPath/rsyncd/receive $serverPath/rsyncd/send
	chmod 700 $serverPath/rsyncd/receive $serverPath/rsyncd/send

	if [ "$OSNAME" != "macos" ];then
		echo "正在编译 rsync ${RSYNC_VERSION} ..."
		if ! Build_Rsync; then
			echo "rsync ${RSYNC_VERSION} 编译失败, 将使用系统自带的 rsync: $(rsync --version 2>/dev/null | head -1)"
		fi
	fi

	echo "${RSYNC_VERSION%.*}" > $serverPath/rsyncd/version.pl
	cd ${rootPath} && python3 ${rootPath}/plugins/rsyncd/index.py init
	cd ${rootPath} && python3 ${rootPath}/plugins/rsyncd/index.py start
	cd ${rootPath} && python3 ${rootPath}/plugins/rsyncd/index.py initd_install
	echo '安装完成'
}

Uninstall_rsyncd()
{
	for s in rsyncd lsyncd; do
		if [ -f /etc/systemd/system/$s.service ];then
			systemctl stop $s
			systemctl disable $s
			rm -f /etc/systemd/system/$s.service
		fi
	done
	systemctl daemon-reload

	cd ${rootPath} && python3 ${rootPath}/plugins/rsyncd/tool_task.py remove

	rm -rf $serverPath/rsyncd
	echo "卸载完成"
}

action=$1
if [ "${1}" = 'install' ] || [ "${1}" = 'upgrade' ];then
	Install_rsyncd
else
	Uninstall_rsyncd
fi
