#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin:/opt/homebrew/bin
export PATH

# cd /Users/dev/Desktop/pmdev/server/pmpanel/plugins/openresty && bash install.sh install 1.31
# cd /www/server/pmpanel/plugins/openresty && bash install.sh install 1.31

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

sysName=`uname`
action=$1
type=$2

VERSION=1.31.9.1

openrestyDir=${serverPath}/source/openresty

Install_openresty()
{
	if [ "${action}" = "install" ];then
		if [ -d $serverPath/openresty ];then
			exit 0
		fi
	fi
	
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

	if [ "$cpuCore" -gt "2" ];then
		cpuCore=`echo "$cpuCore" | awk '{printf("%.f",($1)*0.8)}'`
	else
		cpuCore="1"
	fi
	# ----- cpu end ------

	mkdir -p ${openrestyDir}
	echo '正在安装脚本文件...'

	# wget -O openresty-1.21.4.1.tar.gz https://openresty.org/download/openresty-1.21.4.1.tar.gz
	if [ ! -f ${openrestyDir}/openresty-${VERSION}.tar.gz ];then
		wget --no-check-certificate -O ${openrestyDir}/openresty-${VERSION}.tar.gz https://openresty.org/download/openresty-${VERSION}.tar.gz -T 3
	fi

	DOWNLOAD_SIZE=`wc -c ${openrestyDir}/openresty-${VERSION}.tar.gz | awk '{print $1}'`
	if [ "$DOWNLOAD_SIZE" = "0" ];then
		echo 'download failed, download again'
		rm -rf ${openrestyDir}/openresty-${VERSION}.tar.gz
	fi

	# Last Download Method
	if [ ! -f ${openrestyDir}/openresty-${VERSION}.tar.gz ];then
		wget -O ${openrestyDir}/openresty-${VERSION}.tar.gz https://github.com/openresty/openresty/releases/download/v${VERSION}/openresty-${VERSION}.tar.gz -T 3
	fi

	cd ${openrestyDir} && tar -zxvf openresty-${VERSION}.tar.gz

	OPTIONS=''

	opensslVersion="4.0.3"
	libresslVersion="3.9.1"
	pcreVersion='8.45'
	if [ "$sysName" = "Darwin" ];then

		if [ ! -f ${openrestyDir}/pcre-${pcreVersion}.tar.gz ];then
			wget --no-check-certificate -O ${openrestyDir}/pcre-${pcreVersion}.tar.gz https://netix.dl.sourceforge.net/project/pcre/pcre/${pcreVersion}/pcre-${pcreVersion}.tar.gz
		fi

		if [ ! -d ${openrestyDir}/pcre-${pcreVersion} ];then
			cd ${openrestyDir} &&  tar -zxvf pcre-${pcreVersion}.tar.gz
		fi
		OPTIONS="${OPTIONS} --with-pcre=${openrestyDir}/pcre-${pcreVersion}"


		if [ ! -f ${openrestyDir}/openssl-${opensslVersion}.tar.gz ];then
	        wget --no-check-certificate -O ${openrestyDir}/openssl-${opensslVersion}.tar.gz https://www.openssl.org/source/openssl-${opensslVersion}.tar.gz -T 10
	    fi
	    # openssl.org 无法访问时从 OpenSSL 官方 GitHub 发布页下载
	    if [ ! -s ${openrestyDir}/openssl-${opensslVersion}.tar.gz ];then
	        rm -f ${openrestyDir}/openssl-${opensslVersion}.tar.gz
	        wget -O ${openrestyDir}/openssl-${opensslVersion}.tar.gz https://github.com/openssl/openssl/releases/download/openssl-${opensslVersion}/openssl-${opensslVersion}.tar.gz
	    fi

	    if [ ! -d ${openrestyDir}/openssl-${opensslVersion} ];then
			cd ${openrestyDir} &&  tar -zxvf openssl-${opensslVersion}.tar.gz
		fi
	    OPTIONS="${OPTIONS} --with-openssl=${openrestyDir}/openssl-${opensslVersion}"

		# BREW_DIR=`which brew`
		# BREW_DIR=${BREW_DIR/\/bin\/brew/}

		# brew info openssl@1.1 | grep /opt/homebrew/Cellar/openssl@1.1 | cut -d \  -f 1 | awk 'END {print}'
		# OPENSSL_LIB_DEPEND_DIR=`brew info openssl@1.1 | grep ${BREW_DIR}/Cellar/openssl@1.1 | cut -d \  -f 1 | awk 'END {print}'`
		# OPTIONS="${OPTIONS} --with-openssl=${OPENSSL_LIB_DEPEND_DIR}"
	else
		if [ ! -f ${openrestyDir}/openssl-${opensslVersion}.tar.gz ];then
	        wget --no-check-certificate -O ${openrestyDir}/openssl-${opensslVersion}.tar.gz https://www.openssl.org/source/openssl-${opensslVersion}.tar.gz -T 10
	    fi
	    # openssl.org 无法访问时从 OpenSSL 官方 GitHub 发布页下载
	    if [ ! -s ${openrestyDir}/openssl-${opensslVersion}.tar.gz ];then
	        rm -f ${openrestyDir}/openssl-${opensslVersion}.tar.gz
	        wget -O ${openrestyDir}/openssl-${opensslVersion}.tar.gz https://github.com/openssl/openssl/releases/download/openssl-${opensslVersion}/openssl-${opensslVersion}.tar.gz
	    fi

	    if [ ! -d ${openrestyDir}/openssl-${opensslVersion} ];then
			cd ${openrestyDir} &&  tar -zxvf openssl-${opensslVersion}.tar.gz
		fi
		OPTIONS="${OPTIONS} --with-openssl=${openrestyDir}/openssl-${opensslVersion}"

	fi

	if [[ "$VERSION" =~ "1.31." ]];then
		OPTIONS="${OPTIONS} --with-http_v3_module"

		# if [ ! -f ${openrestyDir}/libressl-${libresslVersion}.tar.gz ];then
	    #     wget --no-check-certificate -O ${openrestyDir}/libressl-${libresslVersion}.tar.gz https://ftp.openbsd.org/pub/OpenBSD/LibreSSL/libressl-${libresslVersion}.tar.gz
	    # fi

	    # if [ ! -d ${openrestyDir}/libressl-${libresslVersion} ];then
		# 	cd ${openrestyDir} &&  tar -zxvf libressl-${libresslVersion}.tar.gz
		# fi
	    
	    # OPTIONS="${OPTIONS} --with-cc-opt=-I${openrestyDir}/libressl-${libresslVersion}/libressl/build/include"
	    # OPTIONS="${OPTIONS} --with-cc-opt=-I${openrestyDir}/libressl-${libresslVersion}/libressl/build/lib"
	fi

	# br: 每次编译都检查并加入(旧版仅在首次下载时加入, 升级/重装后模块会丢失)
	if [ ! -f ${openrestyDir}/ngx_brotli/config ] || [ ! -f ${openrestyDir}/ngx_brotli/deps/brotli/c/include/brotli/encode.h ];then
		rm -rf ${openrestyDir}/ngx_brotli
		cd ${openrestyDir} && git clone --depth 1 https://github.com/wxx9248/ngx_brotli.git && \
			cd ${openrestyDir}/ngx_brotli && git submodule update --init --depth 1 || rm -rf ${openrestyDir}/ngx_brotli
	fi
	if [ -f ${openrestyDir}/ngx_brotli/config ] && [ -f ${openrestyDir}/ngx_brotli/deps/brotli/c/include/brotli/encode.h ];then
		OPTIONS="${OPTIONS} --add-module=${openrestyDir}/ngx_brotli"
	else
		echo "ngx_brotli 下载失败, 跳过 brotli 压缩模块"
	fi

	OPTIONS="${OPTIONS} --with-threads"
	OPTIONS="${OPTIONS} --with-pcre-jit"
	OPTIONS="${OPTIONS} --with-http_gzip_static_module"

	if [ "$sysName" != "Darwin" ];then
		OPTIONS="${OPTIONS} --with-file-aio"
	fi

	#zstd: 下载失败时跳过该模块, 不影响 OpenResty 编译
	if [ ! -f ${openrestyDir}/zstd-nginx-module-master/config ];then
		rm -rf ${openrestyDir}/zstd-nginx-module-master ${openrestyDir}/zstd-nginx-module.tar.gz
		cd ${openrestyDir} && wget -O $openrestyDir/zstd-nginx-module.tar.gz https://github.com/tokers/zstd-nginx-module/archive/refs/heads/master.tar.gz && \
			tar -zxf zstd-nginx-module.tar.gz
		if [ ! -f ${openrestyDir}/zstd-nginx-module-master/config ];then
			rm -rf ${openrestyDir}/zstd-nginx-module-master
			git clone --depth 1 https://github.com/tokers/zstd-nginx-module.git ${openrestyDir}/zstd-nginx-module-master || rm -rf ${openrestyDir}/zstd-nginx-module-master
		fi
	fi

	if [ "$sysName" = "Darwin" ];then
		export ZSTD_INC=/opt/homebrew/include
		export ZSTD_LIB=/opt/homebrew/lib
	fi

	if [ -f ${openrestyDir}/zstd-nginx-module-master/config ] && pkg-config --exists libzstd;then
		OPTIONS="${OPTIONS} --add-module=${openrestyDir}/zstd-nginx-module-master"
	else
		echo "zstd 模块或 libzstd 不可用, 跳过 zstd 压缩模块"
	fi
	
	

	# --with-compat: 允许单独编译的动态模块(如 ModSecurity 防火墙)加载
	cd ${openrestyDir}/openresty-${VERSION} && ./configure \
	--prefix=$serverPath/openresty \
	--with-compat \
	$OPTIONS \
	--with-stream \
	--with-http_v2_module \
	--with-http_ssl_module  \
	--with-http_slice_module \
	--with-http_stub_status_module \
	--with-http_sub_module \
	--with-http_realip_module
	# --without-luajit-gc64
	# --with-debug
	# 用于调式

	CMD_MAKE=`which gmake`
	if [ "$?" = "0" ];then
		MAKE_BIN=gmake
	else
		MAKE_BIN=make
	fi
	# 编译或安装失败时立即退出, 不再显示"安装完成"
	if ! ($MAKE_BIN -j${cpuCore} && $MAKE_BIN install); then
		echo 'ERROR: OpenResty 编译失败, 请查看上面的错误信息'
		exit 1
	fi
	$MAKE_BIN clean


    if [ -d ${openrestyDir}/pcre-${pcreVersion} ];then
    	rm -rf ${openrestyDir}/pcre-${pcreVersion}
    fi

    if [ -d ${openrestyDir}/openssl-${opensslVersion} ];then
    	rm -rf ${openrestyDir}/openssl-${opensslVersion}
    fi

    if [ -d ${openrestyDir}/libressl-${libresslVersion} ];then
    	rm -rf ${openrestyDir}/libressl-${libresslVersion}
    fi

    if [ -d $openrestyDir/openresty-${VERSION} ];then
		rm -rf $openrestyDir/openresty-${VERSION}
	fi

	# if [ -d $openrestyDir/zstd-nginx-module-master ];then
	# 	rm -rf $openrestyDir/zstd-nginx-module-master
	# fi

	# if [ -d $openrestyDir/ngx_brotli ];then
	# 	rm -rf $openrestyDir/ngx_brotli
	# fi
	if [ ! -f $serverPath/openresty/nginx/sbin/nginx ];then
		echo 'ERROR: 未找到 OpenResty 程序, 安装失败'
		exit 1
	fi
	echo 'Installation of Openresty completed'
}

Uninstall_openresty()
{
	echo 'Uninstalling Openresty completed'
}

action=$1
if [ "${1}" = "install" ];then
	Install_openresty
elif [ "${1}" = "upgrade" ];then
	Install_openresty
else
	Uninstall_openresty
fi
