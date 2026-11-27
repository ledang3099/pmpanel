# coding: utf-8

# ---------------------------------------------------------------------------------
# PM-Linux面板 ModSecurity 防火墙(ModSecurity v3 + OWASP 核心规则集 CRS 4)
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------
# 目录:
#   {server}/modsecurity/libmodsecurity   libmodsecurity 程序库
#   {server}/modsecurity/crs              OWASP CRS 规则集
#   {server}/modsecurity/conf             本插件生成的配置(main.conf 等)
#   {server}/modsecurity/logs             审计日志(JSON, 每行一条)
#   {server}/modsecurity/settings.json    面板设置
# OpenResty:
#   web_conf/nginx/modules/modsecurity.conf   load_module(主配置 main 上下文)
#   web_conf/nginx/vhost/0.modsecurity.conf   http 级别开关
#   各站点 server 块中 #MODSECURITY-START ... #MODSECURITY-END 段: 单站点覆盖
# ---------------------------------------------------------------------------------

import os
import re
import sys
import json
import time
import shutil
import ipaddress
import subprocess

web_dir = os.getcwd() + "/web"
if os.path.exists(web_dir):
    sys.path.append(web_dir)
    os.chdir(web_dir)

import core.mw as mw

MODULE_FILE = 'ngx_http_modsecurity_module.so'
ENGINES = ('On', 'DetectionOnly')
SITE_MODES = ('inherit', 'off', 'detect')
SITE_START = '#MODSECURITY-START'
SITE_END = '#MODSECURITY-END'


def ok(msg='OK', data=None):
    return {'status': True, 'msg': msg, 'data': data}


def fail(msg, data=None):
    return {'status': False, 'msg': msg, 'data': data}


def getPluginName():
    return 'modsecurity'


def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()


def orDir():
    return mw.getServerDir() + '/openresty'


def nginxBin():
    return orDir() + '/nginx/sbin/nginx'


def nginxConf():
    return orDir() + '/nginx/conf/nginx.conf'


def moduleSo():
    return orDir() + '/nginx/modules/' + MODULE_FILE


def webConfDir():
    return mw.getServerDir() + '/web_conf/nginx'


def loadConf():
    return webConfDir() + '/modules/modsecurity.conf'


def httpConf():
    return webConfDir() + '/vhost/0.modsecurity.conf'


def mainConf():
    return getServerDir() + '/conf/main.conf'


def auditLog():
    return getServerDir() + '/logs/audit.log'


# ------------------------------- 设置 -------------------------------------------

def defaultSettings():
    return {
        'enabled': True,
        'engine': 'DetectionOnly',     # 新安装默认"仅记录", 确认没有误报后再切换为拦截
        'paranoia': 1,                 # CRS 严格等级 1-4, 越高越严格, 误报也越多
        'inbound_threshold': 5,        # 请求异常评分阈值(CRS 默认 5)
        'outbound_threshold': 4,       # 响应异常评分阈值(CRS 默认 4)
        'body_limit_kb': 12800,        # 允许检测的请求体大小
        'ip_whitelist': [],
        'disabled_rules': [],
        'sites': {},                   # 站点名 -> inherit/off/detect
    }


def settingsPath():
    return getServerDir() + '/settings.json'


def getSettings():
    data = None
    if os.path.exists(settingsPath()):
        try:
            data = json.loads(mw.readFile(settingsPath()))
        except Exception:
            data = None
    base = defaultSettings()
    if isinstance(data, dict):
        base.update(data)
    return base


def saveSettings(data):
    tmp = settingsPath() + '.tmp'
    with open(tmp, 'w') as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2))
    os.replace(tmp, settingsPath())


# ------------------------------- 版本信息 ---------------------------------------

def readVersion(name):
    path = getServerDir() + '/' + name + '.pl'
    return (mw.readFile(path) or '').strip() if os.path.exists(path) else ''


