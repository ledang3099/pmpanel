#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

# ModSecurity 防火墙: libmodsecurity + ModSecurity-nginx 动态模块 + OWASP CRS
# cd /www/server/pmpanel/plugins/modsecurity && bash install.sh install 3.0
# cd /www/server/pmpanel/plugins/modsecurity && bash install.sh rebuild_module

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")
sysName=`uname`

# 固定版本与校验值(哈希已与官方发布的 .sha256 / Git 标签核对)
MODSEC_VERSION=3.0.17
MODSEC_SHA256=f283b33d5c21130fd3a15c84a93a1abe12bd1949edaf44288b12af571b671a50
CONNECTOR_VERSION=1.0.4
CONNECTOR_COMMIT=3f4b57df10ce43b1f1c722141f7621dc64838be8
CRS_VERSION=4.31.0
CRS_SHA256=70e8c32ea5b57962a9081c74b738a498dcd299b1fc32099de6444b8ca5cdd8f5
# OpenResty 源码包的已知校验值(用于编译模块时提取对应版本的 nginx 源码)
declare -A OR_SHA256
OR_SHA256["1.31.9.1"]=71d49935bdc186dafc1f4b0a8ba44dba1bf4abc8ca52d4621f2039ec8fdcc95f

APP_DIR=$serverPath/modsecurity
SRC_DIR=$serverPath/source/modsecurity
OR_SRC=$serverPath/source/openresty

bash ${rootPath}/scripts/getos.sh
OSNAME=`cat ${rootPath}/data/osname.pl`
if [ -f ${rootPath}/bin/activate ];then
	. ${rootPath}/bin/activate
fi

cpuCore=$(nproc 2>/dev/null || echo 2)

checkSha256()
{
	local file=$1 expect=$2
	local got=$(sha256sum "$file" | awk '{print $1}')
	if [ "$got" != "$expect" ];then
		echo "校验失败: $file ($got)"
		rm -f "$file"
		return 1
	fi
	return 0
}

Install_Deps()
{
	if [ "$OSNAME" = "debian" ] || [ "$OSNAME" = "ubuntu" ];then
		apt install -y g++ make libtool autoconf automake pkg-config git wget \
			libpcre2-dev libxml2-dev libyajl-dev libcurl4-openssl-dev liblmdb-dev libmaxminddb-dev libssl-dev zlib1g-dev
	elif [ "$OSNAME" = "opensuse" ]; then
		zypper install -y gcc-c++ make libtool autoconf automake pkg-config git wget \
			pcre2-devel libxml2-devel libyajl-devel libcurl-devel lmdb-devel libmaxminddb-devel libopenssl-devel zlib-devel
	elif [ "$OSNAME" = "arch" ]; then
		echo y | pacman -Sy gcc make libtool autoconf automake pkgconf git wget pcre2 libxml2 yajl curl lmdb libmaxminddb openssl zlib
	else
		yum install -y epel-release
		yum install -y gcc-c++ make libtool autoconf automake pkgconfig git wget \
			pcre2-devel libxml2-devel yajl-devel libcurl-devel lmdb-devel libmaxminddb-devel openssl-devel zlib-devel
	fi
}

Build_Libmodsecurity()
{
	mkdir -p $SRC_DIR
	local tgz=$SRC_DIR/modsecurity-v${MODSEC_VERSION}.tar.gz
	if [ ! -f $tgz ];then
		wget -O $tgz https://github.com/owasp-modsecurity/ModSecurity/releases/download/v${MODSEC_VERSION}/modsecurity-v${MODSEC_VERSION}.tar.gz || return 1
	fi
	checkSha256 $tgz $MODSEC_SHA256 || return 1

	rm -rf $SRC_DIR/modsecurity-v${MODSEC_VERSION}
	cd $SRC_DIR && tar -zxf $tgz || return 1
	cd $SRC_DIR/modsecurity-v${MODSEC_VERSION} || return 1
	./configure --prefix=$APP_DIR/libmodsecurity --with-pcre2 --without-lua --disable-doxygen-doc --disable-examples || return 1
	make -j${cpuCore} && make install || return 1

	mkdir -p $APP_DIR/conf
	cp -f unicode.mapping $APP_DIR/conf/unicode.mapping
	echo "${MODSEC_VERSION}" > $APP_DIR/libmodsecurity.pl
	cd $curPath
	rm -rf $SRC_DIR/modsecurity-v${MODSEC_VERSION}
	return 0
}

