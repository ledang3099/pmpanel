#!/usr/bin/env bash

case "$1" in
    install)
        source ../../scripts/tools/zabbix-8-apt.sh || exit 1
        install_zabbix_8_apt zabbix-agent
        ;;
    uninstall) apt-get remove -y -- zabbix-agent ;;
    *) exit 1 ;;
esac
