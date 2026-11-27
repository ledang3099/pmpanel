// PM-Linux面板 安全: 系统防火墙 / SSH管理 / SSH登录日志 / 系统账号

var SEC = { fwPage: 1, logPage: 1, logStatus: 'all', logSearch: '', info: null };

$(function () {
    pmTabs('#secPanel', function (name) {
        $('.sec-pane').hide();
        $('#pane-' + name).show();
        if (name == 'firewall') fwLoad();
        if (name == 'ssh') sshLoad();
        if (name == 'sshlog') sshLogLoad(1);
        if (name == 'users') userLoad();
    });
    $(document).on('click', '[data-goto]', function () {
        $('#secPanel .pm-tab[data-tab="' + $(this).attr('data-goto') + '"]').trigger('click');
    });
    fwBind();
    sshLogBind();
    $('#userAdd').on('click', userAddDialog);
    $('#userShowSystem').on('change', userLoad);
});

// ================================ 系统防火墙 ================================

function fwBind() {
    $('#fwType').on('change', function () {
        var ip = $(this).val() == 'address';
        $('#fwPort').attr('placeholder', ip ? 'IP 或网段, 如 1.2.3.4 或 1.2.3.0/24' : '端口, 如 8080 或 3000:3500');
        $('#fwProtocol').toggle(!ip);
        $('#fwTip').text(ip ? '屏蔽后该 IP 无法访问服务器的任何端口' : '支持端口范围, 如 3000:3500');
    });
    $('#fwAdd').on('click', function () {
        var type = $('#fwType').val(), port = $.trim($('#fwPort').val()), ps = $.trim($('#fwPs').val());
        if (!port) { layer.msg(type == 'address' ? '请输入 IP' : '请输入端口', { icon: 2 }); return; }
        if (type == 'port' && !/^\d{1,5}([:-]\d{1,5})?$/.test(port)) { layer.msg('端口格式不正确', { icon: 2 }); return; }
        pmPost('/firewall/add_accept_port', { port: port, ps: ps || (type == 'address' ? '屏蔽IP' : '放行端口'), type: type, protocol: $('#fwProtocol').val() }, function (r) {
            pmResult(r, function () { $('#fwPort').val(''); $('#fwPs').val(''); fwLoad(); });
        });
    });
}

function fwLoad() {
    pmPost('/firewall/get_ssh_info', {}, function (info) {
        SEC.info = info;
        var html = '<div class="pm-stat ' + (info.firewall_status ? 'ok' : 'warn') + '"><div class="pm-stat-label">系统防火墙</div>' +
            '<div class="pm-stat-value" style="font-size:18px">' + (info.firewall_status ? '已启用' : '未启用') + ' ' + pmSwitch('fwSwitch', info.firewall_status) + '</div>' +
            '<div class="pm-stat-sub">ufw / firewalld / iptables</div></div>' +
            '<div class="pm-stat"><div class="pm-stat-label">允许 Ping</div><div class="pm-stat-value" style="font-size:18px">' +
            (info.ping ? '允许' : '已禁止') + ' ' + pmSwitch('fwPing', info.ping) + '</div><div class="pm-stat-sub">禁止后无法 ping 通服务器</div></div>' +
            '<div class="pm-stat"><div class="pm-stat-label">SSH 端口</div><div class="pm-stat-value">' + pmEsc(info.port) + '</div>' +
            '<div class="pm-stat-sub"><a class="btlink" data-goto="ssh">SSH 管理</a></div></div>';
        $('#fwStats').html(html);
        $('#fwSwitch').on('change', function () {
            var on = this.checked, el = this;
            layer.confirm(on ? '确定启用系统防火墙吗? 启用前请确认 SSH 与面板端口已放行。' : '关闭防火墙会降低服务器安全性, 确定关闭吗?', { icon: 3, title: '系统防火墙' }, function (idx) {
                layer.close(idx);
                pmPost('/firewall/set_fw', { status: on ? '0' : '1' }, function (r) { pmResult(r); fwLoad(); });
            }, function () { el.checked = !on; });
        });
        $('#fwPing').on('change', function () { setPing(this.checked, fwLoad); });
    }, { silent: true });
    fwList(SEC.fwPage);
}

