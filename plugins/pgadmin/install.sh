#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin:/opt/homebrew/bin
export PATH

function version_gt() { test "$(echo "$@" | tr " " "\n" | sort -V | head -n 1)" != "$1"; }
function version_le() { test "$(echo "$@" | tr " " "\n" | sort -V | head -n 1)" = "$1"; }
function version_lt() { test "$(echo "$@" | tr " " "\n" | sort -rV | head -n 1)" != "$1"; }
function version_ge() { test "$(echo "$@" | tr " " "\n" | sort -rV | head -n 1)" = "$1"; }

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

if [ -f ${rootPath}/bin/activate ];then
	. ${rootPath}/bin/activate
fi


P_VER=`python3 -V | awk '{print $2}'`
echo "python:$P_VER"

# https://cn.linux-console.net/?p=6560

# cd /Users/dev/Desktop/pmdev/server/pmpanel/plugins/pgadmin && bash install.sh install 4
# cd /www/server/pmpanel/plugins/pgadmin && bash install.sh install 4

# python /www/server/pgadmin/run/lib/python3.10/site-packages/pgadmin4/setup.py --help
# python /www/server/pgadmin/run/lib/python3.10/site-packages/pgadmin4/setup.py add-user pmpanel@gmail.com 123123
# cd /www/server/pmpanel && python3 plugins/pgadmin/index.py start
# cd /www/server/pmpanel && python3 plugins/pgadmin/index.py stop

if [ "$sys_os" = "Darwin" ];then
	BAK='_bak'
else
	BAK=''
fi

sysName=`uname`
echo "use system: ${sysName}"

if [ "${sysName}" = "Darwin" ]; then
	OSNAME='macos'
elif grep -Eqi "CentOS" /etc/issue || grep -Eq "CentOS" /etc/*-release; then
	OSNAME='centos'
elif grep -Eqi "Fedora" /etc/issue || grep -Eq "Fedora" /etc/*-release; then
	OSNAME='fedora'
elif grep -Eqi "Debian" /etc/issue || grep -Eq "Debian" /etc/*-release; then
	OSNAME='debian'
elif grep -Eqi "Ubuntu" /etc/issue || grep -Eq "Ubuntu" /etc/*-release; then
	OSNAME='ubuntu'
elif grep -Eqi "Raspbian" /etc/issue || grep -Eq "Raspbian" /etc/*-release; then
	OSNAME='raspbian'
else
	OSNAME='unknow'
fi

Install_pgadmin()
{
	# if [ -d $serverPath/pgadmin ];then
	# 	exit 0
	# fi

	if version_lt "$P_VER" "3.8.0" ;then
		echo 'Python版本太低,无法安装'
		return 1
	fi
	PG_DIR=${serverPath}/pgadmin/run
	PG_DATA_DIR=${serverPath}/pgadmin/data
	mkdir -p $PG_DIR
	mkdir -p $PG_DATA_DIR
    if [ ! -x "$PG_DIR/bin/python" ]; then
        python3 -m venv "$PG_DIR" || return 1
    fi
    "$PG_DIR/bin/python" -m pip install gunicorn pgadmin4==9.19 || return 1
    cd "$rootPath" || return 1
    python3 plugins/pgadmin/index.py start || return 1
    if [ "$(uname)" = Linux ]; then
        for attempt in 1 2 3 4 5 6 7 8 9 10; do
            if curl -fsS --max-time 3 --unix-socket /tmp/pgadmin4.sock http://localhost/misc/ping >/dev/null 2>&1; then
                printf '%s\n' "$1" > "$serverPath/pgadmin/version.pl"
                return $?
            fi
            sleep 1
        done
        return 1
    fi
    printf '%s\n' "$1" > "$serverPath/pgadmin/version.pl"

}

Uninstall_pgadmin()
{
	cd ${rootPath} && python3 ${rootPath}/plugins/pgadmin/index.py stop

	if [ -f /usr/lib/systemd/system/pgadmin.service ];then
		systemctl stop pgadmin
		systemctl disable pgadmin
		rm -rf /usr/lib/systemd/system/pgadmin.service
		systemctl daemon-reload
	fi

	if [ -f /lib/systemd/system/pgadmin.service ];then
		systemctl stop pgadmin
		systemctl disable pgadmin
		rm -rf /lib/systemd/system/pgadmin.service
		systemctl daemon-reload
	fi

	rm -rf ${serverPath}/pgadmin
	# rm -rf /var/lib/pgadmin
	# rm -rf /var/log/pgadmin
	echo '卸载完成'
}

action=$1
if [ "${1}" = 'install' ];then
	Install_pgadmin $2
else
	Uninstall_pgadmin $2
fi
