[Unit]
Description=OpenResty is a dynamic web platform based on NGINX and LuaJIT.
After=network.target

[Service]
Type=forking
PIDFile={$SERVER_PATH}/openresty/nginx/logs/nginx.pid
ExecStart={$SERVER_PATH}/openresty/bin/openresty -c {$SERVER_PATH}/openresty/nginx/conf/nginx.conf
ExecReload={$SERVER_PATH}/openresty/bin/openresty -s reload
KillSignal=SIGQUIT
KillMode=mixed
Restart=on-failure

[Install]
WantedBy=multi-user.target