function fwList(page) {
    SEC.fwPage = page;
    pmPost('/firewall/get_list', { p: page, limit: 10 }, function (r) {
        var rows = '';
        for (var i = 0; i < r.data.length; i++) {
            var d = r.data[i], ip = d.protocol == 'address';
            rows += '<tr><td>' + (ip ? '<span class="pm-tag red">屏蔽IP</span>' : '<span class="pm-tag green">放行端口</span>') + '</td>' +
                '<td class="pm-code">' + pmEsc(d.port) + '</td><td>' + (ip ? '-' : pmEsc(d.protocol)) + '</td><td>' + pmEsc(d.ps) + '</td>' +
                '<td>' + pmEsc(d.add_time) + '</td><td class="text-right"><a class="btlink" data-id="' + pmEsc(d.id) + '" data-port="' + pmEsc(d.port) +
                '" data-protocol="' + pmEsc(d.protocol) + '">删除</a></td></tr>';
        }
        if (!rows) rows = '<tr><td colspan="6" class="pm-empty">暂无规则</td></tr>';
        $('#fwBody').html(rows);
        $('#fwBody a[data-id]').on('click', function () {
            var a = $(this);
            layer.confirm('确定删除规则 [' + pmEsc(a.attr('data-port')) + '] 吗?', { icon: 3, title: '删除规则' }, function (idx) {
                layer.close(idx);
                pmPost('/firewall/del_accept_port', { id: a.attr('data-id'), port: a.attr('data-port'), protocol: a.attr('data-protocol') }, function (r) {
                    pmResult(r, function () { fwList(SEC.fwPage); });
                });
            });
        });
        pmPager('fwPager', r.count || 0, page, 10, fwList);
    }, { silent: true });
}

function setPing(allow, done) {
    pmPost('/firewall/set_ping', { status: allow ? '0' : '1' }, function (r) { pmResult(r); done && done(); });
}

// ================================ SSH 管理 ================================

function sshLoad() {
    pmPost('/firewall/get_ssh_info', {}, function (info) {
        SEC.info = info;
        sshRenderSetting(info);
        pmPost('/firewall/ssh_stats', {}, function (r) { sshRenderStats(info, r.data || {}); }, { silent: true });
    }, { silent: true });
}

function sshRenderStats(info, st) {
    var last = st.last_success ? pmEsc(st.last_success.user) + ' 来自 ' + pmEsc(st.last_success.ip) + '<br>' + pmEsc(st.last_success.time) : '暂无记录';
    var html =
        '<div class="pm-stat ' + (info.status ? 'ok' : 'bad') + '"><div class="pm-stat-label">SSH 服务</div>' +
        '<div class="pm-stat-value" style="font-size:18px">' + (info.status ? '运行中' : '已停止') + '</div>' +
        '<div class="pm-stat-sub"><a class="btlink" data-ssh-act="' + (info.status ? 'stop' : 'start') + '">' + (info.status ? '停止' : '启动') + '</a>' +
        (info.status ? ' &nbsp; <a class="btlink" data-ssh-act="restart">重启</a>' : '') + '</div></div>' +
        '<div class="pm-stat ok"><div class="pm-stat-label">今日登录成功</div><div class="pm-stat-value">' + (st.success_today || 0) + '<small>次</small></div>' +
        '<div class="pm-stat-sub">累计 ' + (st.success_total || 0) + ' 次</div></div>' +
        '<div class="pm-stat bad"><div class="pm-stat-label">今日登录失败</div><div class="pm-stat-value">' + (st.fail_today || 0) + '<small>次</small></div>' +
        '<div class="pm-stat-sub">累计 ' + (st.fail_total || 0) + ' 次, 来自 ' + (st.fail_ip_count || 0) + ' 个 IP</div></div>' +
        '<div class="pm-stat"><div class="pm-stat-label">最近成功登录</div><div class="pm-stat-sub" style="font-size:13px;color:#374151;margin-top:8px;line-height:20px">' + last + '</div></div>';
    $('#sshStats').html(html);
    $('#sshStats [data-ssh-act]').on('click', function () {
        var act = $(this).attr('data-ssh-act');
        var tip = { stop: '停止 SSH 后将无法通过 SSH 远程登录服务器(面板仍可访问), 确定停止吗?', start: '确定启动 SSH 服务吗?', restart: '确定重启 SSH 服务吗? 已建立的连接不受影响。' }[act];
        layer.confirm(tip, { icon: 3, title: 'SSH 服务' }, function (idx) {
            layer.close(idx);
            pmPost('/firewall/ssh_service', { action: act }, function (r) { pmResult(r); sshLoad(); });
        });
    });

    var ips = st.top_fail_ips || [], rows = '';
    for (var i = 0; i < ips.length; i++) {
        var t = ips[i];
        rows += '<tr><td class="pm-code">' + pmEsc(t.ip) + '</td><td><span class="pm-tag red">' + t.count + '</span></td>' +
            '<td>' + pmEsc(t.users.join(', ')) + '</td><td>' + pmEsc(t.last) + '</td><td class="text-right">' +
            (t.blocked ? '<span class="pm-tag gray">已屏蔽</span>' : '<a class="btlink" data-block="' + pmEsc(t.ip) + '">屏蔽</a>') + '</td></tr>';
    }
    if (!rows) rows = '<tr><td colspan="5" class="pm-empty">暂无登录失败记录</td></tr>';
    $('#sshTopIps').html(rows);
    $('#sshTopIps a[data-block]').on('click', function () { sshBlockIp($(this).attr('data-block'), sshLoad); });
}

