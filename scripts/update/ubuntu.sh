#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin:/opt/homebrew/bin
export PATH
export LANG=en_US.UTF-8
export DEBIAN_FRONTEND=noninteractive

# localedef -v -c -i en_US -f UTF-8 en_US.UTF-8

if grep -Eq "Ubuntu" /etc/*-release; then
    sudo ln -sf /bin/bash /bin/sh
    #sudo dpkg-reconfigure dash
fi


cd /www/server/pmpanel/scripts && bash lib.sh
chmod 755 /www/server/pmpanel/data


if [ -f /etc/rc.d/init.d/pm ];then
    if [ -f /usr/bin/pm ];then
        rm -rf /usr/bin/pm
    fi
    bash /etc/rc.d/init.d/pm stop && rm -rf /www/server/pmpanel/scripts/init.d/pm && rm -rf /etc/rc.d/init.d/pm
fi

echo -e "stop pm"
isStart=`ps -ef|grep 'gunicorn -c setting.py app:app' |grep -v grep|awk '{print $2}'`
port=7200

if [ -f /www/server/pmpanel/data/port.pl ];then
    port=$(cat /www/server/pmpanel/data/port.pl)
fi
n=0
while [[ "$isStart" != "" ]];
do
    echo -e ".\c"
    sleep 0.5
    isStart=$(lsof -n -P -i:$port|grep LISTEN|grep -v grep|awk '{print $2}'|xargs)
    let n+=1
    if [ $n -gt 15 ];then
        break;
    fi
done


echo -e "start pm"
cd /www/server/pmpanel && bash cli.sh start
isStart=`ps -ef|grep 'gunicorn -c setting.py app:app' |grep -v grep|awk '{print $2}'`
n=0
while [[ ! -f /etc/rc.d/init.d/pm ]];
do
    echo -e ".\c"
    sleep 1
    let n+=1
    if [ $n -gt 20 ];then
        echo -e "start pm fail"
        exit 1
    fi
done
echo -e "start pm success"

systemctl daemon-reload
