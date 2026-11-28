#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin
app_file="{$SERVER_PATH}"

active()
{
    swapon --show=NAME --noheadings --raw | grep -Fxq -- "$app_file"
}

app_start()
{
    active || swapon -- "$app_file"
}

app_stop()
{
    if active; then
        swapoff -- "$app_file"
    fi
}

case "$1" in
    start) app_start ;;
    stop) app_stop ;;
    restart|reload) app_stop && app_start ;;
    status) active ;;
    *) exit 1 ;;
esac
