#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

# cd /www/server/pmpanel/plugins/docker && /bin/bash install.sh uninstall 1.0
# cd /www/server/pmpanel/plugins/docker && /bin/bash install.sh install 1.0

VERSION=$2

if [ -f ${rootPath}/bin/activate ];then
	. ${rootPath}/bin/activate
fi

# {
#     "registry-mirrors": [
#         "http://hub-mirror.c.163.com",
#         "https://docker.mirrors.ustc.edu.cn",
#         "https://registry.docker-cn.com"
#     ]
# }

# sudo mkdir -p /etc/docker
# sudo tee /etc/docker/daemon.json <<-'EOF'
# {
#     "registry-mirrors": [
#         "http://hub-mirror.c.163.com",
#         "https://docker.mirrors.ustc.edu.cn",
#         "https://registry.docker-cn.com"
#     ]
# }
# EOF
# sudo systemctl daemon-reload
# sudo systemctl restart docker

Install_Docker()
{
    if ! command -v docker >/dev/null || ! command -v dockerd >/dev/null; then
        if [ -f /etc/os-release ]; then source /etc/os-release; fi
        case "$ID" in
            debian|ubuntu)
                apt-get install -y ca-certificates curl || return 1
                install -d -m 0755 /etc/apt/keyrings || return 1
                curl --proto '=https' --proto-redir '=https' -fsSL "https://download.docker.com/linux/$ID/gpg" \
                    -o /etc/apt/keyrings/docker.asc.new || return 1
                chmod 0644 /etc/apt/keyrings/docker.asc.new || return 1
                mv -f /etc/apt/keyrings/docker.asc.new /etc/apt/keyrings/docker.asc || return 1
                if [ ! -f /etc/apt/sources.list.d/docker.list ] && [ ! -f /etc/apt/sources.list.d/docker.sources ]; then
                    codename=${UBUNTU_CODENAME:-$VERSION_CODENAME}
                    arch=$(dpkg --print-architecture) || return 1
                    if [ -z "$codename" ]; then return 1; fi
                    printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/%s %s stable\n' \
                        "$arch" "$ID" "$codename" > /etc/apt/sources.list.d/docker.list || return 1
                fi
                apt-get update || return 1
                apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin || return 1
                ;;
            *)
                installer=$(mktemp) || return 1
                trap 'unlink "$installer"' EXIT
                curl --proto '=https' --proto-redir '=https' -fsSL https://get.docker.com -o "$installer" &&
                    bash "$installer" || return 1
                ;;
        esac
    fi

    python3 -m pip install --upgrade docker pytz || return 1
    systemctl enable --now docker || return 1
    docker version --format '{{.Server.Version}}' || return 1
    mkdir -p "$serverPath/docker" || return 1
    printf '%s\n' "$VERSION" > "$serverPath/docker/version.pl" || return 1
    echo '安装Docker完成'
}

Uninstall_Docker()
{
	CMD=yum
	which apt
	if [ "$?" = "0" ];then
		CMD=apt
	fi

	if [ -f /usr/lib/systemd/system/docker.service ];then
		systemctl stop docker
		systemctl disable docker
		rm -rf /usr/lib/systemd/system/docker.service
		systemctl daemon-reload
	fi

	$CMD remove -y docker docker-ce-cli containerd.io
	# docker-client \
	# docker-client-latest \
	# docker-common \
	# docker-latest \
	# docker-latest-logrotate \
	# docker-logrotate \
	# docker-selinux \
	# docker-engine-selinux \
	# docker-engine \
	# docker-ce

	rm -rf $serverPath/docker
	echo "卸载Docker"
}

action=$1
if [ "${1}" = 'install' ];then
	Install_Docker
else
	Uninstall_Docker
fi
