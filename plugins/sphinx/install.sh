#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin:/opt/homebrew/bin
export PATH

# "3.2.1","3.3.1","3.4.1","3.5.1","3.6.1","3.7.1","3.8.1"
download() {
    local url="$1"
    local out="$2"
    if [ -f "$out" ]; then
        return 0
    fi
    local tmp="${out}.downloading"
    rm -f "$tmp"
    if command -v wget >/dev/null 2>&1; then
        wget -O "$tmp" "$url"
    else
        curl -fL -o "$tmp" "$url"
    fi
    if [ $? -ne 0 ] || [ ! -s "$tmp" ]; then
        rm -f "$tmp"
        echo "download failed: $url"
        return 1
    fi
    mv -f "$tmp" "$out"
    echo "download $out successful!"
    return 0
}


curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")
sysName=`uname`
sysArch=`arch`


if [ -f ${rootPath}/bin/activate ];then
	. ${rootPath}/bin/activate
fi

# cd /www/server/pmpanel && . bin/activate && python3 plugins/sphinx/index.py rebuild
# cd /www/server/pmpanel/plugins/sphinx && bash install.sh install 3.1.1
# cd /www/server/pmpanel && . bin/activate && python3 plugins/sphinx/index.py db_to_sphinx && /www/server/sphinx/bin/bin/indexer -c /www/server/sphinx/sphinx.conf --all --rotate
# /Users/dev/Desktop/pmdev/server/sphinx/bin/bin/indexer /Users/dev/Desktop/pmdev/server/sphinx/sphinx.conf --all --rotate

# cd /www/server/pmpanel && . bin/activate && python3 plugins/sphinx/index.py sphinx_cmd

# /Users/dev/Desktop/pmdev/server/sphinx/bin/bin/indexer /Users/dev/Desktop/pmdev/server/sphinx/sphinx.conf --all --rotate

# cd /www/server/pmpanel && . bin/activate && python3 plugins/sphinx/index.py start
bash ${rootPath}/scripts/getos.sh
# echo "bash ${rootPath}/scripts/getos.sh"
OSNAME="macos"
if [ -f ${rootPath}/data/osname.pl ];then
	OSNAME=`cat ${rootPath}/data/osname.pl`	
fi

if [ "${OSNAME}" = "centos" ] || 
	[ "${OSNAME}" = "fedora" ] ||
	[ "${OSNAME}" = "alma" ]; then
	yum install -y postgresql-libs unixODBC
fi

# http://sphinxsearch.com/files/sphinx-3.1.1-612d99f-linux-amd64.tar.gz
# https://github.com/mw-plugin/sphinx/releases/download/init/sphinx-3.1.1-612d99f-linux-amd64.tar.gz
VERSION=$2

# echo $VERSION

if [ "$VERSION" = "3.1.1" ];then
	if [ "$sysArch" != "x86_64" ];then
		echo "no support"
		exit 1
	fi
	VERSION_NUM=${VERSION}-612d99f
elif [ "$VERSION" = "3.2.1" ]; then
	if [ "$sysArch" != "x86_64" ];then
		echo "no support"
		exit 1
	fi
	VERSION_NUM=${VERSION}-f152e0b
elif [ "$VERSION" = "3.3.1" ]; then
	if [ "$sysArch" != "x86_64" ];then
		echo "no support"
		exit 1
	fi
	VERSION_NUM=${VERSION}-b72d67b
elif [ "$VERSION" = "3.4.1" ]; then
	if [ "$sysArch" != "x86_64" ];then
		echo "no support"
		exit 1
	fi
	VERSION_NUM=${VERSION}-efbcc65
elif [ "$VERSION" = "3.5.1" ]; then
	if [ "$sysArch" != "x86_64" ];then
		echo "no support"
		exit 1
	fi
	VERSION_NUM=${VERSION}-82c60cb
elif [ "$VERSION" = "3.6.1" ]; then
	if [ "$sysArch" != "x86_64" ];then
		echo "no support"
		exit 1
	fi
	VERSION_NUM=${VERSION}-c9dbeda
elif [ "$VERSION" = "3.7.1" ]; then
	VERSION_NUM=${VERSION}-da9f8a4
elif [ "$VERSION" = "3.8.1" ]; then
	VERSION_NUM=${VERSION}-d25e0bb
elif [ "$VERSION" = "3.9.1" ]; then
	VERSION_NUM=${VERSION}-141d2ea
fi

# echo $VERSION_NUM

Install_current_sphinx() (
    case "$sysName:$sysArch" in
        Linux:x86_64)
            grep -qw avx2 /proc/cpuinfo || { echo 'Sphinx 3.9.1 x86_64 requires AVX2' >&2; return 1; }
            platform=linux-amd64
            digest=07b3214d40dd4cb2b5dcd951af292aee33b2397e87f201a81c606c1181b0ab46
            ;;
        Linux:aarch64)
            platform=linux-aarch64
            digest=ef862d7bf624018294985139c09ca871f9e11515c98277a378d4fe4b4827fca6
            ;;
        Darwin:arm64)
            platform=darwin-aarch64
            digest=1d9ff25e0d63942d1a6f04f8fab5894f94384529c72f8ba682240200beb0ea2d
            ;;
        *) echo 'Sphinx 3.9.1 has no verified archive for this platform' >&2; return 1 ;;
    esac

    source "$rootPath/scripts/tools/verified-download.sh" || return 1
    sources="$serverPath/source/sphinx"
    mkdir -p "$sources" || return 1
    archive="sphinx-3.9.1-141d2ea-$platform.tar.gz"
    verified_download "https://sphinxsearch.com/files/$archive" "$sources/$archive" "$digest" || return 1
    stage=$(mktemp -d "$sources/install.XXXXXX") || return 1
    trap 'rm -rf -- "$stage"' EXIT
    tar -xzf "$sources/$archive" -C "$stage" || return 1
    "$stage/sphinx-3.9.1/bin/searchd" --help >/dev/null || return 1
    mkdir -p "$serverPath/sphinx/bin" || return 1
    cp -R "$stage/sphinx-3.9.1"/. "$serverPath/sphinx/bin/" || return 1
    printf '3.9.1\n' > "$serverPath/sphinx/version.pl"
    cd "$rootPath" || return 1
    python3 plugins/sphinx/index.py start || return 1
    if [ "$sysName" = Linux ]; then
        python3 plugins/sphinx/index.py initd_install || return 1
    fi
)

