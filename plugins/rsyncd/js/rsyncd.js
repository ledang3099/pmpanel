// ---------------------------------------------------------------------------------
// PM-Linux面板 rsync 同步插件
// Licensed under the Apache License 2.0. See LICENSE and NOTICE.
// ---------------------------------------------------------------------------------

function rsEsc(s) {
    if (typeof htmlAttrEscape === 'function') return htmlAttrEscape(s);
    return String(s == null ? '' : s).replace(/[&<>"'`]/g, function (c) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;', '`': '&#96;' }[c];
    });
}

// 调用插件函数: 参数为对象, 返回 {status, msg, data}
function rsCall(func, args, callback, loadingText) {
    var loadT = loadingText === false ? null : layer.msg(loadingText || '正在处理...', { icon: 16, time: 0, shade: 0.3 });
    $.post('/plugins/callback', { name: 'rsyncd', func: func, args: JSON.stringify(args || {}), script: 'index' }, function (res) {
        if (loadT !== null) layer.close(loadT);
        if (!res.status) {
            layer.msg(rsEsc(res.msg || '调用失败'), { icon: 2, time: 5000 });
            return;
        }
        var r = res.data || {};
        if (typeof callback === 'function') callback(r);
    }, 'json').fail(function () {
        if (loadT !== null) layer.close(loadT);
        layer.msg('请求失败', { icon: 2 });
    });
}

// 先渲染空容器, 再放入表单, 然后按实际高度重新居中(避免对话框超出屏幕)
function rsOpen(opts, node) {
    var wrap = opts.wrap || '<div class="rs-dlg"></div>';
    delete opts.wrap;
    var success = opts.success;
    opts.content = wrap;
    opts.success = function (layero, index) {
        (layero.find('.rs-dlg').length ? layero.find('.rs-dlg') : layero.find('.layui-layer-content')).append(node);
        var h = layero.outerHeight();
        layero.css('top', Math.max(10, ($(window).height() - h) / 2) + 'px');
        if (typeof success === 'function') success(layero, index);
    };
    return layer.open(opts);
}

function rsResult(r, after) {
    layer.msg(rsEsc(r.msg), { icon: r.status ? 1 : 2, time: r.status ? 2000 : 5000 });
    if (r.status && typeof after === 'function') after();
}

function rsMenu(idx) {
    $('.bt-w-menu p').removeClass('bgw').eq(idx).addClass('bgw');
}

// ------------------------------- 版本与安全 -------------------------------------

function rsOverview() {
    rsCall('get_info', {}, function (r) {
        var d = r.data || {};
        var html = '';
        if (!d.rsync_version) {
            html += '<div class="rs-alert warn">未检测到 rsync 程序, 请重新安装插件。</div>';
        } else if (d.rsync_outdated) {
            html += '<div class="rs-alert warn">当前 rsync ' + rsEsc(d.rsync_version) + ' 低于 3.4.3, 存在 2026 年公开的守护进程漏洞(CVE-2026-29518 等)。' +
                '请在软件管理中重新安装本插件以编译 rsync ' + rsEsc(d.rsync_target) + '; 如系统软件包已打安全补丁可忽略。</div>';
        } else {
            html += '<div class="rs-alert ok">rsync ' + rsEsc(d.rsync_version) + (d.rsync_own_build ? ' (插件编译版本)' : ' (系统软件包)') + '</div>';
        }
        if ((d.open_all_modules || []).length) {
            html += '<div class="rs-alert warn">以下接收目录由旧版本迁移而来, 仍对所有 IP 开放: ' + rsEsc(d.open_all_modules.join(', ')) +
                '。请在"接收"中编辑并填写允许访问的 IP。</div>';
        }
        if (d.port_open) {
            html += '<div class="rs-alert info">防火墙已放行 rsync 端口 ' + rsEsc(d.port) + '。rsync 协议不加密, 请只允许可信服务器的 IP 访问各接收目录。</div>';
        }
        html += '<table class="rs-kv">' +
            '<tr><td>rsync 程序</td><td>' + rsEsc(d.rsync_bin || '-') + '</td></tr>' +
            '<tr><td>rsync 版本</td><td>' + rsEsc(d.rsync_version || '-') + '</td></tr>' +
            '<tr><td>lsyncd(实时同步)</td><td>' + (d.lsyncd_bin ? rsEsc(d.lsyncd_bin) : '<span class="rs-tag red">未安装</span> 仅可使用定时同步') + '</td></tr>' +
            '<tr><td>服务端口</td><td>' + rsEsc(d.port) + ' ' + (d.port_open ? '<span class="rs-tag green">防火墙已放行</span>' :
                '<span class="rs-tag">未放行</span> <button class="btn btn-default btn-xs" onclick="rsOpenPort()">放行端口</button>') + '</td></tr>' +
            '<tr><td>接收目录 / 同步任务</td><td>' + rsEsc(d.receive_count) + ' / ' + rsEsc(d.send_count) + '</td></tr>' +
            '</table>';
        $('.soft-man-con').html('<div class="rs-box">' + html + '</div>');
    });
}