function sshRenderSetting(info) {
    $('#sshConfFile').text('写入: ' + info.config_file);
    if (!info.installed) {
        $('#sshSetting').html('<tr><td colspan="2"><div class="pm-alert warn">未检测到 OpenSSH 服务端(openssh-server)</div></td></tr>');
        return;
    }
    var root = info.permit_root_login;
    var html =
        '<tr><td>SSH 端口</td><td><input class="bt-input-text" id="sshPort" style="width:100px" value="' + pmEsc(info.port) + '"> ' +
        '<button class="btn btn-default btn-sm" id="sshPortSave">保存</button><span class="pm-help">修改前会自动在防火墙放行新端口</span></td></tr>' +
        '<tr><td>root 登录</td><td><select class="bt-input-text" id="sshRoot" style="width:170px">' +
        '<option value="yes"' + (root == 'yes' ? ' selected' : '') + '>允许(密码和密钥)</option>' +
        '<option value="prohibit-password"' + (root == 'prohibit-password' ? ' selected' : '') + '>仅允许密钥登录</option>' +
        '<option value="no"' + (root == 'no' ? ' selected' : '') + '>禁止 root 登录</option></select>' +
        ' <a class="btlink" id="sshRootKey" style="margin-left:8px">管理 root 密钥</a></td></tr>' +
        '<tr><td>密码登录</td><td>' + pmSwitch('sshPass', info.password_auth == 'yes') + '<span class="pm-help">建议改用密钥登录后关闭</span></td></tr>' +
        '<tr><td>密钥登录</td><td>' + pmSwitch('sshPubkey', info.pubkey_auth == 'yes') + '</td></tr>' +
        '<tr><td>最大尝试次数</td><td><input class="bt-input-text" id="sshTries" style="width:100px" value="' + pmEsc(info.max_auth_tries) + '"> ' +
        '<button class="btn btn-default btn-sm" id="sshTriesSave">保存</button><span class="pm-help">每个连接允许的认证次数(1-20)</span></td></tr>' +
        '<tr><td>允许 Ping</td><td>' + pmSwitch('sshPing', info.ping) + '</td></tr>' +
        '<tr><td>版本</td><td class="pm-muted">' + pmEsc(info.version) + (info.socket ? ' (ssh.socket 监听)' : '') + '</td></tr>';
    $('#sshSetting').html(html);

    $('#sshPortSave').on('click', function () {
        var port = $.trim($('#sshPort').val());
        layer.confirm('确定将 SSH 端口修改为 ' + pmEsc(port) + ' 吗?<br>修改后请使用新端口连接; 若服务器在云平台, 还需在安全组中放行该端口。', { icon: 3, title: '修改 SSH 端口' }, function (idx) {
            layer.close(idx);
            pmPost('/firewall/set_ssh_port', { port: port }, function (r) { pmResult(r); sshLoad(); });
        });
    });
    $('#sshRoot').on('change', function () { sshSet('PermitRootLogin', $(this).val()); });
    $('#sshPass').on('change', function () { sshSet('PasswordAuthentication', this.checked ? 'yes' : 'no'); });
    $('#sshPubkey').on('change', function () { sshSet('PubkeyAuthentication', this.checked ? 'yes' : 'no'); });
    $('#sshTriesSave').on('click', function () { sshSet('MaxAuthTries', $.trim($('#sshTries').val())); });
    $('#sshPing').on('change', function () { setPing(this.checked, sshLoad); });
    $('#sshRootKey').on('click', function () { userKeysDialog('root'); });
}

