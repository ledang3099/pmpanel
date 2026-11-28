#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin:/opt/homebrew/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

# cd /www/server/pmpanel/plugins/lam && bash install.sh install 9.0
# cd /www/server/pmpanel && python3 plugins/lam/index.py start

if [ -f ${rootPath}/bin/activate ];then
	. ${rootPath}/bin/activate
fi

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

Prepare_PHP()
{
    local selected digits php_version php_bin service
    selected=$(cat "$serverPath/lam/php.pl") || return 1
    case "$selected" in
        apt[0-9].[0-9]|[0-9][0-9]-apt)
            if [[ "$selected" == apt* ]]; then
                php_version=${selected#apt}
            else
                php_version="${selected:0:1}.${selected:1:1}"
            fi
            php_bin="/usr/bin/php$php_version"
            service="php$php_version-fpm"
            if "$php_bin" -r 'exit(extension_loaded("gmp") && extension_loaded("ldap") ? 0 : 1);'; then
                return 0
            fi
            apt-get install -y "php$php_version-gmp" "php$php_version-ldap" || return 1
            ;;
        yum[0-9][0-9]|[0-9][0-9]-yum)
            digits=${selected#yum}
            digits=${digits%-yum}
            php_bin="/opt/remi/php$digits/root/usr/bin/php"
            service="php$digits-php-fpm"
            if "$php_bin" -r 'exit(extension_loaded("gmp") && extension_loaded("ldap") ? 0 : 1);'; then
                return 0
            fi
            yum install -y "php$digits-php-gmp" "php$digits-php-ldap" || return 1
            ;;
        [0-9][0-9])
            php_bin="$serverPath/php/$selected/bin/php"
            if "$php_bin" -r 'exit(extension_loaded("gmp") && extension_loaded("ldap") ? 0 : 1);'; then
                return 0
            fi
            echo "请先在面板的 PHP-$selected 设置中安装 GMP 和 LDAP 扩展。" >&2
            return 1
            ;;
        *)
            echo "无法识别 LAM 选用的 PHP 运行时：$selected" >&2
            return 1
            ;;
    esac
    "$php_bin" -r 'exit(extension_loaded("gmp") && extension_loaded("ldap") ? 0 : 1);' &&
        systemctl restart "$service"
}

Start_App()
{
    local requested=$1 installed result
    cd "$rootPath" || return 1
    result=$(python3 plugins/lam/index.py start) || return 1
    if [ "$result" != ok ]; then
        printf '%s\n' "$result" >&2
        return 1
    fi
    installed=$(python3 plugins/lam/index.py deployed_version) || return 1
    if [ "$installed" != "$requested" ]; then
        echo "检测到 LDAP Account Manager $installed。请按上游说明准备并备份现有配置，再迁移到 $requested。" >&2
        return 1
    fi
    Prepare_PHP || return 1
    printf '%s\n' "$installed" > "$serverPath/lam/version.pl"
}

Install_App()
{
    local requested=$1 installed='' archive staging digest
    case "$requested" in
        9.0) digest=d7d57259338efc6e6c6e6578d87098eb4c1c2b83aab8de1db9a698eaf62132cf ;;
        9.7) digest=b3535f91afa09ba49f59d8a7fdfbb0a4f5aae2b9ed17aac7b8bfae36e834d9e0 ;;
        *) return 1 ;;
    esac
    if [ -d "$serverPath/lam" ]; then
        if [ -f "$serverPath/lam/cfg.json" ]; then
            installed=$(cd "$rootPath" && python3 plugins/lam/index.py deployed_version) || return 1
        fi
        if [ "$installed:$requested" != 9.0:9.7 ]; then
            Start_App "$requested"
            return $?
        fi
        Prepare_PHP || return 1
    fi

    archive="$serverPath/source/lam/ldap-account-manager-$requested.tar.bz2"
    mkdir -p "$(dirname "$archive")" || return 1
    source "$rootPath/scripts/tools/verified-download.sh" || return 1
    verified_download "https://github.com/LDAPAccountManager/lam/releases/download/$requested/${archive##*/}" "$archive" "$digest" || return 1

    staging=$(mktemp -d "$serverPath/source/lam/install.XXXXXX") || return 1
    trap "rm -rf -- $(printf '%q' "$staging")" EXIT
    tar -xjf "$archive" -C "$staging" || return 1
    local app="$staging/ldap-account-manager-$requested"
    if [ "$installed:$requested" = 9.0:9.7 ]; then
        cd "$rootPath" || return 1
        python3 plugins/lam/index.py upgrade_app "$app" || return 1
    else
        mkdir -p "$serverPath/lam" && mv "$app" "$serverPath/lam/lam" || return 1
        Start_App "$requested" || return 1
    fi
    echo '安装完成'
}

Uninstall_App()
{
	cd ${rootPath} && python3 ${rootPath}/plugins/lam/index.py stop
	
	rm -rf ${serverPath}/lam
	echo '卸载完成'
}

case "$1" in
    install) Install_App "$2" ;;
    upgrade)
        case "$2" in 9.0|9.7) Install_App 9.7 ;; *) exit 1 ;; esac
        ;;
    uninstall) Uninstall_App ;;
    *) exit 1 ;;
esac
