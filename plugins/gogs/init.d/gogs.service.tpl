[Unit]
Description=Gogs
After=network.target

[Service]
User=root
WorkingDirectory={$SERVER_PATH}/gogs
ExecStart={$SERVER_PATH}/gogs/gogs web

[Install]
WantedBy=multi-user.target
