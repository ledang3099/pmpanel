# coding:utf-8

# ---------------------------------------------------------------------------------
# PM-Linux面板
# ---------------------------------------------------------------------------------
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------

import os
import threading
import re
import time


import core.mw as mw
import thisdb

class Firewall(object):

    __isFirewalld = False
    __isIptables = False
    __isUfw = False
    __isMac = False

    # lock
    _instance_lock = threading.Lock()

    @classmethod
    def instance(cls, *args, **kwargs):
        if not hasattr(Firewall, "_instance"):
            with Firewall._instance_lock:
                if not hasattr(Firewall, "_instance"):
                    Firewall._instance = Firewall(*args, **kwargs)
        return Firewall._instance

    def __init__(self):
        iptables_file = mw.systemdCfgDir() + '/iptables.service'
        if os.path.exists('/usr/sbin/firewalld'):
            self.__isFirewalld = True
        elif os.path.exists('/usr/sbin/ufw'):
            self.__isUfw = True
        elif os.path.exists(iptables_file):
            self.__isIptables = True
        elif mw.isAppleSystem():
            self.__isMac = True

    # 自动识别防火墙配置 | Automatically identify firewall
    def aIF(self):
        if self.__isFirewalld:
            self.AIF_Firewalld()
        if self.__isUfw:
            self.aIF_Ufw()


    def aIF_Ufw(self):
        t = mw.execShell("ufw status|awk '{print $1}' | grep -v 'Status'|grep -v 'To'|grep -v '-'")
        if t[1] != '':
            return True

        all_port = t[0].strip()
        ports_list = all_port.split('\n')


        ports_all = []
        for pinfo in ports_list:
            if pinfo.strip() == "":
                continue

            info = pinfo.split('/')
            if len(info) != 2:
                continue

            is_same = False
            for i in range(len(ports_all)):
                if ports_all[i]['port'] == info[0] and ports_all[i]['protocol'] != info[1]:
                    ports_all[i]['protocol'] = ports_all[i]['protocol']+'/'+info[1]
                    is_same = True

            if not is_same:
                t = {}
                t['port'] = info[0].replace('-',':')
                t['protocol'] = info[1]
                ports_all.append(t)
        for add_info in ports_all:
            if thisdb.getFirewallCountByPort(add_info['port']) == 0:
                thisdb.addFirewall(add_info['port'], ps='自动识别',protocol=add_info['protocol'])

    def AIF_Firewalld(self):
        t = mw.execShell("firewall-cmd --list-all | grep '  ports'")
        if t[1] != '':
            return True

        all_port = t[0].strip()
        data = all_port.split(":")
        ports_str = data[1]
        ports_list = ports_str.strip().split(' ')

        ports_all = []
        for pinfo in ports_list:
            info = pinfo.split('/')

            is_same = False
            for i in range(len(ports_all)):
                if ports_all[i]['port'] == info[0] and ports_all[i]['protocol'] != info[1]:
                    ports_all[i]['protocol'] = ports_all[i]['protocol']+'/'+info[1]
                    is_same = True

            if not is_same:
                t = {}
                t['port'] = info[0].replace('-',':')
                t['protocol'] = info[1]
                ports_all.append(t)

        for add_info in ports_all:
            if thisdb.getFirewallCountByPort(add_info['port']) == 0:
                thisdb.addFirewall(add_info['port'], ps='自动识别',protocol=add_info['protocol'])

    def getList(self, page=1,size=10):
        info = thisdb.getFirewallList(page=page, size=size)

        rdata = {}
        rdata['data'] = info['list']
        rdata['count'] = info['count']
        rdata['page'] = mw.getPage({'count':info['count'],'tojs':'showAccept','p':page,'row':size})
        return rdata

    def reload(self):
        if self.__isUfw:
            mw.execShell('/usr/sbin/ufw reload')
            return
        elif self.__isIptables:
            mw.execShell('service iptables save')
            mw.execShell('service iptables restart')
        elif self.__isFirewalld:
            mw.execShell('firewall-cmd --reload')
        else:
            pass

    def getFwStatus(self):
        if self.__isUfw:
            cmd = "/usr/sbin/ufw status| grep Status | awk -F ':' '{print $2}'"
            data = mw.execShell(cmd)
            if data[0].strip() == 'inactive':
                return False
            return True
        elif self.__isIptables:
            cmd = "systemctl status iptables | grep 'inactive'"
            data = mw.execShell(cmd)
            if data[0] != '':
                return False
            return True
        elif self.__isFirewalld:
            cmd = "ps -ef|grep firewalld |grep -v grep | awk '{print $2}'"
            data = mw.execShell(cmd)
            if data[0] == '':
                return False
            return True
        else:
            return False


    def setFw(self, status):
        if self.__isIptables:
            self.setFwIptables(status)
            return mw.returnData(True, '设置成功!')

        if status == '1':
            if self.__isUfw:
                mw.execShell('/usr/sbin/ufw disable')
            elif self.__isFirewalld:
                mw.execShell('systemctl stop firewalld.service')
                mw.execShell('systemctl disable firewalld.service')
            else:
                pass
        else:
            if self.__isUfw:
                mw.execShell("echo 'y'| ufw enable")
            elif self.__isFirewalld:
                mw.execShell('systemctl start firewalld.service')
                mw.execShell('systemctl enable firewalld.service')
            else:
                pass
        return mw.returnData(True, '设置成功!')

    def setFwIptables(self, status):
        # status == '1' 表示关闭
        if status == '1':
            mw.execShell('systemctl stop iptables.service')
            mw.execShell('systemctl disable iptables.service')
        else:
            mw.execShell('systemctl start iptables.service')
            mw.execShell('systemctl enable iptables.service')

    def addAcceptPortCmd(self, port, protocol ='tcp'):
        # 端口只允许 "端口" 或 "起始:结束" 格式, 防止命令注入
        port = str(port).strip()
        if not re.match(r'^\d{1,5}([:-]\d{1,5})?$', port) or protocol not in ('tcp', 'udp', 'tcp/udp'):
            return False
        if self.__isUfw:
            if protocol == 'tcp':
                mw.execShell('ufw allow ' + port + '/tcp')
            if protocol == 'udp':
                mw.execShell('ufw allow ' + port + '/udp')
            if protocol == 'tcp/udp':
                mw.execShell('ufw allow ' + port + '/tcp')
                mw.execShell('ufw allow ' + port + '/udp')
        elif self.__isFirewalld:
            port = port.replace(':', '-')
            if protocol == 'tcp':
                cmd = 'firewall-cmd --permanent --zone=public --add-port=' + port + '/tcp'
                mw.execShell(cmd)
            if protocol == 'udp':
                cmd = 'firewall-cmd --permanent --zone=public --add-port=' + port + '/udp'
                mw.execShell(cmd)
            if protocol == 'tcp/udp':
                cmd = 'firewall-cmd --permanent --zone=public --add-port=' + port + '/tcp'
                mw.execShell(cmd)
                cmd = 'firewall-cmd --permanent --zone=public --add-port=' + port + '/udp'
                mw.execShell(cmd)
        elif self.__isIptables:
            if protocol == 'tcp':
                cmd = 'iptables -I INPUT -p tcp -m state --state NEW -m tcp --dport ' + port + ' -j ACCEPT'
                mw.execShell(cmd)
            if protocol == 'udp':
                cmd = 'iptables -I INPUT -p udp -m state --state NEW -m udp --dport ' + port + ' -j ACCEPT'
                mw.execShell(cmd)
            if protocol == 'tcp/udp':
                cmd = 'iptables -I INPUT -p tcp -m state --state NEW -m tcp --dport ' + port + ' -j ACCEPT'
                mw.execShell(cmd)
                cmd = 'iptables -I INPUT -p udp -m state --state NEW -m udp --dport ' + port + ' -j ACCEPT'
                mw.execShell(cmd)
        else:
            pass
        return True

    # 添加放行端口
    def addAcceptPort(self, port, ps, stype,
        protocol='tcp'
    ):
        if not re.match(r'^\d{1,5}([:-]\d{1,5})?$', str(port).strip()):
            return mw.returnData(False, '端口格式不正确!')
        if not self.getFwStatus():
            self.setFw(0)
            return mw.returnData(False, '防火墙启动时,才能添加规则!')

        rep = r"^\d{1,5}(:\d{1,5})?$"
        if not re.search(rep, port):
            return mw.returnData(False, '端口范围不正确!')

        if thisdb.getFirewallCountByPort(port) > 0:
            return mw.returnData(False, '您要放行的端口已存在，无需重复放行!')

        thisdb.addFirewall(port, ps=ps,protocol=protocol)
        self.addAcceptPortCmd(port, protocol=protocol)
        self.reload()
        
        msg = mw.getInfo('放行端口[{1}][{2}]成功', (port, protocol,))
        mw.writeLog("防火墙管理", msg)
        return mw.returnData(True, msg)

    def addPanelPort(self, port):
        self.setFw(0)

        protocol = 'tcp'
        ps = 'PANEL端口'

        if thisdb.getFirewallCountByPort(port) > 0:
            return mw.returnData(False, '您要放行的端口已存在，无需重复放行!')

        thisdb.addFirewall(port, ps=ps,protocol=protocol)
        self.addAcceptPortCmd(port, protocol=protocol)
        self.reload()

        msg = mw.getInfo('放行端口[{1}][{2}]成功', (port, protocol,))
        mw.writeLog("防火墙管理", msg)
        return mw.returnData(True, msg)

    # ------------------------------- 屏蔽 IP ----------------------------------------
    # 记录存于 firewall 表: port 字段为 IP/网段, protocol 为 address

    def __blockCmds(self, ip, add=True):
        import ipaddress
        net = ipaddress.ip_network(ip, strict=False)
        v6 = net.version == 6
        src = str(net) if net.num_addresses > 1 else str(net.network_address)
        if self.__isUfw:
            if add:
                # 插入到最前, 确保优先于放行规则; IPv6 无规则时 insert 会失败, 退回追加
                return [['ufw', 'insert', '1', 'deny', 'from', src, 'to', 'any']], \
                       [['ufw', 'deny', 'from', src, 'to', 'any']]
            return [['ufw', 'delete', 'deny', 'from', src, 'to', 'any']], []
        if self.__isFirewalld:
            rule = 'rule family="%s" source address="%s" drop' % ('ipv6' if v6 else 'ipv4', src)
            opt = '--add-rich-rule' if add else '--remove-rich-rule'
            return [['firewall-cmd', '--permanent', opt + '=' + rule]], []
        if self.__isIptables:
            bin_name = 'ip6tables' if v6 else 'iptables'
            return [[bin_name, '-I' if add else '-D', 'INPUT', '-s', src, '-j', 'DROP']], []
        return [], []

    def __runCmds(self, cmds, fallback):
        import subprocess
        for cmd in cmds:
            p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            if p.returncode != 0:
                for fcmd in fallback:
                    p = subprocess.run(fcmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                if p.returncode != 0:
                    return False, p.stdout.strip()[-200:]
        return True, ''

    def addBlockIp(self, ip, ps=''):
        import ipaddress
        ip = str(ip).strip()
        try:
            net = ipaddress.ip_network(ip, strict=False)
        except ValueError:
            return mw.returnData(False, 'IP 地址或网段格式不正确!')
        src = str(net) if net.num_addresses > 1 else str(net.network_address)
        if net.is_loopback:
            return mw.returnData(False, '不能屏蔽本机地址!')
        if not (self.__isUfw or self.__isFirewalld or self.__isIptables):
            return mw.returnData(False, '未检测到系统防火墙(ufw/firewalld/iptables), 无法屏蔽 IP!')
        if not self.getFwStatus():
            return mw.returnData(False, '请先启用系统防火墙!')
        if thisdb.getFirewallCountByPort(src) > 0:
            return mw.returnData(False, '该 IP 已在屏蔽列表中!')
        cmds, fallback = self.__blockCmds(src, add=True)
        good, err = self.__runCmds(cmds, fallback)
        if not good:
            return mw.returnData(False, '屏蔽失败: ' + err)
        thisdb.addFirewall(src, ps=ps or '屏蔽IP', protocol='address')
        self.reload()
        if self.__isIptables:
            mw.execShell('service iptables save')
        mw.writeLog("防火墙管理", '屏蔽IP[%s]' % src)
        return mw.returnData(True, '已屏蔽 ' + src)

    def delBlockIp(self, firewall_id, ip):
        import ipaddress
        try:
            ipaddress.ip_network(str(ip).strip(), strict=False)
        except ValueError:
            return mw.returnData(False, 'IP 格式不正确!')
        cmds, _ = self.__blockCmds(str(ip).strip(), add=False)
        self.__runCmds(cmds, [])
        mw.M('firewall').where('id=? and protocol=?', (firewall_id, 'address')).delete()
        self.reload()
        if self.__isIptables:
            mw.execShell('service iptables save')
        mw.writeLog("防火墙管理", '解除屏蔽IP[%s]' % ip)
        return mw.returnData(True, '已解除屏蔽')

    def getBlockedIps(self):
        rows = mw.M('firewall').where('protocol=?', ('address',)).field('port').select() or []
        return set(str(r['port']) for r in rows if isinstance(r, dict))

    def delAcceptPort(self, firewall_id, port,
        protocol='tcp'
    ):
        if protocol == 'address':
            return self.delBlockIp(firewall_id, port)
        panel_port = mw.getPanelPort()

        if port.find(':') > 0:
            pass
        elif port.find('-') > 0:
            pass
        else:
            if(int(port) == int(panel_port)):
                return mw.returnData(False, '失败，不能删除当前面板端口!')
        try:
            self.delAcceptPortCmd(port, protocol)
            mw.M('firewall').where("id=?", (firewall_id,)).delete()
            return mw.returnData(True, '删除成功!')
        except Exception as e:
            return mw.returnData(False, '删除失败!:' + str(e))

    def delAcceptPortCmd(self, port,
        protocol ='tcp'
    ):
        # 端口只允许 "端口" 或 "起始:结束" 格式, 防止命令注入
        port = str(port).strip()
        if not re.match(r'^\d{1,5}([:-]\d{1,5})?$', port) or protocol not in ('tcp', 'udp', 'tcp/udp'):
            return False
        if self.__isUfw:
            if protocol == 'tcp':
                mw.execShell('ufw delete allow ' + port + '/tcp')
            if protocol == 'udp':
                mw.execShell('ufw delete allow ' + port + '/udp')
            if protocol == 'tcp/udp':
                mw.execShell('ufw delete allow ' + port + '/tcp')
                mw.execShell('ufw delete allow ' + port + '/udp')
        elif self.__isFirewalld:
            port = port.replace(':', '-')
            if protocol == 'tcp':
                mw.execShell(
                    'firewall-cmd --permanent --zone=public --remove-port=' + port + '/tcp')
            if protocol == 'udp':
                mw.execShell(
                    'firewall-cmd --permanent --zone=public --remove-port=' + port + '/udp')
            if protocol == 'tcp/udp':
                mw.execShell(
                    'firewall-cmd --permanent --zone=public --remove-port=' + port + '/tcp')
                mw.execShell(
                    'firewall-cmd --permanent --zone=public --remove-port=' + port + '/udp')
        elif self.__isIptables:
            if protocol == 'tcp':
                mw.execShell(
                    'iptables -D INPUT -p tcp -m state --state NEW -m tcp --dport ' + port + ' -j ACCEPT')
            if protocol == 'udp':
                mw.execShell(
                    'iptables -D INPUT -p udp -m state --state NEW -m udp --dport ' + port + ' -j ACCEPT')
            if protocol == 'tcp/udp':
                mw.execShell(
                    'iptables -D INPUT -p tcp -m state --state NEW -m tcp --dport ' + port + ' -j ACCEPT')
                mw.execShell(
                    'iptables -D INPUT -p udp -m state --state NEW -m udp --dport ' + port + ' -j ACCEPT')
        else:
            pass

        mw.M('firewall').where("port=?", (port,)).delete()
        msg = mw.getInfo('删除防火墙放行端口[{1}][{2}]成功!', (port, protocol,))
        mw.writeLog("防火墙管理", msg)
        self.reload()
        return True
