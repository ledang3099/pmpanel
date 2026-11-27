// ---------------------------------------------------------------------------------
// PM-Linux面板 ModSecurity 防火墙
// Licensed under the Apache License 2.0. See LICENSE and NOTICE.
// ---------------------------------------------------------------------------------

function msEsc(s) {
    if (typeof htmlAttrEscape === 'function') return htmlAttrEscape(s);
    return String(s == null ? '' : s).replace(/[&<>"'`]/g, function (c) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;', '`': '&#96;' }[c];
    });
}

function msCall(func, args, callback, loading) {
    var loadT = loading === false ? null : layer.msg(loading || '正在处理...', { icon: 16, time: 0, shade: 0.3 });
    $.post('/plugins/callback', { name: 'modsecurity', func: func, args: JSON.stringify(args || {}), script: 'index' }, function (res) {
        if (loadT !== null) layer.close(loadT);
        if (!res.status) { layer.msg(msEsc(res.msg || '调用失败'), { icon: 2, time: 5000 }); return; }
        if (typeof callback === 'function') callback(res.data || {});
    }, 'json').fail(function () {
        if (loadT !== null) layer.close(loadT);
        layer.msg('请求失败', { icon: 2 });
    });
}

function msResult(r, after) {
    layer.msg(msEsc(r.msg), { icon: r.status ? 1 : 2, time: r.status ? 2000 : 8000 });
    if (r.status && typeof after === 'function') after();
}

function msMenu(i) { $('.bt-w-menu p').removeClass('bgw').eq(i).addClass('bgw'); }

// 服务开关: 复用插件通用接口
function msToggle(on) {
    var loadT = layer.msg('正在' + (on ? '开启' : '关闭') + '...', { icon: 16, time: 0, shade: 0.3 });
    $.post('/plugins/run', { name: 'modsecurity', func: on ? 'start' : 'stop' }, function (res) {
        layer.close(loadT);
        var okv = res.status && $.trim(res.data) === 'ok';
        layer.msg(okv ? (on ? '防火墙已开启' : '防火墙已关闭') : msEsc(res.data || res.msg), { icon: okv ? 1 : 2, time: okv ? 2000 : 8000 });
        msOverview();
    }, 'json');
}

// ------------------------------- 概览 -------------------------------------------

function msOverview() {
    msMenu(0);
    msCall('get_info', {}, function (r) {
        var d = r.data || {};
        var s = d.settings || {};
        var html = '';
        if (!d.compat) {
            html += '<div class="ms-alert warn">当前 OpenResty 未启用 --with-compat, 防火墙模块无法加载。请先在应用市场中升级/重装 OpenResty。</div>';
        } else if (!d.module) {
            html += '<div class="ms-alert warn">未找到防火墙模块, 请重新安装本插件。</div>';
        } else if (d.module_mismatch) {
            html += '<div class="ms-alert warn">防火墙模块是为 OpenResty ' + msEsc(d.module_for) + ' 编译的, 当前为 ' + msEsc(d.openresty) + ', 请重新安装本插件。</div>';
        }
        var running = d.status === 'start';
        if (running && s.engine === 'DetectionOnly') {
            html += '<div class="ms-alert info">当前为<b>仅记录</b>模式: 检测到攻击只记录日志, 不会拦截。建议观察拦截日志一段时间, 确认没有误报后切换为<b>拦截</b>模式。</div>';
        } else if (running && s.engine === 'On') {
            html += '<div class="ms-alert ok">防火墙运行中, 检测到的攻击将被拦截(返回 403)。</div>';
        } else if (!running) {
            html += '<div class="ms-alert warn">防火墙未开启。</div>';
        }
        html += '<table class="ms-kv">' +
            '<tr><td>防火墙状态</td><td>' + (running ? '<span class="ms-tag green">运行中</span>' : '<span class="ms-tag red">已关闭</span>') +
                ' <button class="btn btn-' + (running ? 'default' : 'success') + ' btn-xs" onclick="msToggle(' + (running ? 'false' : 'true') + ')">' + (running ? '关闭防火墙' : '开启防火墙') + '</button></td></tr>' +
            '<tr><td>工作模式</td><td><div class="ms-seg" id="msEngine">' +
                '<button data-v="DetectionOnly" class="' + (s.engine === 'DetectionOnly' ? 'on' : '') + '">仅记录</button>' +
                '<button data-v="On" class="' + (s.engine === 'On' ? 'on' : '') + '">拦截</button></div></td></tr>' +
            '<tr><td>防护等级</td><td>' + msEsc(s.paranoia) + ' 级 <span class="ms-help" style="display:inline">(防护设置中调整)</span></td></tr>' +
            '<tr><td>规则集</td><td>OWASP CRS ' + msEsc(d.crs || '-') + '</td></tr>' +
            '<tr><td>引擎</td><td>libmodsecurity ' + msEsc(d.libmodsecurity || '-') + ' / ModSecurity-nginx ' + msEsc(d.connector || '-') + '</td></tr>' +
            '<tr><td>OpenResty</td><td>' + msEsc(d.openresty || '-') + (d.compat ? '' : ' <span class="ms-tag orange">缺少 --with-compat</span>') + '</td></tr>' +
            '</table>';
        $('.soft-man-con').html('<div class="ms-box">' + html + '</div>');
        $('#msEngine button').on('click', function () {
            var v = $(this).attr('data-v');
            var go = function () { msCall('set_config', { engine: v }, function (r) { msResult(r, msOverview); }); };
            if (v === 'On') {
                layer.confirm('切换为拦截模式后, 被判定为攻击的请求将返回 403。建议先在"仅记录"模式下观察日志确认没有误报。确定切换吗?', { icon: 3, title: '切换为拦截' }, go);
            } else { go(); }
        });
    });
}

