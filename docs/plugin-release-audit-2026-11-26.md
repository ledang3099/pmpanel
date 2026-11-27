# 软件管理版本核对

核对日期为 2026-11-26，范围为 pmpanel 软件管理的 72 个插件。发行信息来自上游官方发布页、GitHub Releases 或发行版软件源。aaPanel 用于补查同类功能和依赖，例如 PHP、MySQL、Pure-FTPd、Redis 与 PHP Guardian。 [aaPanel 软件商店](https://www.aapanel.com/docs/Function/AppStore.html)

安装器的下载地址或发布元数据已经核对的变更列在表中。软件源条目的实际补丁版本取决于系统和启用的仓库。候选版本尚未完成现有配置、迁移或平台验证。

| 插件 | 结果 | 核对记录 |
| --- | --- | --- |
| `acme_pandominassl_apply` | 面板集成 | 对接 acme.sh，插件 1.0 不是 acme.sh 版本。 [上游](https://github.com/acmesh-official/acme.sh/releases) |
| `alist` | 已更新 | 3.66.0，按版本缓存并验证发布摘要，取消固定管理员密码初始化。Debian 13 安装、systemd 和 HTTP 探活通过。 [上游](https://github.com/alist-org/alist/releases/tag/v3.66.0) |
| `apache` | 已是当前 | 2.4.71。 [上游](https://downloads.apache.org/httpd/Announcement2.4.html) |
| `backup_ftp` | 面板集成 | 面板 FTP 备份任务，无独立上游版本。 |
| `caddy` | 已是当前 | 2.11.9。 [上游](https://github.com/caddyserver/caddy/releases) |
| `clean` | 面板集成 | 面板日志清理任务，无独立上游版本。 |
| `cloudreve` | 已更新 | 新增 4.19.1 全新安装，识别 V3 数据并要求先迁移。Debian 13 安装、systemd 和站点配置 API 通过。 [官方迁移说明](https://docs.cloudreve.org/zh/maintain/upgrade-from-v3) |
| `cryptocurrency_trade` | 候选待验证 | 当前安装含外部依赖与策略代码。CCXT 需单独核对 API 兼容性。 [上游](https://github.com/ccxt/ccxt/releases) |
| `data_query` | 面板集成 | 面板数据查询插件，无独立上游版本。 |
| `docker` | 软件源 | 包装 Docker 官方安装渠道，1.0 是面板插件版本。 [上游](https://docs.docker.com/engine/release-notes/) |
| `doh` | 已更新 | 新增 0.11.1，校验 Linux x86_64 和 aarch64 压缩包。Debian 13 安装与 systemd 启动通过。 [上游](https://github.com/DNSCrypt/doh-server/releases/tag/0.11.1) |
| `dynamic-tracking` | 候选待验证 | 现有安装器使用第三方代理，缺少可核对的新版来源。 |
| `dztasks` | 候选待验证 | 安装脚本引用外部 GitHub 项目，暂无已验证的替换包。 |
| `fail2ban` | 软件源 | 上游 1.1.1。面板安装的是发行版的 fail2ban 包，插件版本不能代表运行版本。 [上游](https://github.com/fail2ban/fail2ban/releases) |
| `gdrive` | 面板集成 | Google Drive 备份适配器。Python SDK 独立维护，需用实际 OAuth 集成验证。 |
| `gitea` | 已更新 | 新增 28.4.0，保留旧版安装入口。 [上游](https://github.com/go-gitea/gitea/releases/tag/v28.4.0) |
| `gogs` | 已更新 | 新增 0.14.4，增加新版 Linux/macOS 官方归档命名和 arm64 选择。 [上游](https://github.com/gogs/gogs/releases/tag/v0.14.4) |
| `gorse` | 已更新 | 新增 0.5.11，确认 Linux amd64 与 arm64 归档存在。 [上游](https://github.com/gorse-io/gorse/releases/tag/v0.5.11) |
| `grafana` | 已更新 | 新增 Grafana OSS 13.3.2，修正服务启动路径及旧默认服务定义。Debian 13 安装、systemd 和数据库健康接口通过。 [上游](https://github.com/grafana/grafana/releases/tag/v13.3.2) |
| `haproxy` | 已更新 | 2.6.36、2.8.32、3.0.31、3.2.27；新增 3.4.8，使用官方 SHA-256。 [上游](https://www.haproxy.org/) |
| `imail` | 面板集成 | 面板邮件组件，版本属于插件。底层邮件服务另行维护。 |
| `keepalived` | 已更新 | 2.4.3，官方归档与发布页摘要一致。 [上游](https://www.keepalived.org/download/) |
| `lam` | 已更新 | 新增 LDAP Account Manager 9.7，改为按所选版本下载。 [上游](https://github.com/LDAPAccountManager/lam/releases/tag/9.7) |
| `ldap` | 软件源 | LDAP 软件由发行版仓库提供，1.0 为封装版本。 |
| `loki` | 已更新 | 新增 Loki 3.7.10 与 Alloy 1.22.0。安装时转换旧 Promtail 配置，验证后切换采集服务。Debian 13 验证日志采集、写入和查询。 [上游迁移指南](https://grafana.com/docs/alloy/latest/set-up/migrate/from-promtail/) |
| `lvs` | 软件源 | 依赖 Linux 内核 IPVS 和发行版工具，无独立面板运行时更新。 |
| `manticoresearch` | 候选待验证 | 上游标签 release-32.1.3。现有入口混合软件源与源码，需按发行版核对。 [上游](https://github.com/manticoresoftware/manticoresearch/releases) |
| `mariadb` | 部分已是当前 | 已核对 10.11.20、11.4.14、11.8.10、12.3.4 与仓库一致。13.1.2 是滚动 GA，待验证数据库迁移和平台包。 [上游](https://mariadb.com/downloads/) |
| `memcached` | 已是当前 | 1.6.45。 [上游](https://www.memcached.org/downloads) |
| `migration_api` | 面板集成 | 面板迁移 API，无独立上游版本。 |
| `mongodb` | 已更新 | Debian x86_64 的 9.0 安装路径使用 9.0.8 与发行版匹配的官方包，同时更新 mongosh 2.14.3 和数据库工具 100.20.1。Debian 13 通过写入、查询、备份和恢复。其他发行版入口仍需验证。 [上游](https://www.mongodb.com/docs/manual/release-notes/9.0/) |
| `mosquitto` | 已更新 | 2.0.23 与 2.1.4，更新源码摘要并在编译失败时停止。 [上游](https://mosquitto.org/blog/2026/11/version-2-1-3-released/) |
| `msonedrive` | 面板集成 | Microsoft OneDrive 备份适配器。SDK 与 API 兼容性需在真实账户验证。 |
| `mtproxy` | 候选待验证 | 上游 mtg 2.3.0。面板的 1.0 是封装版本，需核对运行参数及已有配置。 [上游](https://github.com/9seconds/mtg/releases) |
| `mysql` | 已更新 | 源码 8.4.13.1、9.7.4.1、26.10.0.1。 [上游](https://dev.mysql.com/community/security/advisories/2026-11-24/) |
| `mysql-community` | 已更新 | 同三条版本线，已检查 Linux x86_64、aarch64 和 macOS arm64 下载地址。 [上游](https://dev.mysql.com/downloads/mysql/) |
| `nezha` | 已更新 | 新增固定版本 2.7.0。 [上游](https://github.com/nezhahq/nezha/releases/tag/v2.7.0) |
| `ollama` | 候选待验证 | 上游 0.40.18。面板 1.0 是封装版本，需验证安装器与已下载模型。 [上游](https://github.com/ollama/ollama/releases) |
| `op_load_balance` | 面板集成 | 面板的 OpenResty 负载均衡适配器，无独立运行时。 |
| `op_waf` | 候选待验证 | 上游 0.7.2。需验证规则格式、已有自定义规则及 OpenResty 兼容性。 [上游](https://github.com/loveshell/ngx_lua_waf/releases) |
| `openresty` | 已是当前 | 主线 1.31.9.1。RTMP 变体单独使用带模块的固定构建。 [上游](https://github.com/openresty/openresty/releases) |
| `pgadmin` | 软件源 | Python 包版本由安装环境解析，面板 4 是产品系列。 [上游](https://www.pgadmin.org/download/pgadmin-4-python/) |
| `php` | 已更新 | 8.2.36、8.3.37、8.4.28、8.5.13 已核对 SHA-256，新增 8.6.0。历史分支保留停止维护标识和现有回补，应用失败中止。 [上游](https://www.php.net/supported-versions.php) |
| `php-apt` | 已更新 | 用 APT 候选包和已安装包判断可更新版本，更新当前系列的发行版补丁。 |
| `php-guard` | 面板集成 | PHP 管理适配器，无独立运行时。 |
| `php-yum` | 已更新 | 8.2–8.5 使用 Remi 仓库候选包判断并执行真实升级。 [软件源](https://rpms.remirepo.net/) |
| `phpldapadmin` | 候选待验证 | 上游 2.3.13，原插件基于 1.x 布局。需适配新版依赖、配置和迁移。 [上游](https://github.com/leenooks/phpLDAPadmin/releases) |
| `phpmyadmin` | 已是当前 | 5.2.3 为上游当前稳定版，旧分支单独保留。 [上游](https://www.phpmyadmin.net/downloads/) |
| `postgresql` | 已更新 | 新增 19.0 全新安装，15–18 补丁已与官网一致，14 保留停止维护标识。 [上游](https://www.postgresql.org/support/versioning/) |
| `prometheus` | 已更新 | 新增 3.16.0，修正 Linux arm64 归档选择。 [上游](https://github.com/prometheus/prometheus/releases/tag/v3.16.0) |
| `pureftp` | 已更新 | 1.0.54，支持从旧版发起升级并保留 PureDB 配置。 [上游](https://github.com/jedisct1/pure-ftpd/releases/tag/1.0.54) |
| `rapira` | 候选待验证 | 单独的 PHP 运行时提供方。需确认发行包和补丁，不用 PHP 官方版本号替代。 |
| `redis` | 已更新 | 新增 8.12.0。早期系列继续供既有应用兼容。 [上游](https://github.com/redis/redis/releases/tag/8.12.0) |
| `rsyncd` | 已更新 | 合入维护者的 3.5.2 更新。Debian 13 已通过源码编译、服务启动和文件校验复制。 [上游](https://github.com/RsyncProject/rsync/releases/tag/v3.5.2) |
| `simpleping` | 已更新 | 安装器已下载 2.0，修正目录显示。 [上游](https://github.com/midoks/simpleping/releases) |
| `sphinx` | 候选待验证 | 当前 3.1.1，需核对新包和下载授权。 [上游](https://sphinxsearch.com/downloads/) |
| `supervisor` | 软件源 | Python 包版本随安装渠道变化。 [上游](https://pypi.org/project/supervisor/) |
| `swap` | 面板集成 | 系统 swap 配置，无独立应用版本。 |
| `sys-opt` | 面板集成 | 系统参数配置，无独立应用版本。 |
| `system_safe` | 面板集成 | 系统安全设置，无独立应用版本。 |
| `tamper_proof_py` | 面板集成 | 面板防篡改插件。依赖的 Python 组件独立维护。 |
| `task_manager` | 面板集成 | 面板任务管理插件。网络采集依赖 libpcap 与 Python 包。 |
| `tgbot` | 面板集成 | Telegram Bot API 适配器，SDK 由包管理器维护。 |
| `valkey` | 已更新 | 新增 9.2.1。 [上游](https://github.com/valkey-io/valkey/releases/tag/9.2.1) |
| `varnish` | 软件源 | 安装发行版 Varnish 包。 [上游](https://varnish-cache.org/releases/) |
| `webhook` | 面板集成 | 面板回调功能，无独立应用版本。 |
| `webssh` | 面板集成 | 面板终端功能，SSH 依赖独立维护。 |
| `webstats` | 候选待验证 | 封装多个第三方分析组件，暂无单一可替换的新版包。 |
| `xhprof` | 已更新 | 面板报告页与扩展对齐 PECL 2.3.10，使用 PHP 提供的扩展目录。Debian 13 上分别用 PHP 8.4.28 和 8.6.0 编译、加载扩展并生成分析数据。 [上游](https://pecl.php.net/package/xhprof) |
| `xui` | 候选待验证 | 上游 0.3.4.4。需核对服务管理和数据库兼容性。 [上游](https://github.com/FranzKafkaYu/x-ui/releases) |
| `zabbix` | 已更新 | 新增 Debian/Ubuntu 的 8.0 LTS 安装选项，适配新版前端和 SQL 包路径。Debian 13 用隔离 MariaDB 导入官方 schema，Zabbix server 8.0.0 启动通过。面板自动初始化仍需端到端验证。 [上游](https://www.zabbix.com/documentation/8.0/en/manual/installation/requirements) |
| `zabbix_agent` | 已更新 | 新增 Debian/Ubuntu 的 8.0 LTS 安装选项。Debian 13 通过插件安装、systemd 启动和 zabbix_get 的 agent.ping。 [上游](https://www.zabbix.com/download_sources) |