function rsOpenPort() {
    layer.confirm('rsync 协议不加密。放行端口后, 只有各接收目录中"允许访问的IP"能连接。确定放行吗?', { icon: 3, title: '放行端口' }, function () {
        rsCall('open_port', {}, function (r) { rsResult(r, rsOverview); });
    });
}

// ------------------------------- 接收端 -----------------------------------------

function rsReceive() {
    rsCall('rec_list', {}, function (r) {
        var list = r.data || [];
        var rows = '';
        for (var i = 0; i < list.length; i++) {
            var m = list[i];
            var hosts = m.open_all ? '<span class="rs-tag red">所有IP</span>' :
                (m.hosts && m.hosts.length ? rsEsc(m.hosts.join(' ')) : '<span class="rs-tag">仅本机</span>');
            rows += '<tr data-name="' + rsEsc(m.name) + '">' +
                '<td>' + rsEsc(m.name) + '</td>' +
                '<td><span class="rs-ellipsis" title="' + rsEsc(m.path) + '">' + rsEsc(m.path) + '</span></td>' +
                '<td>' + hosts + '</td>' +
                '<td>' + (m.read_only ? '<span class="rs-tag blue">只读</span>' : '<span class="rs-tag green">可写</span>') + '</td>' +
                '<td style="text-align:right">' +
                    '<a class="btlink" data-act="key">密钥</a> | ' +
                    '<a class="btlink" data-act="edit">编辑</a> | ' +
                    '<a class="btlink" data-act="del">删除</a></td>' +
                '</tr>';
        }
        if (!rows) rows = '<tr><td colspan="5" style="text-align:center;color:#9ca3af">还没有接收目录。接收目录用于让其他服务器把文件同步到本机。</td></tr>';
        var html = '<div class="rs-toolbar"><button class="btn btn-success btn-sm" onclick="rsRecEdit(\'\')">添加接收目录</button>' +
            '<span style="color:#9ca3af;font-size:12px">本机作为服务端, 接收其他服务器发送的文件</span></div>' +
            '<div class="divtable" style="max-height:380px;overflow:auto"><table class="table table-hover rs-table"><thead><tr>' +
            '<th>名称</th><th>目录</th><th>允许的IP</th><th>权限</th><th style="text-align:right">操作</th>' +
            '</tr></thead><tbody id="rsRecBody">' + rows + '</tbody></table></div>';
        $('.soft-man-con').html(html);
        $('#rsRecBody a[data-act]').on('click', function () {
            var name = $(this).closest('tr').attr('data-name');
            var act = $(this).attr('data-act');
            if (act === 'edit') rsRecEdit(name);
            else if (act === 'key') rsRecKey(name);
            else if (act === 'del') {
                layer.confirm('确定删除接收目录【' + rsEsc(name) + '】吗? (不会删除目录中的文件)', { icon: 3, title: '删除' }, function () {
                    rsCall('rec_delete', { name: name }, function (r) { rsResult(r, rsReceive); });
                });
            }
        });
    });
}

