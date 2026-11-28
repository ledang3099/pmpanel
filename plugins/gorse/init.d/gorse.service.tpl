[Unit]
Description=Gorse, an open source recommender system service written in Go.
After=network.target

[Service]
User=root
WorkingDirectory={$SERVER_PATH}/gorse
Type=simple
Restart=always
ExecStart={$SERVER_PATH}/gorse/bin/gorse-in-one -c {$SERVER_PATH}/gorse/gorse.toml \
    --log-path {$SERVER_PATH}/gorse/gorse.log \
    --cache-path {$CACHE_PATH}

[Install]
WantedBy=multi-user.target