// ------------------------------- 防护设置 ---------------------------------------

function msSettings() {
    msMenu(1);
    msCall('get_info', {}, function (r) {
        var s = (r.data || {}).settings || {};
        var form = $('<div class="ms-box">' +
            '<table class="ms-kv">' +
            '<tr><td>防护等级</td><td><select class="bt-input-text" name="paranoia" style="width:240px">' +
                '<option value="1">1 级 - 推荐, 误报极少</option><option value="2">2 级 - 更严格, 少量误报</option>' +
                '<option value="3">3 级 - 严格, 需要调整规则</option><option value="4">4 级 - 极严格, 误报较多</option></select>' +
                '<div class="ms-help">对应 CRS 的 Paranoia Level。等级越高能发现越多攻击, 同时误报越多。</div></td></tr>' +
            '<tr><td>请求拦截阈值</td><td><input class="bt-input-text" name="inbound_threshold" style="width:100px">' +
                '<div class="ms-help">异常评分达到该值即拦截, 默认 5(一条严重规则命中即拦截)。数值越大越宽松。</div></td></tr>' +
            '<tr><td>响应拦截阈值</td><td><input class="bt-input-text" name="outbound_threshold" style="width:100px">' +
                '<div class="ms-help">检测响应中的信息泄露(如报错信息), 默认 4。</div></td></tr>' +
            '<tr><td>请求体大小上限</td><td><input class="bt-input-text" name="body_limit_kb" style="width:120px"> KB' +
                '<div class="ms-help">超过此大小的请求会被拒绝, 上传大文件的网站请适当调大(默认 12800 KB)。</div></td></tr>' +
            '<tr><td>IP 白名单</td><td><textarea class="bt-input-text" name="ip_whitelist" style="width:320px;height:60px"></textarea>' +
                '<div class="ms-help">这些 IP/网段的请求不做检测, 多个用空格或换行分隔。</div></td></tr>' +
            '<tr><td>停用的规则ID</td><td><textarea class="bt-input-text" name="disabled_rules" style="width:320px;height:60px"></textarea>' +
                '<div class="ms-help">出现误报时, 在拦截日志中点击"停用规则", 或在这里填写规则ID, 多个用空格分隔。</div></td></tr>' +
            '</table>' +
            '<div style="margin-top:12px"><button class="btn btn-success btn-sm" data-act="save">保存</button></div></div>');
        form.find('[name=paranoia]').val(String(s.paranoia || 1));
        form.find('[name=inbound_threshold]').val(s.inbound_threshold);
        form.find('[name=outbound_threshold]').val(s.outbound_threshold);
        form.find('[name=body_limit_kb]').val(s.body_limit_kb);
        form.find('[name=ip_whitelist]').val((s.ip_whitelist || []).join('\n'));
        form.find('[name=disabled_rules]').val((s.disabled_rules || []).join(' '));
        form.find('[data-act=save]').on('click', function () {
            msCall('set_config', {
                paranoia: form.find('[name=paranoia]').val(),
                inbound_threshold: form.find('[name=inbound_threshold]').val(),
                outbound_threshold: form.find('[name=outbound_threshold]').val(),
                body_limit_kb: form.find('[name=body_limit_kb]').val(),
                ip_whitelist: form.find('[name=ip_whitelist]').val(),
                disabled_rules: form.find('[name=disabled_rules]').val()
            }, function (r) { msResult(r, msSettings); });
        });
        $('.soft-man-con').empty().append(form);
    });
}

// ------------------------------- 站点设置 ---------------------------------------

