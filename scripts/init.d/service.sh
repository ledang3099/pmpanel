#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

cd /www/server/pmpanel
if [ -f bin/activate ];then
	. bin/activate
fi