function rsRecEdit(name) {
    rsCall('rec_get', { name: name }, function (r) {
        if (!r.status) { rsResult(r); return; }
        var d = r.data;
        var isNew = name === '';
        var form = $('<div class="bt-form pd20 rs-form">' +
            '<div class="line"><span class="tname">名称</span><div class="info-r"><input class="bt-input-text" name="name" style="width:300px"' + (isNew ? '' : ' disabled') + '>' +
                '<div class="rs-help">字母、数字、下划线、短横线, 同时作为连接用户名</div></div></div>' +
            '<div class="line"><span class="tname">接收目录</span><div class="info-r"><input class="bt-input-text" name="path" style="width:300px"></div></div>' +
            '<div class="line"><span class="tname">密码</span><div class="info-r"><input class="bt-input-text" name="password" style="width:220px"> ' +
                '<button type="button" class="btn btn-default btn-xs" data-act="rand">随机</button></div></div>' +
            '<div class="line"><span class="tname">允许访问的IP</span><div class="info-r"><textarea class="bt-input-text" name="hosts" style="width:300px;height:60px"></textarea>' +
                '<div class="rs-help">发送端服务器的 IP 或网段, 多个用空格或换行分隔, 例如 1.2.3.4 10.0.0.0/24</div></div></div>' +
            '<div class="line"><span class="tname">权限</span><div class="info-r"><select class="bt-input-text" name="read_only" style="width:120px">' +
                '<option value="false">可写(接收)</option><option value="true">只读(仅供拉取)</option></select></div></div>' +
            '<div class="line"><span class="tname">备注</span><div class="info-r"><input class="bt-input-text" name="comment" style="width:300px"></div></div>' +
            '</div>');
        form.find('[name=name]').val(d.name);
        form.find('[name=path]').val(d.path);
        form.find('[name=password]').val(d.password);
        form.find('[name=hosts]').val((d.hosts || []).join(' '));
        form.find('[name=read_only]').val(d.read_only ? 'true' : 'false');
        form.find('[name=comment]').val(d.comment || '');
        form.find('[data-act=rand]').on('click', function () { form.find('[name=password]').val(getRandomString(20)); });
        rsOpen({
            type: 1, title: isNew ? '添加接收目录' : '编辑接收目录', area: '520px', closeBtn: 1,
            btn: ['保存', '取消'],
            yes: function (index) {
                var args = {
                    is_new: isNew ? '1' : '0',
                    name: form.find('[name=name]').val(),
                    path: form.find('[name=path]').val(),
                    password: form.find('[name=password]').val(),
                    hosts: form.find('[name=hosts]').val(),
                    read_only: form.find('[name=read_only]').val(),
                    comment: form.find('[name=comment]').val()
                };
                rsCall('rec_save', args, function (r) { rsResult(r, function () { layer.close(index); rsReceive(); }); });
            }
        }, form);
    });
}

function rsRecKey(name) {
    rsCall('rec_client_cmd', { name: name }, function (r) {
        if (!r.status) { rsResult(r); return; }
        var box = $('<div class="pd20">' +
            '<p style="margin-bottom:6px">接收端密钥(在发送端"添加同步任务"时粘贴):</p><div class="rs-pre" data-k="key"></div>' +
            '<p style="margin:12px 0 6px">或在发送端服务器手动执行:</p><div class="rs-pre" data-k="cmd"></div>' +
            '<p class="rs-help" style="margin-top:8px;color:#b45309">密钥包含密码, 请勿泄露。</p></div>');
        box.find('[data-k=key]').text(r.data.secret_key);
        box.find('[data-k=cmd]').text(r.data.cmd);
        rsOpen({ type: 1, title: '连接信息【' + rsEsc(name) + '】', area: '560px', closeBtn: 1 }, box);
    });
}

// ------------------------------- 发送端 -----------------------------------------

