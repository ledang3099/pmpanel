# 软件管理版本核对

核对始于 2026-11-26，覆盖当时软件管理的 72 个条目，并记录主分支随后新增的 ModSecurity。发行信息来自上游官方发布页、GitHub Releases 或发行版软件源。aaPanel 用于补查同类功能和依赖，例如 PHP、MySQL、Pure-FTPd、Redis 与 PHP Guardian。 [aaPanel 软件商店](https://www.aapanel.com/docs/Function/AppStore.html)

安装器的下载地址或发布元数据已经核对的变更列在表中。软件源条目的实际补丁版本取决于系统和启用的仓库。候选版本尚未完成现有配置、迁移或平台验证。

| 插件 | 结果 | 核对记录 |
| --- | --- | --- |
| `acme_pandominassl_apply` | 面板集成 | 对接 acme.sh。Debian 13 已安装面板适配器；公网 DNS 验证和签发需要域名及供应商凭据。 [上游](https://github.com/acmesh-official/acme.sh/releases) |
| `alist` | 已更新 | 3.66.0，按版本缓存并验证发布摘要，取消固定管理员密码初始化。Debian 13 安装、systemd 和 HTTP 探活通过。 [上游](https://github.com/alist-org/alist/releases/tag/v3.66.0) |
| `apache` | 依赖已更新 | httpd 2.4.71 与 APR 1.7.6、APR-util 1.6.6 使用官方校验值。Debian 13 源码编译、服务和默认页面通过。 [Apache httpd](https://httpd.apache.org/download.cgi) [APR](https://apr.apache.org/) |
| `backup_ftp` | 功能修复 | 移除未使用的 Paramiko 依赖，修复路径备份首次运行缺目录及未传计划任务参数。Debian 13 通过计划任务使用的入口连续执行两次路径备份、验证远端保留一份，并下载压缩包恢复文件。网站和数据库备份恢复待验证。 |
| `caddy` | 已是当前 | 2.11.9。Debian 13 通过安装、版本和 HTTP 监听检查。 [上游](https://github.com/caddyserver/caddy/releases) |
| `clean` | 面板集成 | Debian 13 面板日志清理插件安装和初始化通过。 |
| `cloudreve` | 已更新 | 新增 4.19.1 全新安装，识别 V3 数据并要求先迁移。Debian 13 安装、systemd 和站点配置 API 通过。 [官方迁移说明](https://docs.cloudreve.org/zh/maintain/upgrade-from-v3) |
| `cryptocurrency_trade` | 已更新 | 固定 CCXT 4.5.94 和 TA-Lib 0.8.3.post1，Debian 13 通过安装、OKX 行情样例解析和指标计算。真实账户和订单待验证。 [CCXT](https://pypi.org/project/ccxt/) [TA-Lib](https://pypi.org/project/TA-Lib/) |
| `data_query` | 面板集成 | Debian 13 已安装面板数据查询插件。 |
| `docker` | 安装修复 | Debian/Ubuntu 改走 Docker 官方签名软件源，安装器校验真实引擎连接。Debian 13 安装 29.10.1，在隔离容器的本地配置下 API 探活通过。内层容器解包的 unshare 被宿主隔离限制拒绝。 [上游](https://docs.docker.com/engine/install/debian/) |
| `doh` | 已更新 | 新增 0.11.1，校验 Linux x86_64 和 aarch64 压缩包。Debian 13 安装与 systemd 启动通过。 [上游](https://github.com/DNSCrypt/doh-server/releases/tag/0.11.1) |
| `dynamic-tracking` | 已更新 | 固定 Brendan Gregg 官方 FlameGraph 源码提交和摘要。Debian 13 完成安装并从测试堆栈生成 SVG。 [上游](https://github.com/brendangregg/FlameGraph) |
| `dztasks` | 安装修复 | 1.2 为最新官方版本。修正 Linux arm64 归档名，校验归档并保留现有扩展。Debian 13 验证服务、登录页面跳转和示例扩展文件。 [上游](https://github.com/midoks/dztasks/releases/tag/1.2) |
| `fail2ban` | 软件源 | 上游 1.1.1，面板安装发行版软件包。Debian 13 通过安装、服务启动和 fail2ban-client ping。 [上游](https://github.com/fail2ban/fail2ban/releases) |
| `gdrive` | 依赖已更新 | 移除旧版 SDK 强制降级和 ICMP 前置检查。Debian 13 安装并用 Google Drive SDK 2.202.0 构造测试请求。实际 OAuth 和备份写入需有效账户。 [上游](https://pypi.org/project/google-api-python-client/) |
| `gitea` | 已更新 | 新增 28.4.0，校验下载摘要，保留旧版安装入口。Debian 13 服务和初始设置页面通过。 [上游](https://github.com/go-gitea/gitea/releases/tag/v28.4.0) |
| `gogs` | 已更新 | 新增 0.14.4，校验官方归档，修复 Debian 13 systemd 启动失败。服务和初始设置页面通过。 [上游](https://github.com/gogs/gogs/releases/tag/v0.14.4) |
| `gorse` | 已更新 | 新增 0.5.11，适配新配置格式和服务缓存路径。全新安装采用 SQLite；Debian 13 启动后健康接口确认数据及缓存连接成功。 [上游](https://github.com/gorse-io/gorse/releases/tag/v0.5.11) |
| `grafana` | 已更新 | 新增 Grafana OSS 13.3.2，修正服务启动路径及旧默认服务定义。Debian 13 安装、systemd 和数据库健康接口通过。 [上游](https://github.com/grafana/grafana/releases/tag/v13.3.2) |
| `haproxy` | 已更新 | 2.6.36、2.8.32、3.0.31、3.2.27，新增 3.4.8，使用官方 SHA-256。Debian 13 编译并启动 3.4.8，HTTP 请求经代理转发后返回预期内容。 [上游](https://www.haproxy.org/) |
| `imail` | 面板集成 | 0.0.19 为对应项目当前最后的正式发布。Debian 13 验证安装、服务启动和 HTTP 登录跳转。SMTP、IMAP 与真实域名配置待验证。 [上游](https://github.com/midoks/imail/releases) |
| `keepalived` | 已更新 | 2.4.3，修正 systemd 模板，取消新安装默认绑定示例 VIP。Debian 13 编译、配置检查、启动及重载通过。VRRP 主备切换待验证。 [上游](https://www.keepalived.org/download/) |
| `lam` | 已更新 | 新增 LDAP Account Manager 9.7，校验下载摘要并修正 PHP-FPM 版本识别。Debian 13 通过 OpenResty、PHP 8.4 与认证登录页检查。LAM 的 LDAP 写入待验证。 [上游](https://github.com/LDAPAccountManager/lam/releases/tag/9.7) |
| `ldap` | 安装修复 | 发行版 OpenLDAP，安装后显式启动 slapd。Debian 13 通过根 DSE 的 namingContexts 查询。 |
| `loki` | 已更新 | 新增 Loki 3.7.10 与 Alloy 1.22.0。安装时转换旧 Promtail 配置，验证后切换采集服务。Debian 13 验证日志采集、写入和查询。 [上游迁移指南](https://grafana.com/docs/alloy/latest/set-up/migrate/from-promtail/) |
| `lvs` | 软件源 | 发行版 IPVS 工具。Debian 13 安装通过，内核 IPVS 转发待验证。 |
| `manticoresearch` | 安装修复 | APT 入口使用官方仓库并适配 32.1.3 合并后的主包。Debian 13 安装、systemd 和 SQL 版本查询通过。 [上游](https://github.com/manticoresoftware/manticoresearch/releases) |
| `mariadb` | 已更新 | 新增 13.1.2 滚动版 Linux x86_64 全新安装，验证官方归档和认证 SQL 读写。修正 12.3 安装记录，保持现有 LTS 选择和推荐。跨版本数据迁移待验证。 [上游](https://mariadb.org/mariadb-server-13-1-is-now-stable-and-13-2-reaches-release-candidate/) |
| `memcached` | 已是当前 | 1.6.45。Debian 13 通过插件安装和缓存读写。 [上游](https://www.memcached.org/downloads) |
| `migration_api` | 面板集成 | Debian 13 已安装面板迁移 API；跨服务器迁移待验证。 |
| `modsecurity` | 主分支新增 | 主分支集成 ModSecurity 3.0.17、NGINX connector 1.0.4 和 OWASP CRS 4.31.0。Debian 13 通过源码编译、动态模块装载、配置语法和普通 HTTP 请求。 [上游](https://github.com/owasp-modsecurity/ModSecurity/releases/tag/v3.0.17) |
| `mongodb` | 已更新 | Debian、Ubuntu 和 RHEL 系 9.0 安装入口共享官方归档及 SHA-256 校验，使用 9.0.8、mongosh 2.14.3 和数据库工具 100.20.1。Debian 13、Ubuntu 24.04、Rocky Linux 9 的 x86_64 容器通过写入、查询、备份和恢复，Rocky 9 另通过面板安装与 systemd 启动。其他平台运行待验证。 [上游](https://www.mongodb.com/try/download/community-edition/releases) |
| `mosquitto` | 已更新 | 2.0.23 与 2.1.4，修正 CMake、共享库路径及 systemd 前台服务配置。Debian 13 通过源码安装及 MQTT 发布和订阅。 [上游](https://mosquitto.org/blog/2026/11/version-2-1-3-released/) |
| `msonedrive` | 依赖已更新 | 更新 Requests-OAuthlib 2.0.0，Debian 13 生成并校验本地 OAuth 授权 URL。实际 OAuth 和上传需有效账户。 [上游](https://pypi.org/project/requests-oauthlib/) |
| `mtproxy` | 已更新 | 固定 mtg 2.3.0 官方归档和摘要，修复空密钥生成，保留既有密钥。Debian 13 验证服务启动和 TCP 监听。 [上游](https://github.com/9seconds/mtg/releases) |
| `mysql` | 已更新 | 源码 8.4.13.1、9.7.4.1、26.10.0.1。构建使用系统 OpenSSL，Debian/Ubuntu 补充 WebAuthn 依赖，并按 Linux 容器内存限制减少默认构建并发。保护已被占用的 `mysql.service`，初始化保留面板设置的表名大小写并等待服务就绪。Debian 13 通过 26.10.0.1 源码构建、面板初始化、服务启用、认证 SQL 写入与查询及重启。按维护者要求跳过 8.4 和 9.7 源码构建。 [上游](https://dev.mysql.com/community/security/advisories/2026-11-24/) |
| `mysql-community` | 已更新 | 8.4.13.1、9.7.4.1、26.10.0.1 的 Linux x86_64 安装使用 Oracle 官方最小二进制归档。修复初始化误读宿主 MariaDB 配置。Debian 13 实际运行三个版本的面板安装入口，均通过服务启动、账号认证、SQL 写入与查询及服务重启。8.4 验证测试库备份和恢复，26.10 验证拒绝运行中覆盖及停服后重装。核对 Linux aarch64 与 macOS arm64 下载地址。 [上游补丁](https://dev.mysql.com/community/security/advisories/2026-11-24/) [二进制分发说明](https://dev.mysql.com/doc/refman/26.10/en/binary-installation.html) |
| `nezha` | 已更新 | 新增固定版本 2.7.0。Debian 13 完成安装，面板首页返回 HTTP 200。 [上游](https://github.com/nezhahq/nezha/releases/tag/v2.7.0) |
| `ollama` | 已更新 | 固定 0.40.18 官方安装器摘要，面板交由供应商 systemd 单元管理。Debian 13 验证启动和版本 API。 [上游](https://github.com/ollama/ollama/releases/tag/v0.40.18) |
| `op_load_balance` | 面板集成 | Debian 13 使用插件生成的配置经 OpenResty 实测，轮询把 HTTP 请求分发给两个本地后端。主动健康检查将返回 HTTP 503 的后端标记为不可用，并把请求转至健康后端。 |
| `op_waf` | 依赖已更新 | 面板自带的 OpenResty WAF 更新 LuaRocks 3.13.0、lsqlite3 0.9.7、libmaxminddb 1.14.1 和 GeoLite 数据。Debian 13 通过 LuaJIT SQLite 查询、GeoLite 查找和 OpenResty 启动。 [LuaRocks](https://github.com/luarocks/luarocks/releases/tag/v3.13.0) [MaxMind](https://github.com/maxmind/libmaxminddb/releases/tag/1.14.1) |
| `openresty` | 安装修复 | 主线 1.31.9.1，修复升级后旧进程占用端口和动态模块未切换。Debian 13 验证源码构建、ModSecurity 模块和 systemd 重启。无 systemd 容器验证面板脚本启动与重启、HTTP 响应、成功后更新版本及配置错误时保留版本记录。 [上游](https://github.com/openresty/openresty/releases) |
| `pgadmin` | 已更新 | 固定 pgAdmin 4 9.19，改用官方非交互数据库初始化。Debian 13 通过应用初始化、systemd、Unix socket 健康接口和登录页面。 [上游](https://www.pgadmin.org/docs/pgadmin4/9.19/server_deployment.html) |
| `php` | 已更新 | 8.2.36、8.3.37、8.4.28、8.5.13 已核对 SHA-256，新增 8.6.0。Debian 13 已编译五个系列的运行时并做执行检查。历史分支保留停止维护标识和现有回补。 [上游](https://www.php.net/supported-versions.php) |
| `php-apt` | 已更新 | 使用 APT 候选包判断更新，新增 8.6，配置 Sury 签名仓库并修正内置 OPcache。安装通用扩展时延后面板触发的逐项重启。Debian 13 验证 8.2–8.6 的安装、已是最新版时的升级命令和 FastCGI 版本响应，并验证 8.6 加载 OPcache。 [软件源](https://packages.sury.org/php/pool/main/p/php8.6/) |
| `php-guard` | 面板集成 | Debian 13 安装 PHP 管理适配器通过。 |
| `php-yum` | 已更新 | 8.2–8.6 使用 Remi 仓库判断并执行升级，修正 Rocky 等发行版的仓库安装。Rocky Linux 9 通过五个系列的安装、已是最新版时的升级命令和 FastCGI 版本响应。 [软件源](https://rpms.remirepo.net/) |
| `phpldapadmin` | 已更新 | 新增 2.3.13 全新安装，独立站点根目录、PHP-FPM 8.4+ 与 LDAP 配置。Debian 13 完成 Composer 和前端构建，OpenResty 验证 HTTP 认证，与本地 OpenLDAP 联调打开登录页。1.x 配置迁移与登录后编辑待验证。 [上游](https://github.com/leenooks/phpLDAPadmin/releases/tag/2.3.13) |
| `phpmyadmin` | 安装修复 | 5.2.3 为上游当前稳定版，校验发布归档。Debian 13 通过 OpenResty 和 PHP-FPM 登录页检查。 [上游](https://www.phpmyadmin.net/downloads/) |
| `postgresql` | 已更新 | 新增 19.0 全新安装，15–18 补丁已与官网一致，14 保留停止维护标识。Debian 13 编译 19.0、初始化集群，并通过 SQL 建表、写入和查询。 [上游](https://www.postgresql.org/support/versioning/) |
| `prometheus` | 已更新 | 新增 3.16.0，修正 Linux arm64 归档选择。Debian 13 完成安装，readiness 接口通过。 [上游](https://github.com/prometheus/prometheus/releases/tag/v3.16.0) |
| `pureftp` | 已更新 | Debian 13 验证源码编译和服务启动、重复执行升级命令，以及用面板命令从原目录版本 1.0.49 升到 1.0.54。两次升级均保留账号文件和 PureDB，跨版本升级后可用原虚拟账号登录、下载原文件、上传和删除。 [上游](https://github.com/jedisct1/pure-ftpd/releases/tag/1.0.54) |
| `rapira` | 已更新 | 0.9.2 分别嵌入 PHP 8.4.28 与 8.5.13。Debian 13 两个系列源码构建、并行启用及 HTTP 请求通过，8.4 的 curl 扩展编译和加载通过。原有安装需备份并单独验证扩展迁移。 [上游](https://github.com/rapira-rs/rapira/releases/tag/v0.9.2) |
| `redis` | 已更新 | 新增 8.12.0，校验源码及编译结果并保留现有配置。Debian 13 通过源码编译、PING 和键值读写。 [上游](https://github.com/redis/redis/releases/tag/8.12.0) |
| `rsyncd` | 跳过 | 由维护者在主分支处理。 |
| `simpleping` | 已更新 | 安装器下载 2.0，修正目录显示。Debian 13 安装及 systemd 启动通过。 [上游](https://github.com/midoks/simpleping/releases) |
| `sphinx` | 已更新 | 新增 3.9.1，验证官方二进制摘要并检查 x86_64 AVX2。Debian 13 验证服务及 SphinxQL 写入和搜索。 [上游](https://sphinxsearch.com/downloads/) |
| `supervisor` | 已更新 | 固定 4.3.0，修复 systemd 在 Debian 解析程序路径失败。Debian 13 验证插件安装、启动及管理测试任务。 [上游](https://pypi.org/project/supervisor/) |
| `swap` | 面板集成 | 系统 swap 配置，无独立应用版本。通过状态读取和测试文件的 `mkswap` 初始化。启用和停用待验证。 |
| `sys-opt` | 面板集成 | Debian 13 已安装系统参数插件。容器未修改宿主内核参数。 |
| `system_safe` | 安装修复 | 使用面板 Python 环境加载 psutil。Debian 13 服务正常启动；文件属性锁定待验证。 |
| `tamper_proof_py` | 兼容修复 | 为 Python 3.12+ 安装 asyncore 兼容包。Debian 13 已确认 pyinotify 能加载、初始化，并启动服务。 [上游](https://pypi.org/project/pyasyncore/) |
| `task_manager` | 兼容修复 | 通过 Cython 3 重新生成 pypcap 1.3.0，并使用 Python 缓冲区 API。Debian 13/Python 3.13 编译扩展并通过 BPF 测试数据检查。 [上游](https://pypi.org/project/pypcap/) |
| `tgbot` | 已更新 | 固定 PyTelegramBotAPI 4.37.1，并修复 Debian 的启动脚本解释器。通过两条后台进程启动，真实机器人发信需要有效令牌。 [上游](https://pypi.org/project/pyTelegramBotAPI/) |
| `valkey` | 已更新 | 新增 9.2.1，校验源码和编译结果，保留现有配置。Debian 13 插件编译、安装、systemd 启动和认证读写通过。 [上游](https://github.com/valkey-io/valkey/releases/tag/9.2.1) |
| `varnish` | 软件源 | 安装发行版 Varnish 包。Debian 13 通过安装、systemd 和本地代理访问。 [上游](https://varnish-cache.org/releases/) |
| `webhook` | 安装修复 | 缺少 pm 命令时安装仍可完成。Debian 13 验证安装和面板 HTTP 回调，测试脚本按预期输出且调用计数增加一次。 |
| `webssh` | 功能修复 | 修复编辑最后一条常用命令时写入重复项。Debian 13 通过安装和同名命令更新测试；浏览器终端连接待验证。 |
| `webstats` | 依赖已更新 | 更新 LuaRocks、lsqlite3 和 GeoLite City 数据。Debian 13 通过 OpenResty 采集测试请求并写入 SQLite 日志与各项统计。 [lsqlite3](https://luarocks.org/modules/javierguerragiraldez/lsqlite3) |
| `xhprof` | 已更新 | 面板报告页与扩展对齐 PECL 2.3.10，使用 PHP 提供的扩展目录。Debian 13 上分别用 PHP 8.4.28 和 8.6.0 编译、加载扩展并生成分析数据。 [上游](https://pecl.php.net/package/xhprof) |
| `xui` | 安装修复 | 0.3.4.4 为当前对应项目的最后一个正式发布。固定官方归档及摘要，由 systemd 管理进程，保留现有数据库。Debian 13 验证正常启动及 HTTP 登录页。 [上游](https://github.com/FranzKafkaYu/x-ui/releases/tag/0.3.4.4) |
| `zabbix` | 已更新 | 新增 Debian/Ubuntu 的 8.0 LTS，修复 PHP-FPM 与数据库识别、自动建库、schema 导入及 OpenResty 日志目录。Debian 13 从面板正常安装入口用 MySQL Community 8.4 自动建库并启动 Zabbix 8.0.0，验证全局数据库设置恢复、PHP 8.4 前端 HTTP 200、API 登录、主机查询和退出。 [上游](https://www.zabbix.com/documentation/8.0/en/manual/installation/requirements) |
| `zabbix_agent` | 已更新 | 新增 Debian/Ubuntu 的 8.0 LTS 安装选项。Debian 13 通过插件安装、systemd 启动和 zabbix_get 的 agent.ping。 [上游](https://www.zabbix.com/download_sources) |
