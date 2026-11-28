# pmpanel 项目说明(给 Claude Code 的上下文)

pmpanel 是基于 mdserver-web 二次开发的 Linux 服务器管理面板(Apache-2.0, 保留 LICENSE 与 NOTICE)。
当前版本 1.2.0(`web/version.py`)。

## 仓库与协作规则

- 只在 `ledang3099/pmpanel` 开发和推送; 旧仓库 pmserver-web 已删除, 不再使用。
- 维护者希望先在本地(`~/Desktop/panle`)开发测试, 确认后再推送。
- 另一位协作者 paomo2(Codex)通过 PR 提交插件更新。流程: 先审核, 等维护者说"提交完了"再合并;
  合并前确认 master 上的安全修复没有被冲掉, 合并后跑回归测试再推送。
- 提交作者信息不要带个人邮箱或主机名(使用 `noreply@users.noreply.github.com` 一类的地址)。
- 不要把开发者个人信息写进代码。

## 命名

- 系统命令 `pm`(原 `mw`), 安装目录 `/www/server/pmpanel`。
- 侧边栏: 首页、网站、数据库、监控、安全、文件、日志、终端、计划任务、应用市场(原"软件管理")、面板设置。

## 代码结构(新增/重写的部分)

| 功能 | 后端 | 前端 |
| --- | --- | --- |
| 安全: 防火墙、SSH 管理、SSH 登录日志、系统账号 | `web/utils/ssh_manage.py`, `web/utils/sys_user.py`, `web/utils/firewall.py`, 路由 `web/admin/firewall/` | `web/templates/default/firewall.html`, `web/static/app/security.js` |
| 数据库: MySQL/MariaDB、PgSQL、MongoDB、Redis | `web/utils/database.py`(调用数据库插件, 白名单+参数校验), `web/utils/redis_manage.py`, 路由 `web/admin/database/` | `database.html`, `database.js` |
| 日志中心 | `web/utils/log_center.py`, 路由 `web/admin/logs/` | `logs.html`, `logs.js` |
| 终端(本机 pty, 多标签) | `web/utils/ssh/pty_terminal.py`, Socket.IO 事件在 `web/admin/__init__.py`, 路由 `web/admin/terminal/` | `terminal.html`, `terminal.js` |
| 全局文件编辑器(非模态、多标签、跨页面保留) | `/files/get_body`, `/files/save_body` | `web/static/app/pm-editor.js`, `onlineEditFile()` 在 `public.js` |
| 面板在线更新 | `web/utils/system/update.py`, 覆盖脚本 `scripts/update/apply_release.py` | `index.js` |
| ModSecurity + OWASP CRS 防火墙插件 | `plugins/modsecurity/` | 同目录 |
| 新页面公共样式与工具 | — | `pm-theme.css` 末尾的 `pm-*` 组件, `web/static/app/pm-ui.js` |

## 安全约定(已多次修过同类漏洞, 新代码请保持)

- 执行命令用参数列表(`subprocess.run([...])`), 不拼接 shell 字符串; 密码通过 stdin 传入。
- 文件只通过"名称 -> 路径"白名单定位, 或 `realpath` 后检查必须在允许的目录内; 拒绝符号链接。
- 插件函数的参数要逐项校验后再拼进 SQL/命令; 数据库插件里的 `getArgs()` 协议很脆弱,
  新代码通过 `Database.call()` 以 `key:value` 参数列表调用插件。
- 前端输出一律转义(`pmEsc` / `htmlAttrEscape` / `jsAttrEscape`)。
- 会修改状态的接口用 POST(面板对 POST 做 Origin 校验)。

## 运行方式注意

- gunicorn 必须是 1 个 worker(`web/setting.py`): Socket.IO 线程模式下多进程会出现 "Invalid session",
  终端和 WebSSH 都依赖它。线程数 32, 不按请求数重启进程。
- 终端页 Socket.IO 使用长轮询; 输入需合并发送(否则超过 engine.io 单包上限会丢字)。
- 插件回调模块会按文件修改时间自动重新加载(`web/utils/plugin.py`)。

## 测试

- 单元测试: `python3 -m unittest discover -s tests`(只依赖标准库, CI 也运行这些)。
- CI: `.github/workflows/ci.yml` 做 Shell/Python/JSON/JS 语法检查和单元测试。
- 很多功能(SSH、系统账号、ufw、pty 终端、OpenResty)只能在 Linux 上验证; macOS 上请用 Ubuntu 24.04 /
  Debian 12 的容器或虚拟机测试, 面板装在 `/www/server/pmpanel`。

## 发布新版本

1. 修改 `web/version.py` 并推送。
2. 在 GitHub 新建 Release: 标签名与标题都写成版本号(如 `1.2.0`, 不带 v, 不勾选 pre-release),
   说明里写更新内容。面板右上角"更新"读取的就是最新 Release。
   1.0.x 的旧版面板用 Release 标题作为版本号下载, 所以标题必须与标签一致。

## 待办 / 已知事项

- Release 1.2.0 尚未在 GitHub 发布(发布前面板检查更新会提示"仓库中还没有发布正式版本")。
- 已合并可删除的分支: `update/plugin-runtime-verification`, `update/plugin-releases`, `fix/panel-audit-debian`
  (云端会话没有删除分支的权限, 需在 GitHub 网页上删除)。
- 未验证: 防火墙 IPv6 屏蔽(测试容器的 ufw 未开 IPv6); PgSQL/MongoDB 页面(测试环境未安装)。
- 可改进: 插件中非固定版本的下载没有哈希校验; op_waf 的 GeoIP 数据库固定在 2026.11.25 版本。
