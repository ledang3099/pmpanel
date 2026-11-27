#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin:/opt/homebrew/bin
export PATH=$PATH:/opt/homebrew/bin

curPath=`pwd`

rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
rootPath=$(dirname "$rootPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")
sourcePath=${serverPath}/source/php
SYS_ARCH=`arch`
LIBNAME=xhprof
LIBV=2.3.10
sysName=`uname`
actionType=$1
version=$2

if [ "$version" -lt "70" ];then
	LIBV=0.9.4
fi

php_bin="$serverPath/php/$version/bin"
[ -x "$php_bin/php-config" ] || exit 1
extension_dir=$("$php_bin/php-config" --extension-dir) || exit 1
extFile="$extension_dir/${LIBNAME}.so"

if [ "$sysName" = "Darwin" ];then
	BAK='_bak'
else
	BAK=''
fi


Install_lib()
{
	isInstall=`cat $serverPath/php/$version/etc/php.ini|grep "${LIBNAME}.so"`
	if [ "${isInstall}" != "" ];then
		echo "php-$version 已安装${LIBNAME},请选择其它版本!"
		return
	fi
	
	if [ ! -f "$extFile" ];then
        php_lib="$sourcePath/php_lib"
        mkdir -p "$php_lib" || return 1
        archive="$php_lib/$LIBNAME-$LIBV.tgz"
        if [ "$LIBV" = 2.3.10 ]; then
            source "$rootPath/scripts/tools/verified-download.sh" || return 1
            verified_download "https://pecl.php.net/get/$LIBNAME-$LIBV.tgz" "$archive" \
                251aee99c2726ebc6126e1ff0bb2db6e2d5fd22056aa335e84db9f1055d59d95 || return 1
        elif [ ! -f "$archive" ]; then
            curl -fsSL "https://pecl.php.net/get/$LIBNAME-$LIBV.tgz" -o "$archive" || return 1
        fi
        staging=$(mktemp -d "$php_lib/xhprof-build.XXXXXX") || return 1
        trap 'rm -rf -- "$staging"' EXIT
        tar -xzf "$archive" -C "$staging" || return 1
        cd "$staging/$LIBNAME-$LIBV/extension" || return 1

		OPTIONS=''
		if [ "${SYS_ARCH}" = "aarch64" ] && [ "$version" -lt "56" ];then
			OPTIONS="$OPTIONS --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu"
		fi

        "$php_bin/phpize" || return 1
        ./configure --enable-xhprof --with-php-config="$php_bin/php-config" $OPTIONS || return 1
        make && make install || return 1

	fi
	
	if [ ! -f "$extFile" ];then
		echo "ERROR!"
		return 1
	fi

	if [ ! -d /tmp/xhprof ]; then
        install -d -m 0700 -o www -g www /tmp/xhprof || return 1
    fi

	echo "" >> $serverPath/php/$version/etc/php.ini
	echo "[${LIBNAME}]" >> $serverPath/php/$version/etc/php.ini
	echo "extension=${LIBNAME}.so" >> $serverPath/php/$version/etc/php.ini
	echo "${LIBNAME}.output_dir=/tmp/xhprof" >> $serverPath/php/$version/etc/php.ini

	cd  ${curPath} && bash ${rootPath}/plugins/php/versions/lib.sh $version restart
	echo '==========================================================='
	echo 'successful!'
}


Uninstall_lib()
{
	if [ ! -f "$serverPath/php/$version/bin/php-config" ];then
		echo "php-$version 未安装,请选择其它版本!"
		return
	fi
	
	if [ ! -f "$extFile" ];then
		echo "php-$version 未安装${LIBNAME},请选择其它版本!"
		echo "php-$version not install ${LIBNAME}, Plese select other version!"
		return
	fi
	
	sed -i $BAK "/${LIBNAME}.so/d" $serverPath/php/$version/etc/php.ini
	sed -i $BAK "/${LIBNAME}/d" $serverPath/php/$version/etc/php.ini
		
	rm -f $extFile
	cd  ${curPath} && bash ${rootPath}/plugins/php/versions/lib.sh $version restart
	echo '==============================================='
	echo 'successful!'
}


if [ "$actionType" = 'install' ];then
	Install_lib
elif [ "$actionType" = 'uninstall' ];then
	Uninstall_lib
fi