function msSites() {
    msMenu(2);
    msCall('site_list', {}, function (r) {
        var list = r.data || [];
        var rows = '';
        for (var i = 0; i < list.length; i++) {
            var m = list[i];
            rows += '<tr data-name="' + msEsc(m.name) + '"><td>' + msEsc(m.name) + '</td><td>' +
                '<select class="bt-input-text" style="width:150px">' +
                '<option value="inherit"' + (m.mode === 'inherit' ? ' selected' : '') + '>跟随全局</option>' +
                '<option value="detect"' + (m.mode === 'detect' ? ' selected' : '') + '>仅记录</option>' +
                '<option value="off"' + (m.mode === 'off' ? ' selected' : '') + '>关闭防护</option>' +
                '</select></td></tr>';
        }
        if (!rows) rows = '<tr><td colspan="2" style="text-align:center;color:#9ca3af">还没有网站</td></tr>';
        var html = '<div class="ms-help" style="margin-bottom:10px">可以为单个网站关闭防护或设为仅记录(例如后台管理程序误报较多时)。</div>' +
            '<div class="divtable" style="max-height:400px;overflow:auto"><table class="table table-hover ms-table"><thead><tr><th>网站</th><th>防护</th></tr></thead>' +
            '<tbody id="msSiteBody">' + rows + '</tbody></table></div>';
        $('.soft-man-con').html(html);
        $('#msSiteBody select').on('change', function () {
            var name = $(this).closest('tr').attr('data-name');
            msCall('set_site', { name: name, mode: $(this).val() }, function (r) { msResult(r); });
        });
    });
}

// ------------------------------- 拦截日志 ---------------------------------------

function msLogs() {
    msMenu(3);
    msCall('get_logs', { limit: 200 }, function (r) {
        var d = r.data || {};
        var list = d.list || [];
        var rows = '';
        for (var i = 0; i < list.length; i++) {
            var e = list[i];
            var rules = '';
            for (var j = 0; j < e.rules.length; j++) {
                var rule = e.rules[j];
                if (rule.id === '949110' || rule.id === '959100' || rule.id === '980170') continue;
                rules += '<div class="ms-rule"><b>' + msEsc(rule.id) + '</b> ' + msEsc(rule.msg) +
                    ' <a class="btlink" data-rule="' + msEsc(rule.id) + '">停用规则</a></div>';
            }
            // "Thu Nov 26 13:20:55 2026" -> "Nov 26 13:20:55"
            var tm = String(e.time || '').replace(/^\w{3}\s+/, '').replace(/\s+\d{4}$/, '');
            rows += '<tr><td style="white-space:nowrap" title="' + msEsc(e.time) + '">' + msEsc(tm) + '</td>' +
                '<td style="white-space:nowrap">' + msEsc(e.ip) + '</td>' +
                '<td><div class="ms-uri"><span style="color:#6b7280">' + msEsc(e.host) + '</span><br><b>' + msEsc(e.method) + '</b> ' + msEsc(e.uri) + '</div></td>' +
                '<td style="white-space:nowrap">' + (e.intercepted ? '<span class="ms-tag red">已拦截</span>' : '<span class="ms-tag orange">已记录</span>') + '</td>' +
                '<td>' + (rules || '-') + '</td></tr>';
        }
        if (!rows) rows = '<tr><td colspan="5" style="text-align:center;color:#9ca3af">暂无记录</td></tr>';
        var html = '<div class="ms-toolbar"><button class="btn btn-default btn-sm" onclick="msLogs()">刷新</button>' +
            '<button class="btn btn-default btn-sm" data-act="clear">清空日志</button>' +
            '<span class="ms-help">最近 200 条, 日志大小 ' + toSize(d.size || 0) + '</span></div>' +
            '<div class="divtable" style="max-height:420px;overflow:auto"><table class="table table-hover ms-table"><thead><tr>' +
            '<th>时间</th><th>来源IP</th><th>请求</th><th>结果</th><th>命中规则</th></tr></thead><tbody id="msLogBody">' + rows + '</tbody></table></div>';
        $('.soft-man-con').html(html);
        $('.soft-man-con [data-act=clear]').on('click', function () {
            layer.confirm('确定清空拦截日志吗?', { icon: 3, title: '清空日志' }, function () {
                msCall('clear_logs', {}, function (r) { msResult(r, msLogs); });
            });
        });
        $('#msLogBody a[data-rule]').on('click', function () {
            var id = $(this).attr('data-rule');
            layer.confirm('停用规则 ' + msEsc(id) + ' 后, 所有网站都不再检测这条规则。确认这是误报吗?', { icon: 3, title: '停用规则' }, function () {
                msCall('disable_rule', { id: id }, function (r) { msResult(r); });
            });
        });
    });
}

function msHelp() {
    msMenu(4);
    $('.soft-man-con').html('<div class="ms-box" style="line-height:24px;font-size:13px">' +
        '<p>本防火墙基于 <b>ModSecurity v3</b> 与 <b>OWASP 核心规则集(CRS)</b>, 防护 SQL 注入、XSS、命令注入、本地/远程文件包含、PHP/Java 代码注入、协议违规和扫描器等常见攻击。</p>' +
        '<p><b>建议使用方式</b>: ① 安装后默认"仅记录"; ② 正常使用网站几天, 在拦截日志中检查是否有误报, 必要时停用对应规则或为某个网站单独关闭; ③ 确认后切换为"拦截"。</p>' +
        '<p><b>与 OP防火墙的关系</b>: 本插件负责攻击检测; CC 防护、IP 黑白名单、地区屏蔽请继续使用 OP防火墙。</p>' +
        '<p><b>升级 OpenResty</b>: 升级后会自动按新版本重新编译防火墙模块; 如编译失败会自动停用防火墙, 保证网站正常访问。</p>' +
        '</div>');
}
