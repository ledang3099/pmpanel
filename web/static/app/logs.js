// PM-Linux面板 日志: 面板 / 网站 / SSH / 计划任务 / 软件 / 系统 / 清理

var LG = { timer: null, op: { page: 1, search: '', type: '' }, ssh: { page: 1, status: 'all', search: '' } };

$(function () {
    pmTabs('#logPanel', function (name) {
        lgStopAuto();
        if (name == 'panel') lgPanel();
        if (name == 'site') lgSite();
        if (name == 'ssh') lgSsh();
        if (name == 'cron') lgCron();
        if (name == 'soft') lgSoft();
        if (name == 'system') lgSystem();
        if (name == 'clean') lgClean();
    });
});

function lgStopAuto() {
    if (LG.timer) { clearInterval(LG.timer); LG.timer = null; }
}

function lgTime(ts) {
    if (!ts) return '-';
    var d = new Date(ts * 1000), p = function (n) { return n < 10 ? '0' + n : n; };
    return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) + ' ' + p(d.getHours()) + ':' + p(d.getMinutes());
}

// 左侧列表
function lgList(id, items, cur, onPick) {
    var html = '';
    for (var i = 0; i < items.length; i++) {
        var it = items[i];
        html += '<div data-i="' + i + '" class="' + (it.key == cur ? 'on' : '') + '" title="' + pmEsc(it.tip || it.title) + '"><span>' + pmEsc(it.title) + '</span>' +
            '<span class="pm-muted">' + pmEsc(it.extra || '') + '</span></div>';
    }
    if (!html) html = '<div class="pm-muted" style="cursor:default">暂无</div>';
    $('#' + id).html(html);
    $('#' + id + ' [data-i]').on('click', function () {
        $('#' + id + ' [data-i]').removeClass('on');
        $(this).addClass('on');
        onPick(items[$(this).attr('data-i')]);
    });
}

