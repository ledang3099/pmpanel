# coding:utf-8

# ---------------------------------------------------------------------------------
# PM-Linux面板
# ---------------------------------------------------------------------------------
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------

# Redis / Valkey 数据管理: 概览、按库浏览键(SCAN, 不使用会阻塞的 KEYS)、查看/编辑/删除、过期时间、清空

import os
import re

import core.mw as mw

MAX_VALUE = 512 * 1024     # 查看值时最多返回的字节数
MAX_ITEMS = 500            # 集合类型最多返回的成员数


def ok(msg='OK', data=None):
    return mw.returnData(True, msg, data)


def fail(msg, data=None):
    return mw.returnData(False, msg, data)


class RedisManage(object):

    __instance = None

    @classmethod
    def instance(cls):
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    def confPath(self, name):
        base = mw.getServerDir() + '/' + name
        for f in (base + '/' + name + '.conf', base + '/redis.conf', base + '/valkey.conf'):
            if os.path.exists(f):
                return f
        return ''

    def conf(self, name):
        conf = {'port': 6379, 'password': '', 'bind': '127.0.0.1', 'databases': 16, 'unixsocket': ''}
        content = mw.readFile(self.confPath(name)) or ''
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split(None, 1)
            if len(parts) != 2:
                continue
            k, v = parts[0].lower(), parts[1].strip().strip('"')
            if k == 'port' and v.isdigit():
                conf['port'] = int(v)
            elif k == 'requirepass':
                conf['password'] = v
            elif k == 'databases' and v.isdigit():
                conf['databases'] = int(v)
            elif k == 'unixsocket':
                conf['unixsocket'] = v
            elif k == 'bind':
                conf['bind'] = v.split()[0]
        return conf

    def client(self, name, db=0):
        if name not in ('redis', 'valkey'):
            raise ValueError('不支持')
        import redis
        c = self.conf(name)
        host = c['bind'] if c['bind'] not in ('0.0.0.0', '*', '::', '') else '127.0.0.1'
        if c['port'] == 0 and c['unixsocket']:
            return redis.Redis(unix_socket_path=c['unixsocket'], password=c['password'] or None, db=db,
                               socket_timeout=5, decode_responses=False)
        return redis.Redis(host=host, port=c['port'], password=c['password'] or None, db=db,
                           socket_timeout=5, socket_connect_timeout=3, decode_responses=False)

    def __db(self, db):
        try:
            db = int(db)
        except (TypeError, ValueError):
            return None
        return db if 0 <= db < 256 else None

    @staticmethod
    def __text(b):
        if b is None:
            return None
        if isinstance(b, (int, float)):
            return str(b)
        try:
            return b.decode('utf-8')
        except UnicodeDecodeError:
            return b.decode('latin-1')

    def getInfo(self, name):
        try:
            r = self.client(name)
            info = r.info()
        except Exception as e:
            return fail('连接失败: ' + str(e)[:200])
        c = self.conf(name)
        dbs = []
        for i in range(c['databases']):
            ks = info.get('db%d' % i)
            dbs.append({'db': i, 'keys': ks['keys'] if ks else 0, 'expires': ks['expires'] if ks else 0})
        hits, misses = info.get('keyspace_hits', 0), info.get('keyspace_misses', 0)
        return ok('OK', {
            'version': info.get('redis_version') or info.get('valkey_version', ''),
            'uptime': info.get('uptime_in_seconds', 0),
            'clients': info.get('connected_clients', 0),
            'used_memory': info.get('used_memory_human', ''),
            'maxmemory': info.get('maxmemory_human', '0B'),
            'peak_memory': info.get('used_memory_peak_human', ''),
            'ops': info.get('instantaneous_ops_per_sec', 0),
            'hit_rate': round(hits * 100.0 / (hits + misses), 2) if hits + misses else 0,
            'total_keys': sum(d['keys'] for d in dbs),
            'port': c['port'],
            'has_password': bool(c['password']),
            'dbs': dbs,
        })

    def scan(self, name, db, pattern='*', cursor=0, count=50):
        db = self.__db(db)
        if db is None:
            return fail('数据库编号不正确')
        pattern = str(pattern or '*')[:200]
        try:
            cursor = int(cursor)
            count = max(10, min(500, int(count)))
        except (TypeError, ValueError):
            return fail('参数不正确')
        try:
            r = self.client(name, db)
            keys = []
            # 一次最多扫描若干轮, 凑够 count 个或扫描完毕
            for _ in range(20):
                cursor, batch = r.scan(cursor=cursor, match=pattern, count=count)
                keys.extend(batch)
                if cursor == 0 or len(keys) >= count:
                    break
            pipe = r.pipeline()
            for k in keys:
                pipe.type(k)
                pipe.ttl(k)
            meta = pipe.execute()
        except Exception as e:
            return fail('读取失败: ' + str(e)[:200])
        items = []
        for i, k in enumerate(keys):
            items.append({'key': self.__text(k), 'type': self.__text(meta[i * 2]), 'ttl': meta[i * 2 + 1]})
        return ok('OK', {'list': items, 'cursor': cursor})

    def getKey(self, name, db, key):
        db = self.__db(db)
        if db is None or not key:
            return fail('参数不正确')
        try:
            r = self.client(name, db)
            kb = key.encode('utf-8')
            t = self.__text(r.type(kb))
            if t == 'none':
                return fail('键不存在或已过期')
            ttl = r.ttl(kb)
            size = 0
            truncated = False
            if t == 'string':
                size = r.strlen(kb)
                raw = r.getrange(kb, 0, MAX_VALUE - 1)
                value = self.__text(raw)
                truncated = size > MAX_VALUE
            elif t == 'hash':
                size = r.hlen(kb)
                value = []
                for f, v in r.hscan_iter(kb, count=100):
                    value.append({'field': self.__text(f), 'value': self.__text(v)})
                    if len(value) >= MAX_ITEMS:
                        truncated = size > MAX_ITEMS
                        break
            elif t == 'list':
                size = r.llen(kb)
                value = [self.__text(v) for v in r.lrange(kb, 0, MAX_ITEMS - 1)]
                truncated = size > MAX_ITEMS
            elif t == 'set':
                size = r.scard(kb)
                value = []
                for v in r.sscan_iter(kb, count=100):
                    value.append(self.__text(v))
                    if len(value) >= MAX_ITEMS:
                        truncated = size > MAX_ITEMS
                        break
            elif t == 'zset':
                size = r.zcard(kb)
                value = [{'member': self.__text(m), 'score': s} for m, s in r.zrange(kb, 0, MAX_ITEMS - 1, withscores=True)]
                truncated = size > MAX_ITEMS
            else:
                value = '(暂不支持查看 %s 类型)' % t
        except Exception as e:
            return fail('读取失败: ' + str(e)[:200])
        return ok('OK', {'key': key, 'type': t, 'ttl': ttl, 'size': size, 'value': value, 'truncated': truncated})

    def setKey(self, name, db, key, value, ttl=-1, key_type='string', field=''):
        db = self.__db(db)
        key = str(key or '')
        if db is None or not key or len(key) > 1024:
            return fail('键名不能为空且不能超过 1024 字节')
        if len(str(value)) > 16 * 1024 * 1024:
            return fail('值过大')
        try:
            ttl = int(ttl)
        except (TypeError, ValueError):
            return fail('过期时间不正确')
        try:
            r = self.client(name, db)
            kb = key.encode('utf-8')
            if key_type == 'string':
                r.set(kb, str(value).encode('utf-8'))
            elif key_type == 'hash':
                if not field:
                    return fail('请输入字段名')
                r.hset(kb, str(field).encode('utf-8'), str(value).encode('utf-8'))
            elif key_type == 'list':
                r.rpush(kb, str(value).encode('utf-8'))
            elif key_type == 'set':
                r.sadd(kb, str(value).encode('utf-8'))
            elif key_type == 'zset':
                try:
                    score = float(field or 0)
                except ValueError:
                    return fail('分值必须是数字')
                r.zadd(kb, {str(value).encode('utf-8'): score})
            else:
                return fail('不支持的类型')
            if ttl > 0:
                r.expire(kb, ttl)
            elif ttl == -1 and key_type == 'string':
                r.persist(kb)
        except Exception as e:
            return fail('保存失败: ' + str(e)[:200])
        return ok('保存成功')

    def setTtl(self, name, db, key, ttl):
        db = self.__db(db)
        if db is None or not key:
            return fail('参数不正确')
        try:
            ttl = int(ttl)
            r = self.client(name, db)
            kb = str(key).encode('utf-8')
            if not r.exists(kb):
                return fail('键不存在')
            if ttl > 0:
                r.expire(kb, ttl)
            else:
                r.persist(kb)
        except (TypeError, ValueError):
            return fail('过期时间不正确')
        except Exception as e:
            return fail('设置失败: ' + str(e)[:200])
        return ok('设置成功')

    def delKeys(self, name, db, keys):
        db = self.__db(db)
        if db is None or not isinstance(keys, list) or not keys or len(keys) > 1000:
            return fail('参数不正确')
        try:
            r = self.client(name, db)
            n = r.delete(*[str(k).encode('utf-8') for k in keys])
        except Exception as e:
            return fail('删除失败: ' + str(e)[:200])
        mw.writeLog('数据库管理', 'Redis db%d 删除 %d 个键' % (db, n))
        return ok('已删除 %d 个键' % n)

    def flushDb(self, name, db):
        db = self.__db(db)
        if db is None:
            return fail('参数不正确')
        try:
            self.client(name, db).flushdb()
        except Exception as e:
            return fail('清空失败: ' + str(e)[:200])
        mw.writeLog('数据库管理', '清空 %s db%d' % (name, db))
        return ok('已清空 db%d' % db)