Get_Connector()
{
	mkdir -p $SRC_DIR
	local dir=$SRC_DIR/ModSecurity-nginx-${CONNECTOR_VERSION}
	if [ -d $dir ] && [ "$(git -C $dir rev-parse HEAD 2>/dev/null)" = "$CONNECTOR_COMMIT" ];then
		return 0
	fi
	rm -rf $dir
	git clone -q --depth 1 --branch v${CONNECTOR_VERSION} https://github.com/owasp-modsecurity/ModSecurity-nginx $dir || return 1
	if [ "$(git -C $dir rev-parse HEAD)" != "$CONNECTOR_COMMIT" ];then
		echo "ModSecurity-nginx 源码校验失败"
		rm -rf $dir
		return 1
	fi
	return 0
}

# 按当前 OpenResty 版本编译 ModSecurity 动态模块(OpenResty 需带 --with-compat)
Build_Module()
{
	local or_bin=$serverPath/openresty/nginx/sbin/nginx
	if [ ! -f $or_bin ];then
		echo "未安装 OpenResty"
		return 1
	fi
	local info=$($or_bin -V 2>&1)
	if ! echo "$info" | grep -q -- '--with-compat';then
		echo "OpenResty 未启用 --with-compat, 请先升级/重装 OpenResty"
		return 1
	fi
	local or_ver=$(echo "$info" | grep -o 'openresty/[0-9.]*' | head -1 | cut -d/ -f2)
	echo "OpenResty 版本: $or_ver"

	Get_Connector || return 1

	mkdir -p $OR_SRC
	local tgz=$OR_SRC/openresty-${or_ver}.tar.gz
	if [ ! -s $tgz ];then
		rm -f $tgz
		wget -O $tgz https://openresty.org/download/openresty-${or_ver}.tar.gz -T 10 || rm -f $tgz
		if [ ! -s $tgz ];then
			wget -O $tgz https://github.com/openresty/openresty/releases/download/v${or_ver}/openresty-${or_ver}.tar.gz || return 1
		fi
	fi
	if [ -n "${OR_SHA256[$or_ver]}" ];then
		checkSha256 $tgz ${OR_SHA256[$or_ver]} || return 1
	fi

	local work=$SRC_DIR/build-module
	rm -rf $work && mkdir -p $work
	cd $work && tar -zxf $tgz --wildcards "openresty-${or_ver}/bundle/nginx-*" || return 1
	local ngx_dir=$(ls -d $work/openresty-${or_ver}/bundle/nginx-* | head -1)
	cd $ngx_dir || return 1

	export MODSECURITY_INC=$APP_DIR/libmodsecurity/include
	export MODSECURITY_LIB=$APP_DIR/libmodsecurity/lib
	./configure --with-compat --add-dynamic-module=$SRC_DIR/ModSecurity-nginx-${CONNECTOR_VERSION} \
		--with-ld-opt="-Wl,-rpath,$APP_DIR/libmodsecurity/lib" || return 1
	make modules -j${cpuCore} || return 1

	mkdir -p $serverPath/openresty/nginx/modules
	cp -f objs/ngx_http_modsecurity_module.so $serverPath/openresty/nginx/modules/ngx_http_modsecurity_module.so
	echo "${CONNECTOR_VERSION}" > $APP_DIR/connector.pl
	echo "${or_ver}" > $APP_DIR/module_for.pl
	cd $curPath
	rm -rf $work
	return 0
}