function rsSend() {
    rsCall('send_list', {}, function (r) {
        var list = r.data || [];
        var rows = '';
        for (var i = 0; i < list.length; i++) {
            var t = list[i];
            var mode = t.realtime ? '<span class="rs-tag green">实时</span>' :
                '<span class="rs-tag blue">' + (t.period === 'minute-n' ? ('每' + rsEsc(t.minute_n) + '分钟') : ('每天 ' + rsEsc(t.hour) + ':' + ('0' + t.minute).slice(-2))) + '</span>';
            rows += '<tr data-name="' + rsEsc(t.name) + '">' +
                '<td>' + rsEsc(t.name) + '</td>' +
                '<td><span class="rs-ellipsis" title="' + rsEsc(t.path) + '">' + rsEsc(t.path) + '</span></td>' +
                '<td>' + rsEsc(t.ip) + ':' + rsEsc(t.port) + '::' + rsEsc(t.module) + '</td>' +
                '<td>' + mode + (t['delete'] ? '<span class="rs-tag red">镜像删除</span>' : '') + '</td>' +
                '<td style="text-align:right">' +
                    '<a class="btlink" data-act="run">立即同步</a> | ' +
                    '<a class="btlink" data-act="log">日志</a> | ' +
                    '<a class="btlink" data-act="exclude">排除</a> | ' +
                    '<a class="btlink" data-act="edit">编辑</a> | ' +
                    '<a class="btlink" data-act="del">删除</a></td>' +
                '</tr>';
        }
        if (!rows) rows = '<tr><td colspan="5" style="text-align:center;color:#9ca3af">还没有同步任务。同步任务用于把本机目录发送到其他服务器的接收目录。</td></tr>';
        var html = '<div class="rs-toolbar"><button class="btn btn-success btn-sm" onclick="rsSendEdit(\'\')">添加同步任务</button>' +
            '<span style="color:#9ca3af;font-size:12px">本机作为发送端, 把目录同步到其他服务器</span></div>' +
            '<div class="divtable" style="max-height:380px;overflow:auto"><table class="table table-hover rs-table"><thead><tr>' +
            '<th>任务</th><th>本机目录</th><th>目标</th><th>方式</th><th style="text-align:right">操作</th>' +
            '</tr></thead><tbody id="rsSendBody">' + rows + '</tbody></table></div>';
        $('.soft-man-con').html(html);
        $('#rsSendBody a[data-act]').on('click', function () {
            var name = $(this).closest('tr').attr('data-name');
            var act = $(this).attr('data-act');
            if (act === 'edit') rsSendEdit(name);
            else if (act === 'run') rsCall('send_run', { name: name }, function (r) { rsResult(r); });
            else if (act === 'log') rsShowLog(name);
            else if (act === 'exclude') rsExclude(name);
            else if (act === 'del') {
                layer.confirm('确定删除同步任务【' + rsEsc(name) + '】吗?', { icon: 3, title: '删除' }, function () {
                    rsCall('send_delete', { name: name }, function (r) { rsResult(r, rsSend); });
                });
            }
        });
    });
}