// 通用日志查看器
// opts: { box, load(params, cb), clear(cb)|null, download(): path|null, extra: html }
function lgViewer(opts) {
    lgStopAuto();
    var box = $(opts.box);
    box.html('<div class="pm-toolbar">' + (opts.extra || '') +
        '<select class="bt-input-text lg-lines" style="width:110px"><option value="100">最后 100 行</option><option value="200" selected>最后 200 行</option>' +
        '<option value="500">最后 500 行</option><option value="1000">最后 1000 行</option><option value="5000">最后 5000 行</option></select>' +
        '<input class="bt-input-text lg-search" style="width:200px" placeholder="关键词过滤">' +
        '<button class="btn btn-default btn-sm lg-go">搜索</button><button class="btn btn-default btn-sm lg-refresh">刷新</button>' +
        '<label class="pm-muted" style="margin:0;cursor:pointer"><input type="checkbox" class="lg-auto" style="vertical-align:-2px"> 自动刷新</label>' +
        '<div class="pm-right">' + (opts.download ? '<button class="btn btn-default btn-sm lg-dl">下载</button>' : '') +
        (opts.clear ? '<button class="btn btn-danger btn-sm lg-clear">清空</button>' : '') + '</div></div>' +
        '<pre class="lg-view">加载中...</pre><div class="lg-path" style="margin-top:6px"></div>');
    var run = function (quiet) {
        var kw = $.trim(box.find('.lg-search').val());
        opts.load({ lines: box.find('.lg-lines').val(), search: kw }, function (d) {
            if (!d) return;
            var view = box.find('.lg-view');
            var atBottom = view[0].scrollHeight - view.scrollTop() - view.outerHeight() < 30;
            if (d.table) { view.html(lgTable(d.table)); return; }
            var lines = d.lines || [];
            var html = lines.map(function (l) {
                var s = pmEsc(l);
                if (kw) {
                    var re = new RegExp(kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'), 'gi');
                    s = s.replace(re, function (m) { return '<mark>' + m + '</mark>'; });
                }
                if (/\b(error|fatal|crit|emerg|alert|failed)\b/i.test(l)) return '<span class="lg-err">' + s + '</span>';
                if (/\b(warn|warning|notice)\b/i.test(l)) return '<span class="lg-warn">' + s + '</span>';
                return s;
            }).join('\n');
            if (!d.exists && d.exists !== undefined) html = '<span class="pm-muted">日志文件不存在或尚未生成</span>';
            else if (!lines.length) html = '<span class="pm-muted">' + (kw ? '没有匹配的内容' : '日志为空') + '</span>';
            view.html(html);
            if (!quiet || atBottom) view.scrollTop(view[0].scrollHeight);
            box.find('.lg-path').text((d.path ? d.path + '  ·  ' : '') + '大小 ' + toSize(d.size || 0) + (d.mtime ? '  ·  更新于 ' + lgTime(d.mtime) : ''));
        });
    };
    box.find('.lg-go, .lg-refresh').on('click', function () { run(false); });
    box.find('.lg-lines').on('change', function () { run(false); });
    box.find('.lg-search').on('keydown', function (e) { if (e.keyCode == 13) run(false); });
    box.find('.lg-auto').on('change', function () {
        lgStopAuto();
        if (this.checked) LG.timer = setInterval(function () { if (box.is(':visible')) run(true); else lgStopAuto(); }, 3000);
    });
    box.find('.lg-dl').on('click', function () {
        var p = opts.download();
        if (p) window.open('/files/download?filename=' + encodeURIComponent(p), '_blank');
    });
    box.find('.lg-clear').on('click', function () {
        layer.confirm('确定清空该日志吗? 此操作不可恢复。', { icon: 3, title: '清空日志' }, function (idx) {
            layer.close(idx);
            opts.clear(function () { run(false); });
        });
    });
    run(false);
    return run;
}

function lgTable(rows) {
    if (!$.isArray(rows) || !rows.length) return '<span class="pm-muted">没有记录</span>';
    var keys = Object.keys(rows[0]);
    var w = keys.map(function (k) { return Math.max(k.length * 2, 8); });
    rows.forEach(function (r) { keys.forEach(function (k, i) { w[i] = Math.max(w[i], String(r[k] || '').length); }); });
    var line = function (vals) { return vals.map(function (v, i) { v = String(v || ''); return v + new Array(Math.max(1, w[i] - v.length + 3)).join(' '); }).join(''); };
    return pmEsc([line(keys)].concat(rows.map(function (r) { return line(keys.map(function (k) { return r[k]; })); })).join('\n'));
}

function lgPost(url, data, cb) {
    pmPost(url, data, function (r) {
        if (!r.status) { pmResult(r); cb && cb(null); return; }
        cb && cb(r.data);
    }, { silent: true });
}

// ================================ 面板日志 ================================

function lgPanel() {
    $('#logBody').html('<div class="pm-toolbar"><div class="pm-subtabs" id="lpSub"><span data-v="op" class="on">操作日志</span><span data-v="run">运行日志</span></div></div><div id="lpBody"></div>');
    $('#lpSub span').on('click', function () {
        $('#lpSub span').removeClass('on');
        $(this).addClass('on');
        lgStopAuto();
        $(this).attr('data-v') == 'op' ? lgOperation() : lgPanelRun();
    });
    lgOperation();
}

function lgOperation() {
    $('#lpBody').html('<div class="pm-toolbar"><select class="bt-input-text lg-type" id="loType"><option value="">全部类型</option></select>' +
        '<input class="bt-input-text" id="loSearch" style="width:220px" placeholder="搜索日志内容" value="' + pmEsc(LG.op.search) + '">' +
        '<button class="btn btn-default btn-sm" id="loGo">搜索</button>' +
        '<div class="pm-right"><button class="btn btn-default btn-sm" id="loExport">导出 CSV</button><button class="btn btn-danger btn-sm" id="loClear">清空日志</button></div></div>' +
        '<div class="divtable"><table class="table table-hover pm-table"><thead><tr><th width="170">时间</th><th width="130">类型</th><th>详情</th></tr></thead><tbody id="loList"></tbody></table></div><div id="loPager"></div>');
    lgPost('/logs/operation_types', {}, function (types) {
        (types || []).forEach(function (t) { $('#loType').append('<option value="' + pmEsc(t) + '"' + (t == LG.op.type ? ' selected' : '') + '>' + pmEsc(t) + '</option>'); });
    });
    $('#loType').on('change', function () { LG.op.type = $(this).val(); lgOperationLoad(1); });
    $('#loGo').on('click', function () { LG.op.search = $.trim($('#loSearch').val()); lgOperationLoad(1); });
    $('#loSearch').on('keydown', function (e) { if (e.keyCode == 13) $('#loGo').trigger('click'); });
    $('#loExport').on('click', function () {
        window.open('/logs/operation_export?search=' + encodeURIComponent(LG.op.search) + '&type=' + encodeURIComponent(LG.op.type), '_blank');
    });
    $('#loClear').on('click', function () {
        layer.confirm('确定清空全部面板操作日志吗?', { icon: 3, title: '清空日志' }, function (idx) {
            layer.close(idx);
            pmPost('/logs/del_panel_logs', {}, function (r) { pmResult(r, function () { lgOperationLoad(1); }); });
        });
    });
    lgOperationLoad(LG.op.page);
}

function lgOperationLoad(page) {
    LG.op.page = page;
    lgPost('/logs/operation', { p: page, limit: 20, search: LG.op.search, type: LG.op.type }, function (d) {
        if (!d) return;
        var rows = '';
        for (var i = 0; i < d.list.length; i++) {
            var x = d.list[i];
            rows += '<tr><td>' + pmEsc(x.add_time) + '</td><td><span class="pm-tag">' + pmEsc(x.type) + '</span></td><td style="word-break:break-all">' + pmEsc(x.log) + '</td></tr>';
        }
        if (!rows) rows = '<tr><td colspan="3" class="pm-empty">暂无日志</td></tr>';
        $('#loList').html(rows);
        pmPager('loPager', d.total, page, 20, lgOperationLoad);
    });
}

function lgPanelRun() {
    $('#lpBody').html('<div class="lg-layout"><div class="lg-list" id="lrList"></div><div id="lrView"></div></div>');
    var cur = 'panel_error';
    var open = function (name) {
        cur = name;
        lgViewer({
            box: '#lrView',
            load: function (p, cb) { lgPost('/logs/panel_run', { name: cur, lines: p.lines, search: p.search }, cb); },
            clear: function (cb) { pmPost('/logs/panel_run_clear', { name: cur }, function (r) { pmResult(r, cb); }); },
            download: null
        });
    };
    lgPost('/logs/panel_run', { name: cur, lines: 1 }, function (d) {
        if (!d) return;
        var items = d.items.map(function (x) { return { key: x.name, title: x.title, extra: toSize(x.size) }; });
        lgList('lrList', items, cur, function (it) { open(it.key); });
        open(cur);
    });
}

// ================================ 网站日志 ================================

function lgSite() {
    $('#logBody').html('<div class="lg-layout"><div><input class="bt-input-text" id="lsFilter" style="width:100%;margin-bottom:8px" placeholder="筛选网站">' +
        '<div class="lg-list" id="lsList"></div></div><div id="lsView"></div></div>');
    lgPost('/logs/site_list', {}, function (d) {
        if (!d) return;
        if (!d.list.length) { $('#lsView').html('<div class="db-empty-box pm-empty">还没有网站</div>'); $('#lsList').html('<div class="pm-muted">暂无网站</div>'); return; }
        var cur = { name: d.list[0].name, type: 'access' };
        var items = d.list.map(function (x) { return { key: x.name, title: x.name, extra: toSize(x.access_size + x.error_size) }; });
        var open = function () {
            lgViewer({
                box: '#lsView',
                extra: '<div class="pm-subtabs" id="lsType"><span data-v="access"' + (cur.type == 'access' ? ' class="on"' : '') + '>访问日志</span>' +
                    '<span data-v="error"' + (cur.type == 'error' ? ' class="on"' : '') + '>错误日志</span></div>',
                load: function (p, cb) { lgPost('/logs/site_log', { name: cur.name, type: cur.type, lines: p.lines, search: p.search }, function (r) { cur.path = r && r.path; cb(r); }); },
                clear: function (cb) { pmPost('/logs/site_log_clear', { name: cur.name, type: cur.type }, function (r) { pmResult(r, cb); }); },
                download: function () { return cur.path; }
            });
            $('#lsType span').on('click', function () { cur.type = $(this).attr('data-v'); open(); });
        };
        var render = function (filter) {
            var list = items.filter(function (x) { return !filter || x.title.indexOf(filter) > -1; });
            lgList('lsList', list, cur.name, function (it) { cur.name = it.key; open(); });
        };
        render('');
        $('#lsFilter').on('input', function () { render($.trim($(this).val())); });
        open();
    });
}

// ================================ SSH 登录日志 ================================

function lgSsh() {
    $('#logBody').html('<div class="pm-stats" id="lhStats"></div><div class="pm-toolbar"><div class="pm-subtabs" id="lhFilter">' +
        '<span data-v="all" class="on">全部</span><span data-v="success">登录成功</span><span data-v="fail">登录失败</span></div>' +
        '<div class="pm-right"><input class="bt-input-text" id="lhSearch" style="width:200px" placeholder="搜索 IP 或用户名"><button class="btn btn-default btn-sm" id="lhGo">搜索</button>' +
        '<a class="btn btn-default btn-sm" href="/firewall/index#ssh">SSH 设置</a></div></div>' +
        '<div class="divtable"><table class="table table-hover pm-table"><thead><tr><th>时间</th><th>用户名</th><th>来源 IP</th><th>端口</th><th>认证方式</th><th>状态</th></tr></thead><tbody id="lhList"></tbody></table></div><div id="lhPager"></div>');
    pmPost('/firewall/ssh_stats', {}, function (r) {
        var st = r.data || {};
        $('#lhStats').html('<div class="pm-stat ok"><div class="pm-stat-label">今日登录成功</div><div class="pm-stat-value">' + (st.success_today || 0) + '<small>次</small></div><div class="pm-stat-sub">累计 ' + (st.success_total || 0) + ' 次</div></div>' +
            '<div class="pm-stat bad"><div class="pm-stat-label">今日登录失败</div><div class="pm-stat-value">' + (st.fail_today || 0) + '<small>次</small></div><div class="pm-stat-sub">累计 ' + (st.fail_total || 0) + ' 次</div></div>' +
            '<div class="pm-stat warn"><div class="pm-stat-label">失败来源 IP</div><div class="pm-stat-value">' + (st.fail_ip_count || 0) + '<small>个</small></div><div class="pm-stat-sub"><a class="btlink" href="/firewall/index#ssh">查看并屏蔽</a></div></div>');
    }, { silent: true });
    $('#lhFilter span').on('click', function () { $('#lhFilter span').removeClass('on'); $(this).addClass('on'); LG.ssh.status = $(this).attr('data-v'); lgSshLoad(1); });
    $('#lhGo').on('click', function () { LG.ssh.search = $.trim($('#lhSearch').val()); lgSshLoad(1); });
    $('#lhSearch').on('keydown', function (e) { if (e.keyCode == 13) $('#lhGo').trigger('click'); });
    lgSshLoad(1);
}

function lgSshLoad(page) {
    pmPost('/firewall/ssh_logs', { p: page, limit: 20, status: LG.ssh.status, search: LG.ssh.search }, function (r) {
        var d = r.data || {}, rows = '';
        (d.list || []).forEach(function (e) {
            rows += '<tr><td>' + pmEsc(e.time) + '</td><td>' + pmEsc(e.user) + '</td><td class="pm-code">' + pmEsc(e.ip) + '</td><td>' + pmEsc(e.port) + '</td>' +
                '<td>' + pmEsc(e.method_name) + '</td><td>' + (e.status ? '<span class="pm-tag green">成功</span>' : '<span class="pm-tag red">失败</span>') + '</td></tr>';
        });
        if (!rows) rows = '<tr><td colspan="6" class="pm-empty">暂无登录记录</td></tr>';
        $('#lhList').html(rows);
        pmPager('lhPager', d.total || 0, page, 20, lgSshLoad);
    }, { silent: true });
}

// ================================ 计划任务日志 ================================

function lgCron() {
    $('#logBody').html('<div class="lg-layout"><div class="lg-list" id="lcList"></div><div id="lcView"></div></div>');
    lgPost('/logs/cron_list', {}, function (list) {
        if (!list) return;
        if (!list.length) { $('#lcList').html('<div class="pm-muted">暂无计划任务</div>'); $('#lcView').html('<div class="pm-empty">还没有计划任务, <a class="btlink" href="/crontab/index">去添加</a></div>'); return; }
        var cur = list[0].id;
        var items = list.map(function (x) { return { key: x.id, title: x.name, extra: toSize(x.size) }; });
        var open = function () {
            lgViewer({
                box: '#lcView',
                load: function (p, cb) { lgPost('/logs/cron_log', { id: cur, lines: p.lines, search: p.search }, cb); },
                clear: function (cb) { pmPost('/logs/cron_log_clear', { id: cur }, function (r) { pmResult(r, cb); }); },
                download: null
            });
        };
        lgList('lcList', items, cur, function (it) { cur = it.key; open(); });
        open();
    });
}

// ================================ 软件日志 ================================

function lgSoft() {
    $('#logBody').html('<div class="lg-layout"><div class="lg-list" id="lfList"></div><div id="lfView"></div></div>');
    lgPost('/logs/soft_list', {}, function (list) {
        if (!list) return;
        if (!list.length) { $('#lfList').html('<div class="pm-muted">暂无</div>'); $('#lfView').html('<div class="pm-empty">已安装的软件还没有生成日志</div>'); return; }
        var cur = list[0];
        var items = list.map(function (x) { return { key: x.key, title: x.title, extra: toSize(x.size), tip: x.path, raw: x }; });
        var open = function () {
            lgViewer({
                box: '#lfView',
                load: function (p, cb) { lgPost('/logs/soft_log', { key: cur.key, lines: p.lines, search: p.search }, cb); },
                clear: null,
                download: function () { return cur.path; }
            });
        };
        lgList('lfList', items, cur.key, function (it) { cur = it.raw; open(); });
        open();
    });
}

// ================================ 系统日志 ================================

var LG_SYS_TITLE = {
    'auth.log': '认证日志(登录/sudo)', 'secure': '认证日志(登录/sudo)', 'syslog': '系统日志', 'messages': '系统日志',
    'kern.log': '内核日志', 'dpkg.log': '软件包安装日志', 'apt/history.log': 'APT 操作记录', 'yum.log': 'YUM 操作记录',
    'cron': '定时任务日志', 'cron.log': '定时任务日志', 'wtmp': '登录历史', 'btmp': '登录失败记录', 'lastlog': '最后登录时间',
    'boot.log': '启动日志', 'ufw.log': '防火墙日志', 'fail2ban.log': 'Fail2ban 日志', 'faillog': '登录失败统计', 'alternatives.log': '系统替代项变更'
};

function lgSystem() {
    $('#logBody').html('<div class="lg-layout"><div><input class="bt-input-text" id="lyFilter" style="width:100%;margin-bottom:8px" placeholder="筛选文件">' +
        '<div class="lg-list" id="lyList"></div></div><div id="lyView"></div></div>');
    lgPost('/logs/system_list', {}, function (list) {
        if (!list) return;
        var items = list.map(function (x) {
            return { key: x.name, title: LG_SYS_TITLE[x.name] ? LG_SYS_TITLE[x.name] + ' (' + x.name + ')' : (x.title && x.title != x.name ? x.title + ' (' + x.name + ')' : x.name), extra: toSize(x.size), tip: x.log_file, raw: x };
        });
        var prio = ['auth.log', 'secure', 'syslog', 'messages', 'kern.log', 'wtmp', 'btmp'];
        items.sort(function (a, b) {
            var ia = prio.indexOf(a.key), ib = prio.indexOf(b.key);
            return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib) || a.key.localeCompare(b.key);
        });
        if (!items.length) { $('#lyList').html('<div class="pm-muted">暂无</div>'); return; }
        var cur = items[0].raw;
        var open = function () {
            lgViewer({
                box: '#lyView',
                load: function (p, cb) { lgPost('/logs/system_log', { name: cur.name, lines: p.lines, search: p.search }, cb); },
                clear: null,
                download: function () { return /^(wtmp|btmp|utmp|lastlog)/.test(cur.name.split('/').pop()) ? null : cur.log_file; }
            });
        };
        var render = function (filter) {
            lgList('lyList', items.filter(function (x) { return !filter || x.title.indexOf(filter) > -1; }), cur.name, function (it) { cur = it.raw; open(); });
        };
        render('');
        $('#lyFilter').on('input', function () { render($.trim($(this).val())); });
        open();
    });
}