Install_CRS()
{
	mkdir -p $SRC_DIR
	local tgz=$SRC_DIR/coreruleset-${CRS_VERSION}-minimal.tar.gz
	if [ ! -f $tgz ];then
		wget -O $tgz https://github.com/coreruleset/coreruleset/releases/download/v${CRS_VERSION}/coreruleset-${CRS_VERSION}-minimal.tar.gz || return 1
	fi
	checkSha256 $tgz $CRS_SHA256 || return 1

	rm -rf $SRC_DIR/coreruleset-${CRS_VERSION}
	cd $SRC_DIR && tar -zxf $tgz || return 1
	rm -rf $APP_DIR/crs.new
	cp -r $SRC_DIR/coreruleset-${CRS_VERSION} $APP_DIR/crs.new || return 1
	cp -f $APP_DIR/crs.new/crs-setup.conf.example $APP_DIR/crs.new/crs-setup.conf
	rm -rf $APP_DIR/crs.old
	[ -d $APP_DIR/crs ] && mv $APP_DIR/crs $APP_DIR/crs.old
	mv $APP_DIR/crs.new $APP_DIR/crs
	rm -rf $APP_DIR/crs.old $SRC_DIR/coreruleset-${CRS_VERSION}
	echo "${CRS_VERSION}" > $APP_DIR/crs.pl
	cd $curPath
	return 0
}

Install_App()
{
	echo '正在安装依赖...'
	Install_Deps
	mkdir -p $APP_DIR/conf $APP_DIR/logs $APP_DIR/tmp

	echo "正在编译 libmodsecurity ${MODSEC_VERSION} (需要几分钟)..."
	Build_Libmodsecurity || { echo 'ERROR: libmodsecurity 编译失败'; exit 1; }

	echo "正在编译 OpenResty 防火墙模块..."
	Build_Module || { echo 'ERROR: 防火墙模块编译失败'; exit 1; }

	echo "正在安装 OWASP CRS ${CRS_VERSION} ..."
	Install_CRS || { echo 'ERROR: 规则集安装失败'; exit 1; }

	echo "${MODSEC_VERSION%.*}" > $APP_DIR/version.pl
	# 默认"仅记录"模式: 不拦截请求, 确认没有误报后再在面板中切换为"拦截"
	cd ${rootPath} && python3 ${rootPath}/plugins/modsecurity/index.py init
	echo '安装完成'
}

Rebuild_Module()
{
	if [ ! -d $APP_DIR/libmodsecurity ];then
		exit 0
	fi
	if Build_Module; then
		cd ${rootPath} && python3 ${rootPath}/plugins/modsecurity/index.py reload
		echo 'ModSecurity 防火墙模块已按新版本重新编译'
	else
		# 模块与新版 OpenResty 不兼容时先停用防火墙, 保证网站正常访问
		cd ${rootPath} && python3 ${rootPath}/plugins/modsecurity/index.py uninstall_clean
		rm -f $serverPath/openresty/nginx/modules/ngx_http_modsecurity_module.so
		echo 'WARNING: 防火墙模块重新编译失败, 已暂时停用防火墙, 请在应用市场中重新安装 ModSecurity 防火墙'
	fi
}

Uninstall_App()
{
	cd ${rootPath} && python3 ${rootPath}/plugins/modsecurity/index.py uninstall_clean
	rm -f $serverPath/openresty/nginx/modules/ngx_http_modsecurity_module.so
	rm -rf $APP_DIR $SRC_DIR
	echo '卸载完成'
}

action=$1
if [ "$action" = 'install' ] || [ "$action" = 'upgrade' ];then
	Install_App
elif [ "$action" = 'rebuild_module' ];then
	Rebuild_Module
elif [ "$action" = 'update_crs' ];then
	Install_CRS && cd ${rootPath} && python3 ${rootPath}/plugins/modsecurity/index.py reload
else
	Uninstall_App
fi