Install_sphinx()
{
	echo '正在安装Sphinx...'
	mkdir -p $serverPath/sphinx

	SPHINX_DIR=${serverPath}/source/sphinx
	mkdir -p $SPHINX_DIR

	SPH_NAME=amd64
	if [ "$sysArch" = "arm64" ];then
		SPH_NAME=amd64
	elif [ "$sysArch" = "x86_64" ]; then
		SPH_NAME=amd64
	elif [ "$sysArch" = "aarch64" ]; then
		SPH_NAME=aarch64
	fi

	if [ "$sysName" = "Darwin" ] && [ "$VERSION" = "3.7.1" ];then
		SPH_NAME=aarch64
	fi

	SPH_SYSNAME=linux
	if [ $sysName = 'Darwin' ]; then
		SPH_SYSNAME=darwin
	elif [ "$sysName" = "aarch64" ]; then
		SPH_NAME=aarch64
	elif [ "$sysName" = "freebsd" ]; then
		SPH_NAME=freebsd
	fi

	if [ "$SPH_SYSNAME" = "linux" ];then
		glibc_ver=`ldd  --version | grep libc | awk -F ')' '{print $2}'|awk '{gsub(/^\s+|\s+$/, "");print}'`
		if [ "$VERSION" = "3.7.1" ] && [ `echo "2.29 > $glibc_ver " | bc` -eq 1 ];then
			SPH_NAME=${SPH_NAME}-glibc2.17
		fi
		if [ "$VERSION" = "3.6.1" ] && [ `echo "2.29 > $glibc_ver " | bc` -eq 1 ];then
			SPH_NAME=${SPH_NAME}-glibc2.17
		fi
	fi
	

	FILE_NAME=sphinx-${VERSION_NUM}-${SPH_SYSNAME}-${SPH_NAME}
	FILE_TGZ=${FILE_NAME}.tar.gz

	echo $FILE_TGZ
	# curl -sSLo ${SPHINX_DIR}/${FILE_TGZ} http://sphinxsearch.com/files/${FILE_TGZ}
	if [ ! -f ${SPHINX_DIR}/${FILE_TGZ} ];then
		# https://github.com/mw-plugin/sphinx/releases/download/init/sphinx-3.1.1-612d99f-darwin-amd64.tar.gz
		download "https://github.com/mw-plugin/sphinx/releases/download/init/${FILE_TGZ}" ${SPHINX_DIR}/${FILE_TGZ}
		# wget --no-check-certificate -O ${SPHINX_DIR}/${FILE_TGZ} https://github.com/mw-plugin/sphinx/releases/download/init/${FILE_TGZ}
		# wget --no-check-certificate -O ${SPHINX_DIR}/${FILE_TGZ} http://sphinxsearch.com/files/${FILE_TGZ}
	fi

	if [ ! -f ${SPHINX_DIR}/${FILE_TGZ} ];then
		echo "download file ${SPHINX_DIR}/${FILE_TGZ} fail!"
		exit 1
	fi

	cd ${SPHINX_DIR} && tar -zxvf ${FILE_TGZ}
	
	if [ "$?" = "0" ];then
		mkdir -p $serverPath/sphinx/bin
		cp -rf ${SPHINX_DIR}/sphinx-${VERSION}/* $serverPath/sphinx/bin
	fi
	
	if [ -d $serverPath/sphinx ];then
		echo "${VERSION}" > $serverPath/sphinx/version.pl
		echo '安装Sphinx完成'
		cd ${rootPath} && python3 ${rootPath}/plugins/sphinx/index.py start

		if [ $sysName != 'Darwin' ]; then
			cd ${rootPath} && python3 ${rootPath}/plugins/sphinx/index.py initd_install
		fi
	fi

	if [ -d ${SPHINX_DIR}/sphinx-${VERSION} ];then
		rm -rf ${SPHINX_DIR}/sphinx-${VERSION}
	fi
}

Uninstall_sphinx()
{
	if [ -f /usr/lib/systemd/system/sphinx.service ] || [ -f /lib/systemd/system/sphinx.service ];then
		systemctl stop sphinx
		systemctl disable sphinx

		if [ -f /usr/lib/systemd/system/sphinx.service ];then
			rm -rf /usr/lib/systemd/system/sphinx.service
		fi

		if [ -f /lib/systemd/system/sphinx.service ];then
			rm -rf /lib/systemd/system/sphinx.service
		fi
		systemctl daemon-reload
	fi

	if [ -f $serverPath/sphinx/initd/sphinx ];then
		$serverPath/sphinx/initd/sphinx stop
	fi

	if [ -d $serverPath/sphinx ];then
		echo "rm -rf $serverPath/sphinx"
		rm -rf $serverPath/sphinx
	fi

	echo "卸载sphinx成功"
}

action=$1
case "$action" in
    install)
        if [ "$VERSION" = 3.9.1 ]; then Install_current_sphinx; else Install_sphinx; fi
        ;;
    uninstall) Uninstall_sphinx ;;
    *) exit 1 ;;
esac
