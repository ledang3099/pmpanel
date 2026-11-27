#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

if [ -f ${rootPath}/bin/activate ];then
	. ${rootPath}/bin/activate
fi


GOGS_DOWNLOAD='https://dl.gogs.io'

getOs(){
	os=`uname`
	if [ "Darwin" = "$os" ];then
		echo 'darwin'
	else
		echo 'linux'
	fi
	return 0
}

getBit(){
	echo `getconf  LONG_BIT`
}


Install_gogs()
{
	
	mkdir -p $serverPath/source/gogs

	echo '正在安装脚本文件...'
	version=$1
	os=`getOs`

	# if id git &> /dev/null ;then 
	#     echo "git uid is `id -u git`"
	#     echo "git shell is `grep "^git:" /etc/passwd |cut -d':' -f7 `"
	# else
	#     groupadd git
	# 	useradd -g git git
	# fi

	git config --global push.default simple

	if [ "darwin" = "$os" ];then
		file=gogs_${version}_darwin_amd64.zip
	else
		file=gogs_${version}_linux_amd64.zip
	fi

	if [ "$version" = 0.14.4 ]; then
		architecture=$(uname -m)
		case "$architecture" in
			x86_64) architecture=amd64 ;;
			arm64|aarch64) architecture=arm64 ;;
			*) echo "Unsupported Gogs architecture: $architecture" >&2; return 1 ;;
		esac
		file="gogs_v${version}_${os}_${architecture}.zip"
		url="https://github.com/gogs/gogs/releases/download/v${version}/${file}"
	else
		url="${GOGS_DOWNLOAD}/${version}/${file}"
	fi
    sources="$serverPath/source/gogs"
    archive="$sources/$file"
    if [ "$version" = 0.14.4 ]; then
        case "$os-$architecture" in
            linux-amd64) digest=98c38c2b0f4ec9a48700504098461a0bdbc382b359c02e8f28a5393a2a26f1cd ;;
            linux-arm64) digest=21680249845bf638897af428102a699ab0cc1202ac347ff436466737582971bd ;;
            darwin-amd64) digest=4c15424d8421ec48f2d8eec8f2e658607b806b1040446924b2116dc4ee476e90 ;;
            darwin-arm64) digest=1c20741a6442dc6dc0f2dfa45fa7956ac60994bf41873aecca1dca36754be57c ;;
        esac
        source "$rootPath/scripts/tools/verified-download.sh" || return 1
        verified_download "$url" "$archive" "$digest" || return 1
    elif [ ! -f "$archive" ]; then
        curl -fsSL --retry 2 "$url" -o "$archive.part" && mv -- "$archive.part" "$archive" || return 1
    fi

    if [ ! -e "$serverPath/gogs" ]; then
        staging=$(mktemp -d "$sources/install.XXXXXX") || return 1
        trap 'rm -rf -- "$staging"' EXIT
        unzip -q "$archive" -d "$staging" || return 1
        test -x "$staging/gogs/gogs" || return 1
        mv -- "$staging/gogs" "$serverPath/gogs" || return 1
        printf '%s\n' "$version" > "$serverPath/gogs/version.pl" || return 1
    elif [ "$(cat "$serverPath/gogs/version.pl" 2>/dev/null)" != "$version" ]; then
        echo '检测到已安装的 Gogs。请备份数据库和配置后按上游文档升级。' >&2
        return 1
    fi

    cd "$rootPath" || return 1
    [ "$(python3 plugins/gogs/index.py start)" = ok ] || return 1
    if [ "$os" != darwin ]; then
        [ "$(python3 plugins/gogs/index.py initd_install)" = ok ] || return 1
    fi

	echo 'install success'
}

Uninstall_gogs()
{

	if [ -f /usr/lib/systemd/system/gogs.service ];then
		systemctl stop gogs
		systemctl disable gogs
		rm -rf /usr/lib/systemd/system/gogs.service
		systemctl daemon-reload
	fi

	if [ -f $serverPath/gogs/initd/gogs ];then
		$serverPath/gogs/initd/gogs stop
	fi

	rm -rf $serverPath/gogs
	echo 'uninstall success'
}


action=$1
version=$2
if [ "${1}" = 'install' ];then
	Install_gogs $version
else
	Uninstall_gogs $version
fi
