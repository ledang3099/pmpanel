[Unit]
Description=Grafana Alloy log collector for pmpanel Loki
After=network.target loki.service

[Service]
ExecStart={$SERVER_PATH}/loki/bin/alloy run --server.http.listen-addr=127.0.0.1:12345 --storage.path={$SERVER_PATH}/loki/alloy-data {$SERVER_PATH}/loki/conf/collector.alloy
Restart=on-failure

[Install]
WantedBy=multi-user.target
