[Unit]
Description=Keepalived
After=network.target

[Service]
Type=simple
ExecStart={$SERVER_PATH}/keepalived/sbin/keepalived --dont-fork --log-console
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure

[Install]
WantedBy=multi-user.target
