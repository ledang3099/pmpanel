#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

# cd /www/server/pmpanel/plugins/gitea && bash install.sh upgrade 1.25.3

action=$1
version=$2

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

if [ -f ${rootPath}/bin/activate ];then
	. ${rootPath}/bin/activate
fi



URL_DOWNLOAD=https://dl.gitea.com


bash ${rootPath}/scripts/getos.sh
OSNAME=`cat ${rootPath}/data/osname.pl`
OSNAME_ID=`cat /etc/*-release | grep VERSION_ID | awk -F = '{print $2}' | awk -F "\"" '{print $2}'`


getBit(){
	echo `getconf  LONG_BIT`
}

Install_Rsync(){
	if [ "$OSNAME" = "debian" ] || [ "$OSNAME" = "ubuntu" ];then
		apt install -y rsync
	elif [[ "$OSNAME" = "arch" ]]; then
		echo y | pacman -Sy rsync
	elif [[ "$OSNAME" = "macos" ]]; then
		# brew install rsync
		# brew install lsyncd
		echo "ok"
	else
		yum install -y rsync
	fi
}


Install_App()
{
	Install_Rsync

	mkdir -p $serverPath/source/gitea

	if id www &> /dev/null ;then 
	    echo "www uid is `id -u www`"
	    echo "www shell is `grep "^www:" /etc/passwd |cut -d':' -f7 `"
	else
	    groupadd www
		useradd -g www www
	fi

	if [ "macos" != "$OSNAME" ];then
		if [ ! -d /home/www ];then
			mkdir -p /home/www
			chown -R www:www /home/www
		fi
	fi

	echo '正在安装脚本文件...'
	version=$1
	

	git config --global push.default simple

	if [ "$version" = 28.4.0 ]; then
        case "$(uname -m)" in
            x86_64) architecture=amd64 ;;
            arm64|aarch64) architecture=arm64 ;;
            *) echo "Unsupported Gitea architecture" >&2; return 1 ;;
        esac
        platform=linux
        if [ "$OSNAME" = macos ]; then platform=darwin; fi
        file="gitea-${version}-${platform}-${architecture}"
    elif [ "macos" = "$OSNAME" ];then
		file=gitea-${version}-darwin-10.12-amd64
	else
		file=gitea-${version}-linux-amd64
	fi

    archive="$serverPath/source/gitea/$file.xz"
    url="$URL_DOWNLOAD/gitea/$version/$file.xz"
    if [ "$version" = 28.4.0 ]; then
        case "$platform-$architecture" in
            linux-amd64) digest=0b60b8efd1c7d948d927ef29e849d7263eb000c3cb2ae5d4303e3ecbdeaaa237 ;;
            linux-arm64) digest=b33a221b9d970a262fc71bbb6e993ad5c4549ed597f078c04ea2112900280a0c ;;
            darwin-amd64) digest=976a3f7636e0dae5a17123adaa5a100fe72d15e1f942ca4f0d3fd297a44bfb2c ;;
            darwin-arm64) digest=5556974ede49e173940a80a5db966d33487655d888fa7c90a1def61c55fc44a8 ;;
        esac
        source "$rootPath/scripts/tools/verified-download.sh" || return 1
        verified_download "$url" "$archive" "$digest" || return 1
    elif [ ! -f "$archive" ]; then
        curl -fsSL --retry 2 "$url" -o "$archive.part" && mv -- "$archive.part" "$archive" || return 1
    fi

    mkdir -p "$serverPath/gitea" || return 1
    binary=$(mktemp "$serverPath/gitea/.gitea.XXXXXX") || return 1
    trap 'unlink "$binary" 2>/dev/null || true' EXIT
    xz -dc "$archive" > "$binary" && chmod 0755 "$binary" || return 1
    chown www:www "$binary" && mv -f -- "$binary" "$serverPath/gitea/gitea" || return 1
    chown -R www:www "$serverPath/gitea" || return 1

	if [ -d $serverPath/gitea ] && [ "${action}" = 'install' ] ;then
		cd ${rootPath} && python3 plugins/gitea/index.py start
		cd ${rootPath} && python3 plugins/gitea/index.py initd_install
	fi

	echo $version > $serverPath/gitea/version.pl
	echo 'install success'

	if [ "$action" = "upgrade" ];then
		which systemctl && systemctl restart gitea
	fi
}

Uninstall_App()
{
	if [ -f /usr/lib/systemd/system/gitea.service ];then
		systemctl stop gitea
		systemctl disable gitea
		rm -rf /usr/lib/systemd/system/gitea.service
		systemctl daemon-reload
	fi

	if [ -f $serverPath/gitea/initd/gitea ];then
		$serverPath/gitea/initd/gitea stop
	fi

	rm -rf $serverPath/gitea
	echo 'uninstall success'
}

if [ "${action}" = 'install' ] || [ "$action" = "upgrade" ];then
	Install_App $version
elif [ "${action}" = 'uninstall' ];then
	Uninstall_App $version
else
	echo "OPTIONS ERROR"
fi
