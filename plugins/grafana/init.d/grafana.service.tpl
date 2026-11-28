[Unit]
Description=Grafana instance
Documentation=http://docs.grafana.org
After=network-online.target
[Service]
Type=simple
User=grafana
Group=grafana
Restart=on-failure
WorkingDirectory={$SERVER_PATH}/grafana
ExecStart={$SERVER_PATH}/grafana/bin/grafana server --homepath={$SERVER_PATH}/grafana

[Install]
WantedBy=multi-user.target