function sshSet(key, value, force) {
    pmPost('/firewall/ssh_set', { key: key, value: value, force: force ? '1' : '' }, function (r) {
        if (!r.status && r.data && r.data.need_force) {
            layer.confirm(pmEsc(r.msg) + '<br><br>仍要继续吗?', { icon: 0, title: '风险提示', btn: ['仍然继续', '取消'] }, function (idx) {
                layer.close(idx);
                sshSet(key, value, true);
            }, function () { sshLoad(); });
            return;
        }
        pmResult(r);
        sshLoad();
    });
}

function sshBlockIp(ip, done) {
    layer.confirm('确定在系统防火墙中屏蔽 ' + pmEsc(ip) + ' 吗? 屏蔽后该 IP 无法访问服务器的任何端口。', { icon: 3, title: '屏蔽 IP' }, function (idx) {
        layer.close(idx);
        pmPost('/firewall/ssh_block_ip', { ip: ip }, function (r) { pmResult(r); done && done(); });
    });
}

// ================================ SSH 登录日志 ================================

function sshLogBind() {
    $('#sshLogFilter span').on('click', function () {
        $('#sshLogFilter span').removeClass('on');
        $(this).addClass('on');
        SEC.logStatus = $(this).attr('data-v');
        sshLogLoad(1);
    });
    $('#sshLogSearchBtn').on('click', function () { SEC.logSearch = $.trim($('#sshLogSearch').val()); sshLogLoad(1); });
    $('#sshLogSearch').on('keydown', function (e) { if (e.keyCode == 13) $('#sshLogSearchBtn').trigger('click'); });
    $('#sshLogRefresh').on('click', function () { sshLogLoad(SEC.logPage); });
}

function sshLogLoad(page) {
    SEC.logPage = page;
    pmPost('/firewall/ssh_logs', { p: page, limit: 20, status: SEC.logStatus, search: SEC.logSearch }, function (r) {
        var d = r.data || {}, list = d.list || [], rows = '';
        for (var i = 0; i < list.length; i++) {
            var e = list[i];
            rows += '<tr><td>' + pmEsc(e.time) + '</td><td>' + pmEsc(e.user) + (e.invalid ? ' <span class="pm-tag gray">不存在</span>' : '') + '</td>' +
                '<td class="pm-code">' + pmEsc(e.ip) + '</td><td>' + pmEsc(e.port) + '</td><td>' + pmEsc(e.method_name) + '</td>' +
                '<td>' + (e.status ? '<span class="pm-tag green">成功</span>' : '<span class="pm-tag red">失败</span>') + '</td>' +
                '<td class="text-right">' + (e.status ? '' : '<a class="btlink" data-block="' + pmEsc(e.ip) + '">屏蔽 IP</a>') + '</td></tr>';
        }
        if (!rows) rows = '<tr><td colspan="7" class="pm-empty">暂无登录记录</td></tr>';
        $('#sshLogBody').html(rows);
        $('#sshLogBody a[data-block]').on('click', function () { sshBlockIp($(this).attr('data-block')); });
        pmPager('sshLogPager', d.total || 0, page, 20, sshLogLoad);
        $('#sshLogSource').text('日志来源: ' + (d.source || ''));
    }, { silent: true });
}

// ================================ 系统账号 ================================