function rsSendEdit(name) {
    rsCall('send_get', { name: name }, function (r) {
        if (!r.status) { rsResult(r); return; }
        var d = r.data;
        var isNew = name === '';
        var form = $('<div class="bt-form pd20 rs-form">' +
            '<div class="line"><span class="tname">任务名称</span><div class="info-r"><input class="bt-input-text" name="name" style="width:300px"' + (isNew ? '' : ' disabled') + '></div></div>' +
            '<div class="line"><span class="tname">接收端地址</span><div class="info-r"><input class="bt-input-text" name="ip" style="width:300px" placeholder="接收端服务器 IP 或域名"></div></div>' +
            '<div class="line"><span class="tname">连接方式</span><div class="info-r"><select class="bt-input-text" name="conn" style="width:160px">' +
                '<option value="key">粘贴接收端密钥</option><option value="manual">手动填写</option></select></div></div>' +
            '<div class="line rs-key"><span class="tname">接收端密钥</span><div class="info-r"><textarea class="bt-input-text" name="secret_key" style="width:300px;height:56px" placeholder="在接收端的 接收 > 密钥 中复制"></textarea></div></div>' +
            '<div class="rs-manual">' +
                '<div class="line"><span class="tname">接收目录名</span><div class="info-r"><input class="bt-input-text" name="module" style="width:300px"></div></div>' +
                '<div class="line"><span class="tname">密码</span><div class="info-r"><input class="bt-input-text" name="password" type="password" style="width:300px"></div></div>' +
                '<div class="line"><span class="tname">端口</span><div class="info-r"><input class="bt-input-text" name="port" style="width:100px"></div></div>' +
            '</div>' +
            '<div class="line"><span class="tname">本机目录</span><div class="info-r"><input class="bt-input-text" name="path" style="width:300px"></div></div>' +
            '<div class="line"><span class="tname">同步方式</span><div class="info-r"><select class="bt-input-text" name="realtime" style="width:120px">' +
                '<option value="true">实时同步</option><option value="false">定时同步</option></select> ' +
                '<span class="rs-rt">延迟 <input class="bt-input-text" name="delay" style="width:60px"> 秒</span></div></div>' +
            '<div class="line rs-period"><span class="tname">定时周期</span><div class="info-r"><select class="bt-input-text" name="period" style="width:100px">' +
                '<option value="day">每天</option><option value="minute-n">每隔N分钟</option></select> ' +
                '<span class="rs-day"><input class="bt-input-text" name="hour" style="width:50px"> 时 <input class="bt-input-text" name="minute" style="width:50px"> 分</span>' +
                '<span class="rs-n"><input class="bt-input-text" name="minute_n" style="width:60px"> 分钟</span></div></div>' +
            '<div class="line"><span class="tname">限速</span><div class="info-r"><input class="bt-input-text" name="bwlimit" style="width:100px"> KB/s <span class="rs-help" style="display:inline">0 为不限速</span></div></div>' +
            '<div class="line"><span class="tname">选项</span><div class="info-r">' +
                '<label style="font-weight:400;margin-right:16px"><input type="checkbox" name="compress"> 压缩传输</label>' +
                '<label style="font-weight:400"><input type="checkbox" name="delete"> 镜像删除(目标端删除本机已删除的文件)</label></div></div>' +
            '</div>');
        form.find('[name=name]').val(d.name);
        form.find('[name=ip]').val(d.ip);
        form.find('[name=module]').val(d.module);
        form.find('[name=password]').val(d.password);
        form.find('[name=port]').val(d.port);
        form.find('[name=path]').val(d.path);
        form.find('[name=realtime]').val(d.realtime ? 'true' : 'false');
        form.find('[name=delay]').val(d.delay);
        form.find('[name=period]').val(d.period);
        form.find('[name=hour]').val(d.hour);
        form.find('[name=minute]').val(d.minute);
        form.find('[name=minute_n]').val(d.minute_n);
        form.find('[name=bwlimit]').val(d.bwlimit);
        form.find('[name=compress]').prop('checked', !!d.compress);
        form.find('[name=delete]').prop('checked', !!d['delete']);
        form.find('[name=conn]').val(isNew ? 'key' : 'manual');
        var sync = function () {
            var key = form.find('[name=conn]').val() === 'key';
            form.find('.rs-key').toggle(key);
            form.find('.rs-manual').toggle(!key);
            var rt = form.find('[name=realtime]').val() === 'true';
            form.find('.rs-rt').toggle(rt);
            form.find('.rs-period').toggle(!rt);
            var day = form.find('[name=period]').val() === 'day';
            form.find('.rs-day').toggle(day);
            form.find('.rs-n').toggle(!day);
        };
        form.find('select').on('change', sync);
        sync();
        rsOpen({
            type: 1, title: isNew ? '添加同步任务' : '编辑同步任务', area: '560px', closeBtn: 1,
            btn: ['保存', '取消'],
            yes: function (index) {
                var useKey = form.find('[name=conn]').val() === 'key';
                var module = form.find('[name=module]').val();
                var args = {
                    is_new: isNew ? '1' : '0',
                    name: form.find('[name=name]').val(),
                    ip: form.find('[name=ip]').val(),
                    secret_key: useKey ? form.find('[name=secret_key]').val() : '',
                    module: module, user: module,
                    password: form.find('[name=password]').val(),
                    port: form.find('[name=port]').val(),
                    path: form.find('[name=path]').val(),
                    realtime: form.find('[name=realtime]').val(),
                    delay: form.find('[name=delay]').val(),
                    period: form.find('[name=period]').val(),
                    hour: form.find('[name=hour]').val(),
                    minute: form.find('[name=minute]').val(),
                    minute_n: form.find('[name=minute_n]').val(),
                    bwlimit: form.find('[name=bwlimit]').val(),
                    compress: form.find('[name=compress]').prop('checked') ? 'true' : 'false',
                    'delete': form.find('[name=delete]').prop('checked') ? 'true' : 'false'
                };
                rsCall('send_save', args, function (r) { rsResult(r, function () { layer.close(index); rsSend(); }); });
            }
        }, form);
    });
}

