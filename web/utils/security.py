# coding:utf-8

# ---------------------------------------------------------------------------------
# PM-Linux面板
# ---------------------------------------------------------------------------------
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------
# 安全相关的公共函数: 密码哈希、登录限流、路径/参数校验
# ---------------------------------------------------------------------------------

import os
import re
import hmac
import time
import hashlib
import secrets

_MD5_RE = re.compile(r'^[0-9a-f]{32}$')
_IDENT_RE = re.compile(r'^[A-Za-z0-9_]+$')
_NAME_RE = re.compile(r'^[A-Za-z0-9_.\-]+$')
_VERSION_RE = re.compile(r'^[A-Za-z0-9_.\-]*$')


# ------------------------------- 常量时间比较 ---------------------------------------

def safe_equals(a, b):
    if a is None or b is None:
        return False
    if isinstance(a, str):
        a = a.encode('utf-8')
    if isinstance(b, str):
        b = b.encode('utf-8')
    return hmac.compare_digest(a, b)


# ------------------------------- 密码哈希 -------------------------------------------

def hash_password(password):
    import bcrypt
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')


def is_legacy_hash(stored):
    return bool(stored) and bool(_MD5_RE.match(stored))


def verify_password(password, stored):
    '''
    校验密码,兼容旧版无盐md5。返回 (是否通过, 是否需要升级哈希)
    '''
    if not stored or password is None:
        return (False, False)
    if is_legacy_hash(stored):
        legacy = hashlib.md5(password.encode('utf-8')).hexdigest()
        ok = safe_equals(legacy, stored)
        return (ok, ok)
    try:
        import bcrypt
        return (bcrypt.checkpw(password.encode('utf-8'), stored.encode('utf-8')), False)
    except Exception:
        return (False, False)


# ------------------------------- 随机数 ---------------------------------------------

def random_string(length, chars='AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz0123456789'):
    return ''.join(secrets.choice(chars) for _ in range(length))


def get_session_secret(data_dir):
    '''
    会话密钥: 首次启动时随机生成并持久化(0600), 多个worker共享同一个文件
    '''
    secret_file = os.path.join(data_dir, 'session_secret.pl')
    if os.path.exists(secret_file):
        with open(secret_file, 'r') as f:
            secret = f.read().strip()
        if len(secret) >= 32:
            return secret
    secret = secrets.token_hex(32)
    fd = os.open(secret_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as f:
        f.write(secret)
    return secret


def restrict_file(path):
    '''敏感文件只允许属主读写'''
    try:
        if os.path.exists(path):
            os.chmod(path, 0o600)
    except Exception:
        pass


# ------------------------------- 登录限流 -------------------------------------------
# 按客户端IP计数,避免任何人通过错误登录把整个面板关闭

LOGIN_MAX_FAILS = 5
LOGIN_LOCK_SECONDS = 3600


def _fail_key(scope, ip):
    return 'login_fail_' + scope + '_' + hashlib.md5(ip.encode('utf-8')).hexdigest()


def login_fail_count(cache, ip, scope='panel'):
    num = cache.get(_fail_key(scope, ip))
    return int(num) if num else 0


def login_is_locked(cache, ip, scope='panel'):
    return login_fail_count(cache, ip, scope) >= LOGIN_MAX_FAILS


def login_record_fail(cache, ip, scope='panel'):
    num = login_fail_count(cache, ip, scope) + 1
    cache.set(_fail_key(scope, ip), num, timeout=LOGIN_LOCK_SECONDS)
    return LOGIN_MAX_FAILS - num


def login_reset(cache, ip, scope='panel'):
    cache.delete(_fail_key(scope, ip))


# ------------------------------- 参数校验 -------------------------------------------

def is_ident(value):
    return isinstance(value, str) and bool(_IDENT_RE.match(value))


def is_safe_name(value):
    '''插件名/文件名: 不允许路径分隔符和 ..'''
    return isinstance(value, str) and bool(_NAME_RE.match(value)) and value not in ('.', '..')


def is_safe_version(value):
    return isinstance(value, str) and bool(_VERSION_RE.match(value))


def is_valid_port(value):
    try:
        port = int(str(value).strip())
    except Exception:
        return False
    return 1 <= port <= 65535


def safe_join(base, *paths):
    '''
    拼接路径并确认结果仍在 base 目录内, 否则返回 None
    '''
    base_real = os.path.realpath(base)
    target = os.path.realpath(os.path.join(base_real, *paths))
    if target == base_real or target.startswith(base_real + os.sep):
        return target
    return None


def ip_in_whitelist(ip, white_list):
    '''
    white_list: 以换行/逗号/空格分隔的IP或CIDR, 为空表示不限制
    '''
    import ipaddress
    if white_list is None:
        return True
    items = [x.strip() for x in re.split(r'[\s,;]+', str(white_list)) if x.strip()]
    if not items:
        return True
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for item in items:
        try:
            if addr in ipaddress.ip_network(item, strict=False):
                return True
        except ValueError:
            continue
    return False
