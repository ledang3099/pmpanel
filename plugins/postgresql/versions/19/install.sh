#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin:/opt/homebrew/bin
export PATH

#https://www.postgresql.org/ftp/source/

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")
sysName=`uname`

postgreDir=${serverPath}/source/postgresql

VERSION=19.0
OPTIONS=""
action=$1
# su - postgres -c "/www/server/postgresql/bin/pg_ctl start -D /www/server/postgresql/data"

Install_App()
{
    mkdir -p ${postgreDir}
    echo '正在安装脚本文件...'

    if id postgres &> /dev/null ;then
        echo "postgres uid is `id -u postgres`"
        echo "postgres shell is `grep "^postgres:" /etc/passwd |cut -d':' -f7 `"
    else
        which groupadd && groupadd postgres
        which useradd && useradd -g postgres postgres
    fi

    if [ "$sysName" != "Darwin" ];then
        if [ ! -d /home/postgres ];then
            mkdir -p /home/postgres
        fi
    fi

    # if [ "$sysName" != "Darwin" ];then
    # 	mkdir -p /var/log/mariadb
    # 	touch /var/log/mariadb/mariadb.log
    # fi

    # ----- cpu start ------
    if [ -z "${cpuCore}" ]; then
        cpuCore="1"
    fi

    if [ -f /proc/cpuinfo ];then
        cpuCore=`cat /proc/cpuinfo | grep "processor" | wc -l`
    fi

    MEM_INFO=$(free -m|grep Mem|awk '{printf("%.f",($2)/1024)}')
    if [ "${cpuCore}" != "1" ] && [ "${MEM_INFO}" != "0" ];then
        if [ "${cpuCore}" -gt "${MEM_INFO}" ];then
            cpuCore="${MEM_INFO}"
        fi
    else
        cpuCore="1"
    fi

    # for stable installation
    if [ "$cpuCore" -gt "1" ];then
        cpuCore=`echo "$cpuCore" | awk '{printf("%.f",($1)*0.8)}'`
    fi
    # ----- cpu end ------

    if [ -d "$serverPath/postgresql" ]; then
        echo "PostgreSQL 19 requires a fresh prefix or an explicit data migration." >&2
        return 1
    fi
    source "$rootPath/scripts/tools/verified-download.sh" || return 1
    archive="$postgreDir/postgresql-${VERSION}.tar.bz2"
    verified_download "https://ftp.postgresql.org/pub/source/v${VERSION}/postgresql-${VERSION}.tar.bz2" \
        "$archive" a89fd70efbad6a08c7dbed8d4872e3af30170d9e5ca9dc7906523be95b4e692d || return 1
    tar -xjf "$archive" -C "$postgreDir" || return 1

    if [ "$sysName" = "Darwin" ];then
        OPENSSL_DEPEND_DIR=`brew --prefix openssl@3`
        OPTIONS="$OPTIONS --with-includes="${OPENSSL_DEPEND_DIR}/include""
        OPTIONS="$OPTIONS --with-libraries="${OPENSSL_DEPEND_DIR}/lib""

        LIB_DEPEND_DIR=`brew --prefix icu4c`
        export PKG_CONFIG_PATH="${LIB_DEPEND_DIR}/lib/pkgconfig:$PKG_CONFIG_PATH"
        export PATH="${LIB_DEPEND_DIR}/bin:$PATH"
        OPTIONS="$OPTIONS PKG_CONFIG_PATH="${LIB_DEPEND_DIR}/lib/pkgconfig""
    fi

    cd "$postgreDir/postgresql-${VERSION}" || return 1
    ./configure --prefix="$serverPath/postgresql" --with-openssl $OPTIONS || return 1
    make -j"${cpuCore}" && make install || return 1
    make -C contrib && make -C contrib install || return 1
    printf '%s\n' "$VERSION" > "$serverPath/postgresql/version.pl"

}

Uninstall_App()
{
    if [ -f /usr/lib/systemd/system/postgresql.service ];then
        systemctl stop postgresql
        systemctl disable postgresql
        rm -rf /usr/lib/systemd/system/postgresql.service
        systemctl daemon-reload
    fi

    if [ -f /lib/systemd/system/postgresql.service ];then
        systemctl stop postgresql
        systemctl disable postgresql
        rm -rf /lib/systemd/system/postgresql.service
        systemctl daemon-reload
    fi

    if [ -f $serverPath/postgresql/initd/postgresql ];then
        $serverPath/postgresql/initd/postgresql stop
    fi

    if [ -d $serverPath/postgresql ];then
        rm -rf $serverPath/postgresql
    fi

    echo '卸载[postgresql]完成'
}


if [ "${1}" = "install" ];then
    Install_App
else
    Uninstall_App
fi
