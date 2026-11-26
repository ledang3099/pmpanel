# coding:utf-8

# ---------------------------------------------------------------------------------
# PM-Linux面板
# ---------------------------------------------------------------------------------
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------

import os
import re
import threading
import fcntl
import ssl
import tempfile
from pathlib import Path
import time
import json

import core.mw as mw
import thisdb

class setting(object):

    # lock
    _instance_lock = threading.Lock()

    @classmethod
    def instance(cls, *args, **kwargs):
        if not hasattr(setting, "_instance"):
            with setting._instance_lock:
                if not hasattr(setting, "_instance"):
                    setting._instance = setting(*args, **kwargs)
        return setting._instance

    def __init__(self):
        pass


    # 保存面板证书
    def savePanelSsl(self, choose, cert_pem, private_key):
        if choose not in ('local', 'nginx'):
            return mw.returnData(False, '未知的证书类型')
        folder = Path(mw.getPanelDir()) / 'ssl' / choose
        if not folder.is_dir():
            return mw.returnData(False, '请先申请证书')
        try:
            with (folder / '.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                key = folder / 'private.pem'
                cert = folder / 'cert.pem'
                if not key.is_file() or not cert.is_file():
                    return mw.returnData(False, '请先申请证书')
                with tempfile.TemporaryDirectory(dir=folder) as staging:
                    staging = Path(staging)
                    new_key = staging / key.name
                    new_cert = staging / cert.name
                    new_key.touch(mode=0o600)
                    new_key.write_text(private_key)
                    new_cert.write_text(cert_pem)
                    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                    context.load_cert_chain(new_cert, new_key, password=lambda: '')
                    previous = staging / 'previous.key'
                    os.link(key, previous, follow_symlinks=False)
                    os.replace(new_key, key)
                    try:
                        os.replace(new_cert, cert)
                    except OSError:
                        os.replace(previous, key)
                        raise
        except (OSError, ValueError):
            return mw.returnData(False, '保存失败，请检查证书、私钥及文件权限')
        return mw.returnData(True, '证书已保存!')

    def getPanelSsl(self):
        rdata = {}
        rdata['choose'] = 'local'


        pdir = mw.getPanelDir()

        keyPath = pdir+'/ssl/local/private.pem'
        certPath = pdir+'/ssl/local/cert.pem'

        if not os.path.exists(certPath):
            mw.createLocalSSL()

        cert = {}
        cert['privateKey'] = mw.readFile(keyPath)
        cert['is_https'] = ''
        cert['certPem'] = mw.readFile(certPath)
        cert['info'] = mw.getCertName(certPath)
        rdata['local'] = cert

        panel_ssl = mw.getServerDir() + "/web_conf/nginx/vhost/panel.conf"
        if not os.path.exists(panel_ssl):
            cert['is_https'] = ''
        else:
            ssl_data = mw.readFile(panel_ssl)
            if ssl_data.find('$server_port !~ 443') != -1:
                cert['is_https'] = 'checked'

        keyPath = pdir+'/ssl/nginx/private.pem'
        certPath = pdir+'/ssl/nginx/cert.pem'

        cert = {}
        cert['privateKey'] = ''
        cert['certPem'] = ''
        cert['info'] = {}
        if os.path.exists(keyPath):
            cert['privateKey'] = mw.readFile(keyPath)

        if os.path.exists(certPath):
            cert['certPem'] = mw.readFile(certPath)
            cert['info'] = mw.getCertName(certPath)

        rdata['nginx'] = cert

        return rdata

    # 删除面板证书
    def delPanelSsl(self, choose):
        if choose not in ('local', 'nginx'):
            return mw.returnData(False, '未知的证书类型')
        config = thisdb.getOptionByJson('panel_ssl', default={'open': False})
        if config.get('open') and config.get('choose', 'local') == choose:
            return mw.returnData(False, '请先关闭面板 SSL，再删除正在使用的证书')
        folder = Path(mw.getPanelDir()) / 'ssl' / choose
        if folder.is_dir():
            try:
                with (folder / '.lock').open('a') as lock:
                    fcntl.flock(lock, fcntl.LOCK_EX)
                    for name in ('cert.pem', 'private.pem'):
                        try:
                            (folder / name).unlink()
                        except FileNotFoundError:
                            pass
            except OSError:
                return mw.returnData(False, '删除失败，请检查证书文件权限')
        return mw.returnData(True, '证书已删除!')

    # 面板本地SSL设置
    def setPanelLocalSsl(self, cert_type):
        panel_ssl_data = thisdb.getOptionByJson('panel_ssl', default={'open':False})

        if not panel_ssl_data['open']:
            panel_ssl_data['open'] = True

        pdir = mw.getPanelDir()
        cert = {}
        keyPath = pdir+'/ssl/local/private.pem'
        certPath = pdir+'/ssl/local/cert.pem'
        if not os.path.exists(certPath):
            mw.createLocalSSL()

        panel_ssl_data['choose'] = 'local'
        thisdb.setOption('panel_ssl', json.dumps(panel_ssl_data))
        mw.restartMw()
        return mw.returnData(True, '设置成功')

    def closePanelSsl(self):
        panel_ssl_data = thisdb.getOptionByJson('panel_ssl', default={'open':False})

        if panel_ssl_data['open']:
            panel_ssl_data['open'] = False

        thisdb.setOption('panel_ssl', json.dumps(panel_ssl_data))
        mw.restartMw()
        return mw.returnData(True, '设置成功')


    # 申请面板let证书
    # def applyPanelAcmeSsl(self):
    #     bind_domain = self.__file['bind_domain']
    #     if not os.path.exists(bind_domain):
    #         return mw.returnJson(False, '先要绑定域名!')

    #     # 生成nginx配置
    #     domain = mw.readFile(bind_domain)
    #     panel_tpl = mw.getRunDir() + "/data/tpl/nginx_panel.conf"
    #     dst_panel_path = mw.getServerDir() + "/web_conf/nginx/vhost/panel.conf"
    #     if not os.path.exists(dst_panel_path):
    #         reg = r"^([\w\-\*]{1,100}\.){1,4}(\w{1,10}|\w{1,10}\.\w{1,10})$"
    #         if not re.match(reg, domain):
    #             return mw.returnJson(False, '主域名格式不正确')

    #         op_dir = mw.getServerDir() + "/openresty"
    #         if not os.path.exists(op_dir):
    #             return mw.returnJson(False, '依赖OpenResty,先安装启动它!')

    #         content = mw.readFile(panel_tpl)
    #         content = content.replace("{$PORT}", "80")
    #         content = content.replace("{$SERVER_NAME}", domain)
    #         content = content.replace("{$PANAL_PORT}", mw.readFile('data/port.pl'))
    #         content = content.replace("{$LOGPATH}", mw.getRunDir() + '/logs')
    #         content = content.replace("{$PANAL_ADDR}", mw.getRunDir())
    #         mw.writeFile(dst_panel_path, content)
    #         mw.restartNginx()

    #     siteName = mw.readFile(bind_domain).strip()
    #     auth_to = mw.getRunDir() + "/tmp"
    #     to_args = {
    #         'domains': [siteName],
    #         'auth_type': 'http',
    #         'auth_to': auth_to,
    #     }

    #     src_path = mw.getServerDir() + '/web_conf/letsencrypt/' + siteName
    #     src_csrpath = src_path + "/fullchain.pem"  # 生成证书路径
    #     src_keypath = src_path + "/privkey.pem"  # 密钥文件路径

    #     dst_path = mw.getRunDir() + '/ssl/nginx'
    #     dst_csrpath = dst_path + '/cert.pem'
    #     dst_keypath = dst_path + '/private.pem'

    #     is_already_apply = False

    #     if not os.path.exists(src_path):
    #         import cert_api
    #         data = cert_api.cert_api().applyCertApi(to_args)
    #         if not data['status']:
    #             msg = data['msg']
    #             if type(data['msg']) != str:
    #                 msg = data['msg'][0]
    #                 emsg = data['msg'][1]['challenges'][0]['error']
    #                 msg = msg + '<p><span>响应状态:</span>' + str(emsg['status']) + '</p><p><span>错误类型:</span>' + emsg[
    #                     'type'] + '</p><p><span>错误代码:</span>' + emsg['detail'] + '</p>'
    #             return mw.returnJson(data['status'], msg, data['msg'])
    #     else:
    #         is_already_apply = True

    #     mw.buildSoftLink(src_csrpath, dst_csrpath, True)
    #     mw.buildSoftLink(src_keypath, dst_keypath, True)
    #     mw.execShell('echo "acme" > "' + dst_path + '/README"')

    #     tmp_well_know = auth_to + '/.well-known'
    #     if os.path.exists(tmp_well_know):
    #         mw.execShell('rm -rf ' + tmp_well_know)

    #     if os.path.exists(dst_path):
    #         choose_file = self.__file['ssl']
    #         mw.writeFile(choose_file, 'nginx')

    #     data = self.getPanelSslData()

    #     if is_already_apply:
    #         return mw.returnJson(True, '重复申请!', data)
    #     return mw.returnJson(True, '申请成功!', data)

    def setPanelDomain(self, domain):
        port = mw.getPanelPort()
        
        domain = domain.strip().rstrip('.').lower()
        if domain and (len(domain) > 253 or not all(
            re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', part)
            for part in domain.split('.')
        )):
            return mw.returnData(False, '请输入域名，不包含协议、端口或路径')
        from flask import request
        scheme = request.scheme
        if domain == '':
            ip = mw.getLocalIp()
            client_ip = mw.getClientIp()
            if client_ip in ['127.0.0.1', 'localhost', '::1']:
                ip = client_ip

            to_panel_url = scheme+'://'+ip+":"+str(port)+'/setting/index'
            thisdb.setOption('panel_domain', '')
            return mw.returnData(True, '清空域名成功!', to_panel_url)

        thisdb.setOption('panel_domain', domain)
        to_panel_url = scheme+'://'+domain+":"+str(port)+'/setting/index'
        return mw.returnData(True, '设置域名成功!',to_panel_url)


