#!/bin/sh

CONF="{$SERVER_PATH}/mongodb/mongodb.conf"
EXEC="{$SERVER_PATH}/mongodb/bin/mongod"
PIDFILE=${PMPANEL_MONGODB_PIDFILE:-"{$SERVER_PATH}/mongodb/mongodb.pid"}

app_running()
{
    [ -r "$PIDFILE" ] || return 1
    read -r pid < "$PIDFILE"
    case "$pid" in
        ''|*[!0-9]*) return 1 ;;
    esac
    ps -p "$pid" -o command= | grep -Fxq -- "$EXEC -f $CONF"
}

app_start()
{
    app_running && return 0
    "$EXEC" -f "$CONF" >> "{$SERVER_PATH}/mongodb/logs.pl" 2>&1 </dev/null &
    launcher=$!
    count=0
    while [ "$count" -lt 100 ]; do
        app_running && return 0
        kill -0 "$launcher" 2>/dev/null || break
        sleep 0.2
        count=$((count + 1))
    done
    echo 'MongoDB 启动失败，请查看 MongoDB 日志。' >&2
    return 1
}

app_stop()
{
    if ! app_running; then
        return 0
    fi
    kill -TERM "$pid" || return 1
    count=0
    while [ "$count" -lt 100 ]; do
        app_running || return 0
        sleep 0.2
        count=$((count + 1))
    done
    echo 'MongoDB 停止超时。' >&2
    return 1
}

case "$1" in
    start) app_start ;;
    stop) app_stop ;;
    restart|reload) app_stop && app_start ;;
    status) app_running ;;
    *) exit 1 ;;
esac
