# 软件管理版本核对

核对始于 2026-11-26，覆盖当时软件管理的 72 个条目，并记录主分支随后新增的 ModSecurity。发行信息来自上游官方发布页、GitHub Releases 或发行版软件源。aaPanel 用于补查同类功能和依赖，例如 PHP、MySQL、Pure-FTPd、Redis 与 PHP Guardian。 [aaPanel 软件商店](https://www.aapanel.com/docs/Function/AppStore.html)

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
| `cryptocurrency_trade` | 已更新 | 固定 CCXT 4.5.94 和 TA-Lib 0.8.3.post1，Debian 13 通过安装、OKX 行情样例解析和指标计算。真实账户和订单待验证。 [CCXT](https://pypi.org/project/ccxt/) [TA-Lib](https://pypi.org/project/TA-Lib/) |
| `data_query` | 面板集成 | 面板数据查询插件，无独立上游版本。 |
| `docker` | 软件源 | 包装 Docker 官方安装渠道，1.0 是面板插件版本。 [上游](https://docs.docker.com/engine/release-notes/) |
| `doh` | 已更新 | 新增 0.11.1，校验 Linux x86_64 和 aarch64 压缩包。Debian 13 安装与 systemd 启动通过。 [上游](https://github.com/DNSCrypt/doh-server/releases/tag/0.11.1) |
| `dynamic-tracking` | 已更新 | 固定 Brendan Gregg 官方 FlameGraph 源码提交和摘要。Debian 13 完成安装并从测试堆栈生成 SVG。 [上游](https://github.com/brendangregg/FlameGraph) |
| `dztasks` | 安装修复 | 1.2 为最新官方版本。修正 Linux arm64 归档名，校验归档并保留现有扩展。Debian 13 验证服务、登录页面跳转和示例扩展文件。 [上游](https://github.com/midoks/dztasks/releases/tag/1.2) |
| `fail2ban` | 软件源 | 上游 1.1.1。面板安装的是发行版的 fail2ban 包，插件版本不能代表运行版本。 [上游](https://github.com/fail2ban/fail2ban/releases) |
| `gdrive` | 面板集成 | Google Drive 备份适配器。Python SDK 独立维护，需用实际 OAuth 集成验证。 |
| `gitea` | 已更新 | 新增 28.4.0，校验下载摘要，保留旧版安装入口。Debian 13 服务和初始设置页面通过。 [上游](https://github.com/go-gitea/gitea/releases/tag/v28.4.0) |
| `gogs` | 已更新 | 新增 0.14.4，校验官方归档，修复 Debian 13 systemd 启动失败。服务和初始设置页面通过。 [上游](https://github.com/gogs/gogs/releases/tag/v0.14.4) |
| `gorse` | 已更新 | 新增 0.5.11，适配新配置格式和服务缓存路径。全新安装采用 SQLite；Debian 13 启动后健康接口确认数据及缓存连接成功。 [上游](https://github.com/gorse-io/gorse/releases/tag/v0.5.11) |
| `grafana` | 已更新 | 新增 Grafana OSS 13.3.2，修正服务启动路径及旧默认服务定义。Debian 13 安装、systemd 和数据库健康接口通过。 [上游](https://github.com/grafana/grafana/releases/tag/v13.3.2) |
| `haproxy` | 已更新 | 2.6.36、2.8.32、3.0.31、3.2.27；新增 3.4.8，使用官方 SHA-256。Debian 13 编译并启动 3.4.8。 [上游](https://www.haproxy.org/) |
| `imail` | 面板集成 | 面板邮件组件，版本属于插件。底层邮件服务另行维护。 |
| `keepalived` | 已更新 | 2.4.3，修正 systemd 模板，取消新安装默认绑定示例 VIP。Debian 13 编译、配置检查、启动及重载通过。VRRP 主备切换待验证。 [上游](https://www.keepalived.org/download/) |
| `lam` | 已更新 | 新增 LDAP Account Manager 9.7，校验下载摘要并修正 PHP-FPM 版本识别。Debian 13 通过 OpenResty、PHP 8.4 与认证登录页检查。LAM 的 LDAP 写入待验证。 [上游](https://github.com/LDAPAccountManager/lam/releases/tag/9.7) |
| `ldap` | 软件源 | LDAP 软件由发行版仓库提供，1.0 为封装版本。 |
| `loki` | 已更新 | 新增 Loki 3.7.10 与 Alloy 1.22.0。安装时转换旧 Promtail 配置，验证后切换采集服务。Debian 13 验证日志采集、写入和查询。 [上游迁移指南](https://grafana.com/docs/alloy/latest/set-up/migrate/from-promtail/) |
| `lvs` | 软件源 | 依赖 Linux 内核 IPVS 和发行版工具，无独立面板运行时更新。 |
| `manticoresearch` | 安装修复 | APT 入口使用官方仓库并适配 32.1.3 合并后的主包。Debian 13 安装、systemd 和 SQL 版本查询通过。 [上游](https://github.com/manticoresoftware/manticoresearch/releases) |
| `mariadb` | 部分已是当前 | 已核对 10.11.20、11.4.14、11.8.10、12.3.4 与仓库一致。13.1.2 是滚动 GA，待验证数据库迁移和平台包。 [上游](https://mariadb.com/downloads/) |
| `memcached` | 已是当前 | 1.6.45。 [上游](https://www.memcached.org/downloads) |
| `migration_api` | 面板集成 | 面板迁移 API，无独立上游版本。 |
| `modsecurity` | 主分支新增 | 主分支新增的 ModSecurity 3 与 OWASP CRS 4 集成。完整编译与面板运行待验证。 |
| `mongodb` | 已更新 | Debian x86_64 的 9.0 安装路径使用 9.0.8 与发行版匹配的官方包，同时更新 mongosh 2.14.3 和数据库工具 100.20.1。Debian 13 通过写入、查询、备份和恢复。其他发行版入口仍需验证。 [上游](https://www.mongodb.com/docs/manual/release-notes/9.0/) |
| `mosquitto` | 已更新 | 2.0.23 与 2.1.4，修正 CMake、共享库路径及 systemd 前台服务配置。Debian 13 通过源码安装及 MQTT 发布和订阅。 [上游](https://mosquitto.org/blog/2026/11/version-2-1-3-released/) |
| `msonedrive` | 面板集成 | Microsoft OneDrive 备份适配器。SDK 与 API 兼容性需在真实账户验证。 |
| `mtproxy` | 已更新 | 固定 mtg 2.3.0 官方归档和摘要，修复空密钥生成，保留既有密钥。Debian 13 验证服务启动和 TCP 监听。 [上游](https://github.com/9seconds/mtg/releases) |
| `mysql` | 已更新 | 源码 8.4.13.1、9.7.4.1、26.10.0.1。 [上游](https://dev.mysql.com/community/security/advisories/2026-11-24/) |
| `mysql-community` | 已更新 | 8.4.13.1、9.7.4.1、26.10.0.1 官方 Linux x86_64 归档均用隔离数据目录初始化，SQL 读写通过。核对 Linux aarch64 与 macOS arm64 下载地址。 [上游](https://dev.mysql.com/community/security/advisories/2026-11-24/) |
| `nezha` | 已更新 | 新增固定版本 2.7.0。Debian 13 完成安装，面板首页返回 HTTP 200。 [上游](https://github.com/nezhahq/nezha/releases/tag/v2.7.0) |
| `ollama` | 已更新 | 固定 0.40.18 官方安装器摘要，面板交由供应商 systemd 单元管理。Debian 13 验证启动和版本 API。 [上游](https://github.com/ollama/ollama/releases/tag/v0.40.18) |
| `op_load_balance` | 面板集成 | 面板的 OpenResty 负载均衡适配器，无独立运行时。 |
| `op_waf` | 依赖已更新 | 面板自带的 OpenResty WAF 更新 LuaRocks 3.13.0、lsqlite3 0.9.7、libmaxminddb 1.14.1 和 GeoLite 数据。Debian 13 通过 LuaJIT SQLite 查询、GeoLite 查找和 OpenResty 启动。 [LuaRocks](https://github.com/luarocks/luarocks/releases/tag/v3.13.0) [MaxMind](https://github.com/maxmind/libmaxminddb/releases/tag/1.14.1) |
| `openresty` | 已是当前 | 主线 1.31.9.1。RTMP 变体单独使用带模块的固定构建。 [上游](https://github.com/openresty/openresty/releases) |
| `pgadmin` | 软件源 | Python 包版本由安装环境解析，面板 4 是产品系列。 [上游](https://www.pgadmin.org/download/pgadmin-4-python/) |
| `php` | 已更新 | 8.2.36、8.3.37、8.4.28、8.5.13 已核对 SHA-256，新增 8.6.0。历史分支保留停止维护标识和现有回补，应用失败中止。 [上游](https://www.php.net/supported-versions.php) |
| `php-apt` | 已更新 | 用 APT 候选包和已安装包判断可更新版本，更新当前系列的发行版补丁。 |
| `php-guard` | 面板集成 | PHP 管理适配器，无独立运行时。 |
| `php-yum` | 已更新 | 8.2–8.5 使用 Remi 仓库候选包判断并执行真实升级。 [软件源](https://rpms.remirepo.net/) |
| `phpldapadmin` | 已更新 | 新增 2.3.13 全新安装，独立站点根目录、PHP-FPM 8.4+ 与 LDAP 配置。Debian 13 完成 Composer 和前端构建，OpenResty 验证 HTTP 认证，与本地 OpenLDAP 联调打开登录页。1.x 配置迁移与登录后编辑待验证。 [上游](https://github.com/leenooks/phpLDAPadmin/releases/tag/2.3.13) |
| `phpmyadmin` | 已是当前 | 5.2.3 为上游当前稳定版，旧分支单独保留。 [上游](https://www.phpmyadmin.net/downloads/) |
| `postgresql` | 已更新 | 新增 19.0 全新安装，15–18 补丁已与官网一致，14 保留停止维护标识。Debian 13 编译 19.0、初始化集群，并通过 SQL 建表、写入和查询。 [上游](https://www.postgresql.org/support/versioning/) |
| `prometheus` | 已更新 | 新增 3.16.0，修正 Linux arm64 归档选择。Debian 13 完成安装，readiness 接口通过。 [上游](https://github.com/prometheus/prometheus/releases/tag/v3.16.0) |
| `pureftp` | 已更新 | 1.0.54，支持从旧版发起升级并保留 PureDB 配置。Debian 13 编译和服务启动通过，虚拟用户完成登录、上传、下载和删除。现有账户迁移待验证。 [上游](https://github.com/jedisct1/pure-ftpd/releases/tag/1.0.54) |
| `rapira` | 已更新 | 0.9.2 分别嵌入 PHP 8.4.28 与 8.5.13。Debian 13 两个系列源码构建、并行启用及 HTTP 请求通过，8.4 的 curl 扩展编译和加载通过。原有安装需备份并单独验证扩展迁移。 [上游](https://github.com/rapira-rs/rapira/releases/tag/v0.9.2) |
| `redis` | 已更新 | 新增 8.12.0，校验源码及编译结果并保留现有配置。Debian 13 通过源码编译、PING 和键值读写。 [上游](https://github.com/redis/redis/releases/tag/8.12.0) |
| `rsyncd` | 跳过 | 由维护者在主分支处理。 |
| `simpleping` | 已更新 | 安装器已下载 2.0，修正目录显示。 [上游](https://github.com/midoks/simpleping/releases) |
| `sphinx` | 已更新 | 新增 3.9.1，验证官方二进制摘要并检查 x86_64 AVX2。Debian 13 验证服务及 SphinxQL 写入和搜索。 [上游](https://sphinxsearch.com/downloads/) |
| `supervisor` | 软件源 | Python 包版本随安装渠道变化。 [上游](https://pypi.org/project/supervisor/) |
| `swap` | 面板集成 | 系统 swap 配置，无独立应用版本。 |
| `sys-opt` | 面板集成 | 系统参数配置，无独立应用版本。 |
| `system_safe` | 面板集成 | 系统安全设置，无独立应用版本。 |
| `tamper_proof_py` | 面板集成 | 面板防篡改插件。依赖的 Python 组件独立维护。 |
| `task_manager` | 面板集成 | 面板任务管理插件。网络采集依赖 libpcap 与 Python 包。 |
| `tgbot` | 面板集成 | Telegram Bot API 适配器，SDK 由包管理器维护。 |
| `valkey` | 已更新 | 新增 9.2.1，校验源码和编译结果，保留现有配置。Debian 13 插件编译、安装、systemd 启动和认证读写通过。 [上游](https://github.com/valkey-io/valkey/releases/tag/9.2.1) |
| `varnish` | 软件源 | 安装发行版 Varnish 包。 [上游](https://varnish-cache.org/releases/) |
| `webhook` | 面板集成 | 面板回调功能，无独立应用版本。 |
| `webssh` | 面板集成 | 面板终端功能，SSH 依赖独立维护。 |
| `webstats` | 依赖已更新 | 更新 LuaRocks、lsqlite3 和 GeoLite City 数据。Debian 13 通过 OpenResty 采集测试请求并写入 SQLite 日志与各项统计。 [lsqlite3](https://luarocks.org/modules/javierguerragiraldez/lsqlite3) |
| `xhprof` | 已更新 | 面板报告页与扩展对齐 PECL 2.3.10，使用 PHP 提供的扩展目录。Debian 13 上分别用 PHP 8.4.28 和 8.6.0 编译、加载扩展并生成分析数据。 [上游](https://pecl.php.net/package/xhprof) |
| `xui` | 安装修复 | 0.3.4.4 为当前对应项目的最后一个正式发布。固定官方归档及摘要，由 systemd 管理进程，保留现有数据库。Debian 13 验证正常启动及 HTTP 登录页。 [上游](https://github.com/FranzKafkaYu/x-ui/releases/tag/0.3.4.4) |
| `zabbix` | 已更新 | 新增 Debian/Ubuntu 的 8.0 LTS 安装选项，适配新版前端和 SQL 包路径。Debian 13 用隔离 MariaDB 导入官方 schema，Zabbix server 8.0.0 启动通过。面板自动初始化仍需端到端验证。 [上游](https://www.zabbix.com/documentation/8.0/en/manual/installation/requirements) |
| `zabbix_agent` | 已更新 | 新增 Debian/Ubuntu 的 8.0 LTS 安装选项。Debian 13 通过插件安装、systemd 启动和 zabbix_get 的 agent.ping。 [上游](https://www.zabbix.com/download_sources) |