// ================================ 日志清理 ================================

function lgClean() {
    $('#logBody').html('<div class="pm-stats lg-clean" id="lnStats"></div><div class="pm-alert info">清空日志只截断文件内容, 不会删除文件, 不影响 Nginx 等服务继续写入。也可以在计划任务中添加"切割日志"任务定期处理。</div>');
    lgPost('/logs/overview', {}, function (d) {
        if (!d) return;
        $('#lnStats').html(
            '<div class="pm-stat"><div class="pm-stat-label">网站日志</div><div class="pm-stat-value">' + toSize(d.site.size) + '</div>' +
            '<div class="pm-stat-sub lg-path">' + pmEsc(d.site.path) + '<br><button class="btn btn-default btn-sm" data-clean="site">清空网站日志</button></div></div>' +
            '<div class="pm-stat"><div class="pm-stat-label">计划任务日志</div><div class="pm-stat-value">' + toSize(d.cron.size) + '</div>' +
            '<div class="pm-stat-sub lg-path">' + pmEsc(d.cron.path) + '<br><button class="btn btn-default btn-sm" data-clean="cron">清空计划任务日志</button></div></div>' +
            '<div class="pm-stat"><div class="pm-stat-label">面板运行日志</div><div class="pm-stat-value">' + toSize(d.panel.size) + '</div>' +
            '<div class="pm-stat-sub lg-path">' + pmEsc(d.panel.path) + '<br><button class="btn btn-default btn-sm" data-goto-panel="1">查看</button></div></div>' +
            '<div class="pm-stat"><div class="pm-stat-label">面板操作日志</div><div class="pm-stat-value">' + d.operation + '<small>条</small></div>' +
            '<div class="pm-stat-sub"><button class="btn btn-default btn-sm" data-clean="op">清空操作日志</button></div></div>');
        $('#lnStats [data-clean]').on('click', function () {
            var t = $(this).attr('data-clean');
            var url = { site: '/logs/clean_site_logs', cron: '/logs/clean_cron_logs', op: '/logs/del_panel_logs' }[t];
            var name = { site: '全部网站日志', cron: '全部计划任务日志', op: '全部面板操作日志' }[t];
            layer.confirm('确定清空' + name + '吗? 此操作不可恢复。', { icon: 3, title: '清理日志' }, function (idx) {
                layer.close(idx);
                pmPost(url, {}, function (r) { pmResult(r, lgClean); });
            });
        });
        $('#lnStats [data-goto-panel]').on('click', function () {
            $('#logPanel .pm-tab[data-tab="panel"]').trigger('click');
            setTimeout(function () { $('#lpSub span[data-v="run"]').trigger('click'); }, 300);
        });
    });
}