function userLoad() {
    pmPost('/firewall/user_list', { system: $('#userShowSystem').prop('checked') ? '1' : '' }, function (r) {
        var d = r.data || {}, list = d.list || [], rows = '';
        SEC.shells = d.shells || [];
        SEC.adminGroup = d.admin_group;
        for (var i = 0; i < list.length; i++) {
            var u = list[i], name = pmEsc(u.name);
            var status = u.locked ? '<span class="pm-tag red">已锁定</span>' : (!u.login_shell ? '<span class="pm-tag gray">禁止登录</span>' :
                (u.has_password ? '<span class="pm-tag green">正常</span>' : '<span class="pm-tag orange">未设密码</span>'));
            var ops = '<a class="btlink" data-op="passwd" data-u="' + name + '">改密码</a><a class="btlink" data-op="keys" data-u="' + name + '">公钥</a>';
            if (u.manageable) {
                ops += '<a class="btlink" data-op="edit" data-u="' + name + '">设置</a>' +
                    '<a class="btlink" data-op="lock" data-u="' + name + '" data-v="' + (u.locked ? '0' : '1') + '">' + (u.locked ? '解锁' : '锁定') + '</a>' +
                    '<a class="btlink" style="color:#ef4444" data-op="del" data-u="' + name + '">删除</a>';
            }
            if (!u.manageable && u.uid != 0) ops = '<span class="pm-muted">系统账号</span>';
            var last = u.last_login ? pmEsc(u.last_login.time) + '<br><span class="pm-muted">' + pmEsc(u.last_login.ip) + '</span>' : '<span class="pm-muted">-</span>';
            rows += '<tr><td><b>' + name + '</b>' + (u.comment ? '<br><span class="pm-muted">' + pmEsc(u.comment) + '</span>' : '') + '</td>' +
                '<td>' + u.uid + '</td><td class="pm-code">' + pmEsc(u.home) + '</td><td class="pm-code">' + pmEsc(u.shell) + '</td>' +
                '<td>' + (u.sudo ? '<span class="pm-tag blue">是</span>' : '<span class="pm-muted">否</span>') + '</td>' +
                '<td>' + (u.keys ? u.keys + ' 个' : '<span class="pm-muted">无</span>') + '</td><td>' + last + '</td><td>' + status + '</td>' +
                '<td class="text-right ops">' + ops + '</td></tr>';
        }
        if (!rows) rows = '<tr><td colspan="9" class="pm-empty">暂无账号</td></tr>';
        $('#userBody').html(rows);
        $('#userBody a[data-op]').on('click', function () {
            var op = $(this).attr('data-op'), name = $(this).attr('data-u');
            var user = list.filter(function (x) { return x.name == name; })[0];
            if (op == 'passwd') userPasswdDialog(name);
            if (op == 'keys') userKeysDialog(name);
            if (op == 'edit') userEditDialog(user);
            if (op == 'lock') userLock(name, $(this).attr('data-v') == '1');
            if (op == 'del') userDel(name);
        });
    }, { silent: true });
}

function shellOptions(selected) {
    var html = '';
    for (var i = 0; i < (SEC.shells || []).length; i++) {
        var s = SEC.shells[i];
        var label = /nologin|false$/.test(s) ? s + ' (禁止登录)' : s;
        html += '<option value="' + pmEsc(s) + '"' + (s == selected ? ' selected' : '') + '>' + pmEsc(label) + '</option>';
    }
    return html;
}

function randomPassword() {
    var chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789', sym = '!@#%^*_-+=', out = '';
    var buf = new Uint32Array(16);
    window.crypto.getRandomValues(buf);
    for (var i = 0; i < 14; i++) out += chars[buf[i] % chars.length];
    return out + sym[buf[14] % sym.length] + (buf[15] % 10);
}

function userAddDialog() {
    var html = '<div class="pm-form pd20">' +
        '<div class="line"><span class="tname">用户名</span><input class="bt-input-text" id="uaName" placeholder="小写字母开头, 如 deploy"></div>' +
        '<div class="line"><span class="tname">密码</span><input class="bt-input-text" id="uaPass" style="width:200px"> <a class="btlink" id="uaGen">随机生成</a>' +
        '<span class="pm-help">至少 8 位, 包含大小写字母、数字、符号中的三种</span></div>' +
        '<div class="line"><span class="tname">登录 Shell</span><select class="bt-input-text" id="uaShell">' + shellOptions('/bin/bash') + '</select></div>' +
        '<div class="line"><span class="tname">sudo 权限</span><label style="font-weight:400"><input type="checkbox" id="uaSudo"' + (SEC.adminGroup ? '' : ' disabled') +
        '> 加入 ' + pmEsc(SEC.adminGroup || 'sudo') + ' 组' + (SEC.adminGroup ? '' : ' (系统未安装 sudo)') + '</label></div>' +
        '<div class="line"><span class="tname">备注</span><input class="bt-input-text" id="uaComment" placeholder="可选"></div></div>';
    layer.open({
        type: 1, title: '添加系统账号', area: '470px', closeBtn: 1, shadeClose: false, content: html, btn: ['创建', '取消'],
        success: function () {
            $('#uaGen').on('click', function () { $('#uaPass').val(randomPassword()); });
        },
        yes: function (idx) {
            pmPost('/firewall/user_add', {
                name: $.trim($('#uaName').val()), password: $('#uaPass').val(), shell: $('#uaShell').val(),
                sudo: $('#uaSudo').prop('checked') ? '1' : '', comment: $.trim($('#uaComment').val())
            }, function (r) { pmResult(r, function () { layer.close(idx); userLoad(); }); });
        }
    });
}