def openrestyV():
    if not os.path.exists(nginxBin()):
        return ''
    p = subprocess.run([nginxBin(), '-V'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.stdout.decode('utf-8', 'ignore')


def installPreInspection():
    out = openrestyV()
    if out == '':
        return '请先安装 OpenResty'
    if '--with-compat' not in out:
        return '当前 OpenResty 编译时未启用 --with-compat, 无法加载防火墙模块。请先在应用市场中升级/重装 OpenResty(1.29.2 或 1.31)'
    return 'ok'


# ------------------------------- 配置生成 ---------------------------------------

def writeFile(path, content, mode=None):
    d = os.path.dirname(path)
    if not os.path.exists(d):
        os.makedirs(d)
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        f.write(content)
    if mode is not None:
        os.chmod(tmp, mode)
    os.replace(tmp, path)


def secQuote(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"') + '"'


def writeRuleConfig(s=None):
    if s is None:
        s = getSettings()
    sd = getServerDir()
    conf_dir = sd + '/conf'
    log_dir = sd + '/logs'
    for d in (conf_dir, log_dir, sd + '/tmp'):
        if not os.path.exists(d):
            os.makedirs(d)
    # 审计日志由 nginx worker(www) 写入
    if not mw.isAppleSystem():
        for d in (log_dir, sd + '/tmp'):
            try:
                shutil.chown(d, 'www', 'www')
            except Exception:
                pass

    body = int(s.get('body_limit_kb', 12800)) * 1024
    engine = s['engine'] if s.get('engine') in ENGINES else 'DetectionOnly'

    # 基础引擎配置(参考 ModSecurity 官方 modsecurity.conf-recommended)
    base = '\n'.join([
        '# 由 PM 面板生成, 请在面板中修改',
        'SecRuleEngine ' + engine,
        'SecRequestBodyAccess On',
        'SecRequestBodyLimit %d' % body,
        'SecRequestBodyNoFilesLimit %d' % min(body, 1048576),
        'SecRequestBodyLimitAction Reject',
        'SecRequestBodyJsonDepthLimit 512',
        'SecArgumentsLimit 1000',
        'SecResponseBodyAccess On',
        'SecResponseBodyMimeType text/plain text/html text/xml application/json',
        'SecResponseBodyLimit 524288',
        'SecResponseBodyLimitAction ProcessPartial',
        'SecTmpDir ' + sd + '/tmp',
        'SecDataDir ' + sd + '/tmp',
        'SecPcreMatchLimit 100000',
        'SecPcreMatchLimitRecursion 100000',
        'SecAuditEngine RelevantOnly',
        'SecAuditLogRelevantStatus "^(?:5|4(?!04))"',
        'SecAuditLogParts ABHZ',
        'SecAuditLogType Serial',
        'SecAuditLogFormat JSON',
        'SecAuditLog ' + auditLog(),
        'SecArgumentSeparator &',
        'SecCookieFormat 0',
        'SecUnicodeMapFile ' + sd + '/conf/unicode.mapping 20127',
        'SecStatusEngine Off',
        # 请求体解析失败时拒绝(防止利用解析差异绕过检测)
        'SecRule REQBODY_ERROR "!@eq 0" "id:200002,phase:2,t:none,log,deny,status:400,msg:\'Failed to parse request body.\'"',
        '',
    ])
    writeFile(conf_dir + '/modsecurity.conf', base)

    # CRS 参数(在 crs-setup.conf 之后加载, 覆盖默认值)
    pl = int(s.get('paranoia', 1))
    setup = [
        '# 由 PM 面板生成',
        'SecAction "id:900000,phase:1,pass,t:none,nolog,tag:\'OWASP_CRS\',ver:\'OWASP_CRS/4\',setvar:tx.blocking_paranoia_level=%d"' % pl,
        'SecAction "id:900110,phase:1,pass,t:none,nolog,tag:\'OWASP_CRS\',ver:\'OWASP_CRS/4\',setvar:tx.inbound_anomaly_score_threshold=%d,setvar:tx.outbound_anomaly_score_threshold=%d"' % (
            int(s.get('inbound_threshold', 5)), int(s.get('outbound_threshold', 4))),
    ]
    wl = s.get('ip_whitelist', [])
    if wl:
        # 白名单IP: 关闭检测
        setup.append('SecRule REMOTE_ADDR "@ipMatch %s" "id:1000001,phase:1,pass,nolog,ctl:ruleRemoveByTag=OWASP_CRS,ctl:auditEngine=Off"' % ','.join(wl))
    writeFile(conf_dir + '/pm-setup.conf', '\n'.join(setup) + '\n')

    after = ['# 由 PM 面板生成: 已停用的规则']
    for rid in s.get('disabled_rules', []):
        after.append('SecRuleRemoveById %d' % int(rid))
    writeFile(conf_dir + '/pm-after.conf', '\n'.join(after) + '\n')

    crs = sd + '/crs'
    main = [
        '# 由 PM 面板生成',
        'Include ' + conf_dir + '/modsecurity.conf',
        'Include ' + crs + '/crs-setup.conf',
        'Include ' + conf_dir + '/pm-setup.conf',
    ]
    if os.path.isdir(crs + '/plugins'):
        for kind in ('config', 'before'):
            if any(f.endswith('-' + kind + '.conf') for f in os.listdir(crs + '/plugins')):
                main.append('Include ' + crs + '/plugins/*-' + kind + '.conf')
    main.append('Include ' + crs + '/rules/*.conf')
    if os.path.isdir(crs + '/plugins') and any(f.endswith('-after.conf') for f in os.listdir(crs + '/plugins')):
        main.append('Include ' + crs + '/plugins/*-after.conf')
    main.append('Include ' + conf_dir + '/pm-after.conf')
    writeFile(mainConf(), '\n'.join(main) + '\n')


def ensureNginxInclude():
    '''
    nginx.conf 主上下文中引入 web_conf/nginx/modules/*.conf, 用于 load_module
    (只插入一次; 新版 OpenResty 模板已自带)
    '''
    conf = mw.readFile(nginxConf()) or ''
    inc = 'include ' + webConfDir() + '/modules/*.conf;'
    if inc in conf:
        return True
    lines = conf.split('\n')
    pos = 0
    for i, line in enumerate(lines):
        if re.match(r'^\s*(user|worker_processes|pid|error_log)\b', line):
            pos = i + 1
    lines.insert(pos, inc)
    mw.writeFile(nginxConf(), '\n'.join(lines))
    return True


def vhostFiles():
    d = webConfDir() + '/vhost'
    if not os.path.isdir(d):
        return []
    res = []
    for f in sorted(os.listdir(d)):
        if f.endswith('.conf') and not f.startswith('0.'):
            res.append(d + '/' + f)
    return res


def siteNameOf(path):
    return os.path.basename(path)[:-5]


def setSiteBlock(path, mode):
    content = mw.readFile(path) or ''
    content = re.sub(r'\n?[ \t]*' + SITE_START + r'.*?' + SITE_END + r'[^\n]*', '', content, flags=re.S)
    if mode in ('off', 'detect'):
        if mode == 'off':
            directive = '    modsecurity off;'
        else:
            directive = "    modsecurity_rules 'SecRuleEngine DetectionOnly';"
        block = '\n    ' + SITE_START + '\n' + directive + '\n    ' + SITE_END
        # 只插入到第一个 server 块: 放在 server_name 行之后
        m = re.search(r'(\n[ \t]*server_name[^\n]*;)', content)
        if m:
            content = content[:m.end()] + block + content[m.end():]
    mw.writeFile(path, content)


def applySites(s=None, active=True):
    if s is None:
        s = getSettings()
    sites = s.get('sites', {})
    for path in vhostFiles():
        mode = sites.get(siteNameOf(path), 'inherit') if active else 'inherit'
        setSiteBlock(path, mode)


def writeNginxFiles(active):
    if active:
        ensureNginxInclude()
        writeFile(loadConf(), 'load_module ' + moduleSo() + ';\n')
        writeFile(httpConf(), '# 由 PM 面板生成: ModSecurity 防火墙\nmodsecurity on;\nmodsecurity_rules_file ' + mainConf() + ';\n')
    else:
        for p in (httpConf(), loadConf()):
            if os.path.exists(p):
                os.remove(p)


def nginxTest():
    if not os.path.exists(nginxBin()):
        return (False, 'OpenResty 未安装')
    p = subprocess.run([nginxBin(), '-t', '-c', nginxConf()], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = p.stdout.decode('utf-8', 'ignore')
    return ('test is successful' in out, out)


def backupFiles():
    files = [nginxConf(), loadConf(), httpConf()] + vhostFiles()
    backup = {}
    for f in files:
        backup[f] = mw.readFile(f) if os.path.exists(f) else None
    return backup


def restoreFiles(backup):
    for f, content in backup.items():
        if content is None:
            if os.path.exists(f):
                os.remove(f)
        else:
            mw.writeFile(f, content)


def workerPids():
    '''当前 OpenResty master 的 worker 进程号'''
    pid = (mw.readFile(orDir() + '/nginx/logs/nginx.pid') or '').strip()
    res = set()
    if not pid.isdigit():
        return res
    for d in os.listdir('/proc'):
        if not d.isdigit():
            continue
        try:
            with open('/proc/' + d + '/stat') as f:
                st = f.read()
            ppid = st[st.rfind(')') + 2:].split()[1]
            if ppid == pid:
                res.add(d)
        except (IOError, OSError, IndexError):
            continue
    return res


def reloadAndWait(timeout=20):
    '''
    重新加载 OpenResty 并等待新 worker 启动(加载 CRS 规则需要数秒),
    使"已生效"的提示与实际状态一致
    '''
    old = workerPids()
    mw.restartWeb()
    if not old:
        return
    end = time.time() + timeout
    while time.time() < end:
        time.sleep(0.3)
        # 新 worker 数量达到原数量即视为加载完成
        if len(workerPids() - old) >= len(old):
            break
    # 旧 worker 收到退出信号前仍可能接收新连接, 再等待其退出(长连接最多等 3 秒)
    end = min(end, time.time() + 3)
    while time.time() < end and (workerPids() & old):
        time.sleep(0.1)


def applyAll(s=None):
    '''
    根据设置写入全部配置并测试 nginx 配置; 失败时还原, 不影响网站运行
    '''
    if s is None:
        s = getSettings()
    active = bool(s.get('enabled')) and os.path.exists(moduleSo())
    backup = backupFiles()
    try:
        writeRuleConfig(s)
        writeNginxFiles(active)
        applySites(s, active)
    except Exception as e:
        restoreFiles(backup)
        return fail('写入配置失败: ' + str(e))
    good, out = nginxTest()
    if not good:
        restoreFiles(backup)
        return fail('OpenResty 配置测试未通过, 已还原: ' + out[-600:])
    reloadAndWait()
    return ok('已生效')


# ------------------------------- 服务(命令行) -----------------------------------

def status():
    s = getSettings()
    if s.get('enabled') and os.path.exists(loadConf()) and os.path.exists(httpConf()):
        return 'start'
    return 'stop'


def start():
    s = getSettings()
    s['enabled'] = True
    saveSettings(s)
    r = applyAll(s)
    return 'ok' if r['status'] else r['msg']


def stop():
    s = getSettings()
    s['enabled'] = False
    saveSettings(s)
    r = applyAll(s)
    return 'ok' if r['status'] else r['msg']


def restart():
    return start()


def reload():
    r = applyAll()
    return 'ok' if r['status'] else r['msg']


def site_hook():
    # 站点增删改后重新应用单站点设置(删除的站点从设置中移除)
    s = getSettings()
    names = set(siteNameOf(p) for p in vhostFiles())
    s['sites'] = {k: v for k, v in s.get('sites', {}).items() if k in names}
    saveSettings(s)
    if status() == 'start':
        applySites(s, True)
        good, out = nginxTest()
        if good:
            mw.restartWeb()
    return 'ok'


def uninstall_clean():
    s = getSettings()
    applySites(s, False)
    writeNginxFiles(False)
    good, out = nginxTest()
    if good:
        mw.restartWeb()
    return 'ok'


# ------------------------------- 面板接口 ---------------------------------------

def get_info(args=None):
    s = getSettings()
    out = openrestyV()
    m = re.search(r'openresty/(\S+)', out)
    info = {
        'settings': s,
        'status': status(),
        'module': os.path.exists(moduleSo()),
        'openresty': m.group(1) if m else '',
        'compat': '--with-compat' in out,
        'module_for': readVersion('module_for'),
        'libmodsecurity': readVersion('libmodsecurity'),
        'connector': readVersion('connector'),
        'crs': readVersion('crs'),
    }
    info['module_mismatch'] = info['module'] and info['module_for'] != '' and info['openresty'] != '' and info['module_for'] != info['openresty']
    return ok('OK', info)


def saveAndApply(s, msg):
    '''保存设置并应用; 应用失败时恢复原设置, 保证设置与运行中的配置一致'''
    old = getSettings()
    saveSettings(s)
    r = applyAll(s)
    if not r['status']:
        saveSettings(old)
        return r
    return ok(msg)


def set_config(args):
    args = args or {}
    s = getSettings()
    if 'engine' in args:
        if args['engine'] not in ENGINES:
            return fail('工作模式不正确')
        s['engine'] = args['engine']
    for key, low, high in (('paranoia', 1, 4), ('inbound_threshold', 1, 1000), ('outbound_threshold', 1, 1000), ('body_limit_kb', 64, 1048576)):
        if key in args:
            try:
                v = int(str(args[key]).strip())
            except ValueError:
                return fail('%s 参数不正确' % key)
            if v < low or v > high:
                return fail('%s 取值范围为 %d-%d' % (key, low, high))
            s[key] = v
    if 'ip_whitelist' in args:
        items = [x.strip() for x in re.split(r'[\s,;]+', str(args['ip_whitelist'])) if x.strip()]
        res = []
        for it in items:
            try:
                net = ipaddress.ip_network(it, strict=False)
            except ValueError:
                return fail('白名单IP格式不正确: ' + it[:60])
            res.append(str(net) if net.num_addresses > 1 else str(net.network_address))
        s['ip_whitelist'] = res
    if 'disabled_rules' in args:
        items = [x.strip() for x in re.split(r'[\s,;]+', str(args['disabled_rules'])) if x.strip()]
        res = []
        for it in items:
            if not re.match(r'^\d{1,9}$', it):
                return fail('规则ID格式不正确: ' + it[:30])
            res.append(int(it))
        s['disabled_rules'] = sorted(set(res))
    return saveAndApply(s, '保存成功')


def site_list(args=None):
    s = getSettings()
    res = []
    for p in vhostFiles():
        name = siteNameOf(p)
        res.append({'name': name, 'mode': s.get('sites', {}).get(name, 'inherit')})
    return ok('OK', res)


def set_site(args):
    args = args or {}
    name = str(args.get('name', ''))
    mode = str(args.get('mode', 'inherit'))
    if mode not in SITE_MODES:
        return fail('参数错误')
    if name not in set(siteNameOf(p) for p in vhostFiles()):
        return fail('站点不存在')
    s = getSettings()
    if mode == 'inherit':
        s['sites'].pop(name, None)
    else:
        s['sites'][name] = mode
    return saveAndApply(s, '已生效')


def parseAudit(line):
    try:
        d = json.loads(line)
    except ValueError:
        return None
    t = d.get('transaction', {})
    req = t.get('request', {})
    headers = req.get('headers', {}) or {}
    host = headers.get('Host') or headers.get('host') or ''
    msgs = []
    for m in t.get('messages', []) or []:
        det = m.get('details', {}) or {}
        rid = det.get('ruleId', '')
        # 949110/959100 为异常评分汇总规则, 不单独展示
        msgs.append({'id': rid, 'msg': m.get('message', ''), 'data': (det.get('data') or '')[:200], 'severity': det.get('severity', '')})
    resp = t.get('response', {}) or {}
    return {
        'time': t.get('time_stamp', ''),
        'ip': t.get('client_ip', ''),
        'host': host,
        'method': req.get('method', ''),
        'uri': (req.get('uri') or '')[:300],
        'status': resp.get('http_code', ''),
        'intercepted': any(str(m['id']) in ('949110', '959100', '200002') for m in msgs) or str(resp.get('http_code', '')) == '403',
        'rules': msgs[:20],
    }


def tailLines(path, num, max_bytes=8 * 1024 * 1024):
    '''读取文件最后 num 行(审计日志为单行 JSON, 不能做 HTML 转义)'''
    with open(path, 'rb') as f:
        f.seek(0, 2)
        end = f.tell()
        block = 65536
        data = b''
        pos = end
        while pos > 0 and data.count(b'\n') <= num and end - pos < max_bytes:
            step = min(block, pos)
            pos -= step
            f.seek(pos)
            data = f.read(step) + data
    lines = data.decode('utf-8', 'ignore').split('\n')
    if pos > 0:
        lines = lines[1:]
    return lines[-num - 1:]


def get_logs(args=None):
    args = args or {}
    limit = 100
    try:
        limit = max(1, min(500, int(args.get('limit', 100))))
    except ValueError:
        pass
    path = auditLog()
    if not os.path.exists(path):
        return ok('OK', {'list': [], 'size': 0})
    size = os.path.getsize(path)
    lines = tailLines(path, limit)
    res = []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        item = parseAudit(line)
        # 只展示命中规则的请求(其余为普通 4xx/5xx 响应)
        if item and item['rules']:
            res.append(item)
    return ok('OK', {'list': res, 'size': size})


def clear_logs(args=None):
    path = auditLog()
    if os.path.exists(path):
        with open(path, 'w'):
            pass
    return ok('日志已清空')


def disable_rule(args):
    rid = str((args or {}).get('id', ''))
    if not re.match(r'^\d{1,9}$', rid):
        return fail('规则ID格式不正确')
    s = getSettings()
    rules = set(s.get('disabled_rules', []))
    rules.add(int(rid))
    s['disabled_rules'] = sorted(rules)
    return saveAndApply(s, '已停用规则 ' + rid)


if __name__ == "__main__":
    func = sys.argv[1]
    if func == 'status':
        print(status())
    elif func == 'start':
        print(start())
    elif func == 'stop':
        print(stop())
    elif func == 'restart':
        print(restart())
    elif func == 'reload':
        print(reload())
    elif func == 'install_pre_inspection':
        print(installPreInspection())
    elif func == 'site_hook':
        print(site_hook())
    elif func == 'init':
        if not os.path.exists(settingsPath()):
            saveSettings(defaultSettings())
        print(applyAll()['msg'])
    elif func == 'uninstall_clean':
        print(uninstall_clean())
    else:
        print('error')
