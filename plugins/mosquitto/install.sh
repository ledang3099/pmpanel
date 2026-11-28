#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

sysName=`uname`
echo "use system: ${sysName}"

# cd /Users/dev/Desktop/pmdev/server/pmpanel/plugins/mosquitto && bash install.sh install 2.0.18
# cd /www/pmpanel/plugins/mosquitto && bash install.sh install 2.0.18

VERSION=$2

# 编译依赖: cmake、OpenSSL、cJSON(2.0 起 mosquitto_ctrl 和动态安全插件需要)
Install_Deps()
{
	if [ "$sysName" = "Darwin" ]; then
		brew install cmake openssl@3 cjson || return 1
	elif command -v apt-get >/dev/null; then
		apt-get install -y cmake build-essential pkg-config libssl-dev libcjson-dev || return 1
	elif command -v dnf >/dev/null; then
		dnf install -y epel-release >/dev/null 2>&1
		dnf install -y cmake gcc gcc-c++ make pkgconfig openssl-devel cjson-devel || return 1
	elif command -v yum >/dev/null; then
		yum install -y epel-release >/dev/null 2>&1
		yum install -y cmake gcc gcc-c++ make pkgconfig openssl-devel cjson-devel || return 1
	elif command -v zypper >/dev/null; then
		zypper install -y cmake gcc gcc-c++ make pkg-config libopenssl-devel cJSON-devel || return 1
	elif command -v pacman >/dev/null; then
		pacman -Sy --noconfirm cmake base-devel openssl cjson || return 1
	fi
	return 0
}

Install_App()
{
	Install_Deps || { echo '安装编译依赖失败' >&2; return 1; }
	if id mosquitto &> /dev/null ;then 
	    echo "mosquitto UID is `id -u mosquitto`"
	    echo "mosquitto Shell is `grep "^mosquitto:" /etc/passwd |cut -d':' -f7 `"
	else
	    groupadd mosquitto
		useradd -g mosquitto mosquitto
	fi

	echo '正在安装脚本文件...'
    case "$VERSION" in
        2.0.23) digest=dc815cbd9f27db2fa7fcb06390f7ec1d65b5300827f4c1c7402e62ce9cfd5660 ;;
        2.1.4) digest=ca30b26ccd3041c0e11fc407fe4f2e62bc445e8d8dea94a083cc60c09bd5ea30 ;;
        *) return 1 ;;
    esac
    source "$rootPath/scripts/tools/verified-download.sh" || return 1
    sources="$serverPath/source"
    mkdir -p "$sources" || return 1
    archive="$sources/mosquitto-$VERSION.tar.gz"
    verified_download "https://mosquitto.org/files/source/mosquitto-$VERSION.tar.gz" "$archive" "$digest" || return 1
    build_dir=$(mktemp -d "$sources/mosquitto-build.XXXXXX") || return 1
    trap 'rm -rf -- "$build_dir"' EXIT
    tar -xzf "$archive" -C "$build_dir" || return 1
    cd "$build_dir/mosquitto-$VERSION" || return 1
    prefix="$serverPath/mosquitto"
    cmake -DWITH_DOCS=OFF -DWITH_TESTS=OFF -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
        -DCMAKE_INSTALL_PREFIX="$prefix" -DCMAKE_INSTALL_LIBDIR=lib \
        -DCMAKE_INSTALL_RPATH="$prefix/lib" . || return 1
    make && make install || return 1

	if [ -d $serverPath/mosquitto ];then
		cd "$rootPath" || return 1
        [ "$(python3 plugins/mosquitto/index.py restart)" = ok ] || return 1
        if [ "$sysName" != Darwin ]; then
            [ "$(python3 plugins/mosquitto/index.py initd_install)" = ok ] || return 1
        fi
        printf '%s\n' "$VERSION" > "$prefix/version.pl" || return 1
        echo '安装mosquitto完成'
	fi
}

Uninstall_App()
{
	if [ -f /usr/lib/systemd/system/mosquitto.service ];then
		systemctl stop mosquitto
		systemctl disable mosquitto
		rm -rf /usr/lib/systemd/system/mosquitto.service
		systemctl daemon-reload
	fi

	if [ -f $serverPath/mosquitto/initd/mosquitto ];then
		$serverPath/mosquitto/initd/mosquitto stop
	fi

	rm -rf $serverPath/mosquitto
	echo "卸载mosquitto成功"
}

action=$1
if [ "${1}" = 'install' ];then
	Install_App
else
	Uninstall_App
fi