function userPasswdDialog(name) {
    var html = '<div class="pm-form pd20"><div class="line"><span class="tname">账号</span><b>' + pmEsc(name) + '</b></div>' +
        '<div class="line"><span class="tname">新密码</span><input class="bt-input-text" id="upPass" style="width:200px"> <a class="btlink" id="upGen">随机生成</a>' +
        '<span class="pm-help">至少 8 位, 包含大小写字母、数字、符号中的三种</span></div></div>';
    layer.open({
        type: 1, title: '修改密码', area: '470px', closeBtn: 1, content: html, btn: ['保存', '取消'],
        success: function () { $('#upGen').on('click', function () { $('#upPass').val(randomPassword()); }); },
        yes: function (idx) {
            pmPost('/firewall/user_passwd', { name: name, password: $('#upPass').val() }, function (r) {
                pmResult(r, function () { layer.close(idx); userLoad(); });
            });
        }
    });
}

function userEditDialog(u) {
    var html = '<div class="pm-form pd20"><div class="line"><span class="tname">账号</span><b>' + pmEsc(u.name) + '</b></div>' +
        '<div class="line"><span class="tname">登录 Shell</span><select class="bt-input-text" id="ueShell">' + shellOptions(u.shell) + '</select>' +
        ' <button class="btn btn-default btn-sm" id="ueShellSave">保存</button><span class="pm-help">选择 nologin 可禁止该账号 SSH 登录</span></div>' +
        '<div class="line"><span class="tname">sudo 权限</span>' + pmSwitch('ueSudo', u.sudo, !SEC.adminGroup) + '</div></div>';
    layer.open({
        type: 1, title: '账号设置', area: '470px', closeBtn: 1, content: html,
        success: function () {
            $('#ueShellSave').on('click', function () {
                pmPost('/firewall/user_shell', { name: u.name, shell: $('#ueShell').val() }, function (r) { pmResult(r, userLoad); });
            });
            $('#ueSudo').on('change', function () {
                pmPost('/firewall/user_sudo', { name: u.name, sudo: this.checked ? '1' : '' }, function (r) { pmResult(r); userLoad(); });
            });
        }
    });
}

function userLock(name, lock) {
    var tip = lock ? '锁定后账号 ' + pmEsc(name) + ' 将无法通过密码或密钥登录, 确定锁定吗?' : '确定解锁账号 ' + pmEsc(name) + ' 吗?';
    layer.confirm(tip, { icon: 3, title: lock ? '锁定账号' : '解锁账号' }, function (idx) {
        layer.close(idx);
        pmPost('/firewall/user_lock', { name: name, lock: lock ? '1' : '' }, function (r) { pmResult(r, userLoad); });
    });
}

function userDel(name) {
    var html = '确定删除系统账号 <b>' + pmEsc(name) + '</b> 吗? 此操作不可恢复。<br><br>' +
        '<label style="font-weight:400"><input type="checkbox" id="udHome"> 同时删除主目录及其中的文件</label>';
    layer.confirm(html, { icon: 0, title: '删除账号', btn: ['删除', '取消'] }, function (idx) {
        var rm = $('#udHome').prop('checked');
        layer.close(idx);
        pmPost('/firewall/user_del', { name: name, remove_home: rm ? '1' : '' }, function (r) { pmResult(r, userLoad); });
    });
}

// SSH 公钥管理(系统账号与 root 密钥共用)
function userKeysDialog(name) {
    var html = '<div class="pd15"><div class="pm-toolbar"><b>' + pmEsc(name) + '</b><span class="pm-muted">~/.ssh/authorized_keys</span>' +
        '<div class="pm-right"><button class="btn btn-success btn-sm" id="ukGen">生成密钥对</button><button class="btn btn-default btn-sm" id="ukAdd">添加公钥</button></div></div>' +
        '<div class="divtable" style="max-height:300px;overflow:auto"><table class="table table-hover pm-table"><thead><tr><th>类型</th><th>指纹</th><th>备注</th><th class="text-right">操作</th></tr></thead>' +
        '<tbody id="ukBody"></tbody></table></div></div>';
    var box = layer.open({
        type: 1, title: 'SSH 公钥管理', area: ['720px', '460px'], closeBtn: 1, content: html,
        success: function () {
            ukList(name);
            $('#ukAdd').on('click', function () { ukAddDialog(name); });
            $('#ukGen').on('click', function () { ukGenDialog(name); });
        },
        end: function () { if ($('#pane-users').is(':visible')) userLoad(); }
    });
}

