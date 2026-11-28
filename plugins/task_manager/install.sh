#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin:/opt/homebrew/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

VERSION=$2

# python3 plugins/task_manager/task_manager_index.py
# /www/server/pmpanel/bin/python3 /www/server/pmpanel/plugins/task_manager/process_network_total.py
# ps -ef|grep process_network_total| grep -v grep | awk '{print $2}' | xargs kill -9

if [ -f ${rootPath}/bin/activate ];then
	. ${rootPath}/bin/activate
fi

Install_App()
{
    echo '正在安装脚本文件...'
    if command -v apt-get >/dev/null; then
        apt-get install -y libpcap-dev || return 1
    elif command -v dnf >/dev/null; then
        dnf install -y libpcap-devel || return 1
    elif command -v yum >/dev/null; then
        yum install -y libpcap-devel || return 1
    fi

    if ! python3 -c 'import pcap' >/dev/null 2>&1; then
        source "$rootPath/scripts/tools/verified-download.sh" || return 1
        sources="$serverPath/source/task_manager"
        mkdir -p "$sources" || return 1
        archive="$sources/pypcap-1.3.0.tar.gz"
        verified_download \
            https://files.pythonhosted.org/packages/db/4f/419ad9b163f3e86c32ae3b1e2937709520e24dce589897a26fb875189520/pypcap-1.3.0.tar.gz \
            "$archive" 669976786b2b4c43869c0ecf6228cbbb70336d1d8eb8d4fe2a3a81df395f45b5 || return 1
        stage=$(mktemp -d "$sources/build.XXXXXX") || return 1
        trap 'rm -rf -- "$stage"' EXIT
        tar -xzf "$archive" -C "$stage" || return 1
        python3 -m venv "$stage/build-env" || return 1
        "$stage/build-env/bin/python" -m pip install 'Cython>=3,<4' setuptools wheel || return 1
        cd "$stage/pypcap-1.3.0" || return 1
        patch -p1 < "$curPath/pypcap-buffer.patch" || return 1
        "$stage/build-env/bin/cython" -3 pcap.pyx || return 1
        "$stage/build-env/bin/python" -m pip wheel --no-build-isolation --no-deps -w "$stage" . || return 1
        python3 -m pip install "$stage"/pypcap-*.whl || return 1
    fi
    python3 -c 'import pcap' || return 1
    mkdir -p "$serverPath/task_manager" || return 1
    printf '%s\n' "$VERSION" > "$serverPath/task_manager/version.pl" || return 1
    echo '安装任务管理器成功'

}

Uninstall_App()
{	
	rm -rf $serverPath/task_manager
	echo "卸载任务管理器成功"
}

action=$1
if [ "${1}" = 'install' ];then
	Install_App
else
	Uninstall_App
fi
