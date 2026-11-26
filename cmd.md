### 常用命令说明


- 面板相关命令

```
pm start    | 启动面板服务器
pm stop     | 停止面板服务器
pm restart  | 重启面板服务器
pm default	| 显示登录信息
pm db 		| 快捷连接MySQL
pm redis 	| 快捷连接Redis
pm valkey 	| 快捷连接valkey
pm mongodb 	| 快捷连接MongoDB
pm pgdb 	| 快捷连接PostgreSQL
pm ssh 		| 快捷连接ssh
----------------------------------------
pm open				| 开启面板
pm close			| 关闭面板

pm debug			| 开发测试
pm venv				| 进入虚拟环境
pm mirror			| 切换镜像
pm install_app			| 快捷安装常用软件
pm update 			| 更新到正式
pm dev/update_dev		| 更新到开发

service pm [start|stop|reload|restart|status]
```

- OpenResty

```

systemctl [start|stop|reload|restart|status] openresty 

```

- MySQL

```

systemctl [start|stop|reload|restart|status] mysql 

```

- MariaDB

```

systemctl [start|stop|reload|restart|status] mariadb 

```

- PHP

```

systemctl [start|stop|reload|restart|status] php[54-81] 

systemctl start php71
```

- Redis

```

systemctl [start|stop|reload|restart|status] redis

```

- Memcached

```

systemctl [start|stop|reload|restart|status] memcached

```


- sphinx

```

systemctl [start|stop|reload|restart|status] sphinx

```