function ukList(name) {
    pmPost('/firewall/user_keys', { name: name }, function (r) {
        var list = r.data || [], rows = '';
        if (!r.status) { $('#ukBody').html('<tr><td colspan="4" class="pm-empty">' + pmEsc(r.msg) + '</td></tr>'); return; }
        for (var i = 0; i < list.length; i++) {
            var k = list[i];
            rows += '<tr><td>' + pmEsc(k.type) + ' ' + pmEsc(k.bits) + '</td><td class="pm-code">' + pmEsc(k.fingerprint) + '</td>' +
                '<td>' + pmEsc(k.comment) + '</td><td class="text-right"><a class="btlink" style="color:#ef4444" data-fp="' + pmEsc(k.fingerprint) + '">删除</a></td></tr>';
        }
        if (!rows) rows = '<tr><td colspan="4" class="pm-empty">该账号还没有 SSH 公钥</td></tr>';
        $('#ukBody').html(rows);
        $('#ukBody a[data-fp]').on('click', function () {
            var fp = $(this).attr('data-fp');
            layer.confirm('删除后使用该密钥将无法登录, 确定删除吗?<br><span class="pm-code">' + pmEsc(fp) + '</span>', { icon: 3, title: '删除公钥' }, function (idx) {
                layer.close(idx);
                pmPost('/firewall/user_key_del', { name: name, fingerprint: fp }, function (r) { pmResult(r, function () { ukList(name); }); });
            });
        });
    }, { silent: true });
}

function ukAddDialog(name) {
    layer.open({
        type: 1, title: '添加公钥', area: '560px', closeBtn: 1, btn: ['添加', '取消'],
        content: '<div class="pd15"><textarea id="ukKey" class="bt-input-text pm-code" style="width:100%;height:120px" placeholder="ssh-ed25519 AAAA... user@host"></textarea>' +
            '<div class="pm-muted" style="margin-top:6px">粘贴 id_ed25519.pub / id_rsa.pub 的内容(一行)</div></div>',
        yes: function (idx) {
            pmPost('/firewall/user_key_add', { name: name, key: $.trim($('#ukKey').val()) }, function (r) {
                pmResult(r, function () { layer.close(idx); ukList(name); });
            });
        }
    });
}

function ukGenDialog(name) {
    layer.open({
        type: 1, title: '生成密钥对', area: '470px', closeBtn: 1, btn: ['生成', '取消'],
        content: '<div class="pm-form pd20"><div class="line"><span class="tname">密钥类型</span><select class="bt-input-text" id="ugType" style="width:200px">' +
            '<option value="ed25519">ED25519 (推荐)</option><option value="rsa">RSA 4096</option></select></div>' +
            '<div class="line"><span class="tname">私钥密码</span><input class="bt-input-text" id="ugPass" type="password" style="width:200px" placeholder="可选"></div>' +
            '<div class="pm-alert info">公钥会自动加入该账号的 authorized_keys; 私钥只显示这一次, 服务器不保存, 请立即下载。</div></div>',
        yes: function (idx) {
            pmPost('/firewall/user_key_gen', { name: name, type: $('#ugType').val(), passphrase: $('#ugPass').val() }, function (r) {
                if (!r.status) { pmResult(r); return; }
                layer.close(idx);
                ukList(name);
                ukShowPrivate(r.data);
            });
        }
    });
}

function ukShowPrivate(d) {
    layer.open({
        type: 1, title: '私钥(仅显示一次)', area: '620px', closeBtn: 1, btn: ['下载私钥', '关闭'],
        content: '<div class="pd15"><div class="pm-alert warn">请妥善保管私钥, 关闭此窗口后无法再次查看。</div>' +
            '<textarea class="bt-input-text pm-code" readonly style="width:100%;height:220px">' + pmEsc(d.private_key) + '</textarea></div>',
        yes: function () { pmDownloadText(d.filename, d.private_key); return false; }
    });
}