function rsExclude(name) {
    rsCall('send_get', { name: name }, function (r) {
        if (!r.status) { rsResult(r); return; }
        var ta = $('<textarea class="bt-input-text" style="width:100%;height:220px;font-family:monospace"></textarea>');
        ta.val((r.data.exclude || []).join('\n'));
        rsOpen({
            type: 1, title: '排除规则【' + rsEsc(name) + '】', area: '480px', closeBtn: 1, btn: ['保存', '取消'],
            wrap: '<div class="pd20"><p class="rs-help" style="margin-bottom:8px">每行一条 rsync 排除规则, 例如 **/*.log 、.git 、/cache/</p><div class="rs-dlg"></div></div>',
            yes: function (index) {
                rsCall('send_set_exclude', { name: name, exclude: ta.val() }, function (r) { rsResult(r, function () { layer.close(index); }); });
            }
        }, ta);
    });
}

// ------------------------------- 日志 / 说明 ------------------------------------

function rsShowLog(name) {
    rsCall('send_log', { name: name }, function (r) {
        var pre = $('<div class="rs-pre"></div>').text(r.data || '暂无日志');
        rsOpen({ type: 1, title: '同步日志【' + rsEsc(name) + '】', area: ['720px', '480px'], closeBtn: 1,
            wrap: '<div class="pd15 rs-dlg"></div>' }, pre);
    });
}

function rsLogs() {
    var html = '<div class="rs-toolbar">' +
        '<button class="btn btn-default btn-sm" data-log="rec">接收服务日志</button>' +
        '<button class="btn btn-default btn-sm" data-log="lsyncd">实时同步日志</button></div>' +
        '<div class="rs-pre" id="rsLogBox" style="max-height:400px">请选择日志</div>';
    $('.soft-man-con').html(html);
    $('.soft-man-con [data-log]').on('click', function () {
        var which = $(this).attr('data-log');
        var func = which === 'rec' ? 'rec_log' : 'send_log';
        rsCall(func, which === 'rec' ? {} : { name: '__lsyncd__' }, function (r) {
            $('#rsLogBox').text(r.data || '暂无日志');
        }, false);
    });
    $('.soft-man-con [data-log=rec]').click();
}

function rsHelp() {
    var html = '<div class="rs-box" style="line-height:24px;font-size:13px">' +
        '<p><b>接收(服务端)</b>: 在本机开启 rsync 服务, 其他服务器把文件同步过来。每个接收目录有独立的用户名、密码和允许访问的 IP。</p>' +
        '<p><b>发送(同步任务)</b>: 把本机目录同步到其他服务器的接收目录, 支持 lsyncd 实时同步和计划任务定时同步。</p>' +
        '<p><b>使用步骤</b>: ① 在接收端服务器添加接收目录, 填写发送端的 IP; ② 在 接收 > 密钥 复制连接密钥; ③ 在发送端服务器添加同步任务, 粘贴密钥。</p>' +
        '<p><b>安全提示</b>: rsync 协议不加密传输内容, 跨公网同步敏感数据时建议通过内网或 VPN; 务必为每个接收目录限制允许访问的 IP; 服务以 chroot 方式运行。</p>' +
        '</div>';
    $('.soft-man-con').html(html);
}
