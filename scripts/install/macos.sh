#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin:/opt/homebrew/bin
export PATH
LANG=en_US.UTF-8

USER=$(who | sed -n "2,1p" |awk '{print $1}')
DEV="/Users/${USER}/Desktop/pmdev"


mkdir -p $DEV
mkdir -p $DEV/wwwroot
mkdir -p $DEV/server
mkdir -p $DEV/wwwlogs
mkdir -p $DEV/backup/database
mkdir -p $DEV/backup/site

# install brew
which brew
if [ "$?" != "0" ];then
	/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
	brew install python@2
	brew install mysql
fi

brew install pv
brew install libzip bzip2 gcc openssl re2c cmake
brew install librdkafka
brew install coreutils libxml2 xml2
brew install md5sum libevent pidof bison
brew install pcre2 libxpm libelf
brew install automake icu4c libmemcached

if [ ! -d $DEV/server/pmpanel ]; then
	wget -O /tmp/master.zip https://codeload.github.com/ledang3099/pmpanel/zip/master
	cd /tmp && unzip /tmp/master.zip
	mv /tmp/pmpanel-master $DEV/server/pmpanel
	rm -f /tmp/master.zip
	rm -rf /tmp/pmpanel-master
fi

if [ ! -d $DEV/server/lib ]; then
	cd $DEV/server/pmpanel/scripts && bash lib.sh
fi  

chmod 755 $DEV/server/pmpanel/data
if [ -f $DEV/server/pmpanel/bin/activate ];then
    cd $DEV/server/pmpanel && python3 -m venv $DEV/server/pmpanel
    source $DEV/server/pmpanel/bin/activate
    pip3 install -r $DEV/server/pmpanel/requirements.txt
else
	cd $DEV/server/pmpanel && pip3 install -r $DEV/server/pmpanel/requirements.txt
fi


cd $DEV/server/pmpanel && ./cli.sh start
cd $DEV/server/pmpanel && ./cli.sh stop

sleep 5
cd $DEV/server/pmpanel && ./scripts/init.d/pm default
cd $DEV/server/pmpanel && ./cli.sh debug