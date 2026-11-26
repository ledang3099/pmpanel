#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")
sysName=`uname`

bash ${rootPath}/scripts/getos.sh
OSNAME=`cat ${rootPath}/data/osname.pl`
OSNAME_ID=`cat /etc/*-release | grep VERSION_ID | awk -F = '{print $2}' | awk -F "\"" '{print $2}'`


VERSION=3.4.8
MIN_VERSION=3.4
Install_App()
{
    echo '正在安装Haproxy软件...'
    APP_DIR="$serverPath/source/haproxy"
    mkdir -p "$APP_DIR" || return 1
    source "$rootPath/scripts/tools/verified-download.sh" || return 1
    archive="$APP_DIR/haproxy-${VERSION}.tar.gz"
    verified_download "https://www.haproxy.org/download/${MIN_VERSION}/src/haproxy-${VERSION}.tar.gz" \
        "$archive" 024bd521a6cbbe32b426853147e6bbd6a89b107c5a34144846193fee5b7c6ed1 || return 1
    tar -xzf "$archive" -C "$APP_DIR" || return 1
    cd "$APP_DIR/haproxy-$VERSION" || return 1
    target=linux-glibc
    if [ "$OSNAME" = macos ]; then target=osx; fi
    make TARGET="$target" && make install PREFIX="$serverPath/haproxy" || return 1
    printf '%s\n' "$MIN_VERSION" > "$serverPath/haproxy/version.pl"
    echo '安装Haproxy成功'

    #Haproxy日志配置
    if [ -f /etc/rsyslog.conf ];then
        find_ha=`cat /etc/rsyslog.conf | grep haproxy`
        if [ "$find_ha" != "" ];then
            echo $find_ha
        else
            echo "---------------------------------------------"
            echo "" > ${serverPath}/haproxy/haproxy.log
            echo "local0.*  ${serverPath}/haproxy/haproxy.log" >> /etc/rsyslog.conf
            systemctl restart syslog
            echo "syslog默认的haproxy配置"
            echo "local0.*  ${serverPath}/haproxy/haproxy.log >> /etc/rsyslog.conf"
            echo "---------------------------------------------"
        fi
    fi

    #删除解压源码
    if [ -d ${APP_DIR}/haproxy-${VERSION} ];then
        rm -rf ${APP_DIR}/haproxy-${VERSION}
    fi
}

Uninstall_App()
{
    if [ -f $serverPath/haproxy/initd/haproxy ];then
        $serverPath/haproxy/initd/haproxy stop
    fi

    rm -rf $serverPath/haproxy
    echo "卸载Haproxy成功"
}

action=$1
if [ "${1}" = 'install' ];then
    Install_App
elif [ "$1" = uninstall ]; then
    Uninstall_App
else
    exit 1
fi
