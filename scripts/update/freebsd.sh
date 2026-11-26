#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin:/opt/homebrew/bin
export PATH
LANG=en_US.UTF-8


cd /www/server/pmpanel/scripts && bash lib.sh
chmod 755 /www/server/pmpanel/data


if [ -f /etc/rc.d/init.d/pm ];then
    bash /etc/rc.d/init.d/pm stop && rm -rf /www/server/pmpanel/scripts/init.d/pm && rm -rf /etc/rc.d/init.d/pm
fi

echo -e "start pm"
cd /www/server/pmpanel && bash cli.sh start
isStart=`ps -aux|grep 'gunicorn -c setting.py app:app' |grep -v grep|awk '{print $2}'`
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

cd /www/server/pmpanel && bash /etc/rc.d/init.d/pm stop
cd /www/server/pmpanel && bash /etc/rc.d/init.d/pm start
