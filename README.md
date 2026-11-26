# pmpanel

一款清爽的 Linux 服务器管理面板，基于插件管理网站、数据库、FTP、计划任务等常用服务。

## 系统要求

- 推荐 Debian / Ubuntu，也支持 CentOS / Rocky / Alma / Fedora / openEuler / Amazon Linux 等
- 需要 root 权限

## 安装

```
bash <(curl -fsSL https://raw.githubusercontent.com/ledang3099/pmpanel/master/scripts/install.sh)
```

## 更新

```
bash <(curl -fsSL https://raw.githubusercontent.com/ledang3099/pmpanel/master/scripts/update.sh)
```

## 卸载

```
wget -O uninstall.sh https://raw.githubusercontent.com/ledang3099/pmpanel/master/scripts/uninstall.sh && bash uninstall.sh
```

## 常用命令

安装完成后系统中注册 `pm` 命令，详见 [cmd.md](cmd.md)：

```
pm default    # 显示面板登录信息
pm start      # 启动面板
pm stop       # 停止面板
pm restart    # 重启面板
pm list       # 显示全部命令
```

面板安装目录：`/www/server/pmpanel`

## 常见问题

安装/更新时 Python 依赖（pip、psutil 等）报错，可清理虚拟环境后重新更新：

```
cd /www/server/pmpanel && rm -rf lib lib64 bin include
pm update
```

## 许可证

Apache License 2.0，见 [LICENSE](LICENSE) 与 [NOTICE](NOTICE)。
