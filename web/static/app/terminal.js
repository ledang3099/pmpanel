// PM-Linux面板 终端: 多标签本机终端 + 常用命令

var TM = { sock: null, terms: {}, order: [], active: '', seq: 0, cmds: [], font: 14 };

$(function () {
    try { TM.font = parseInt(localStorage.getItem('pmTermFont')) || 14; } catch (e) { }
    try { if (localStorage.getItem('pmTermSide') == '0') $('#tmSide').addClass('hide'); } catch (e) { }
    $('#tmFont').val(String(TM.font));

    // 使用长轮询: 面板的 gunicorn 线程模式下, 后台线程主动推送在 WebSocket 通道上不可靠
    TM.sock = io('/', { transports: ['polling'], forceNew: true });
    TM.sock.on('pm_term_out', function (d) {
        var t = TM.terms[d.tid];
        if (t) t.term.write(d.data);
    });
    TM.sock.on('pm_term_exit', function (d) {
        var t = TM.terms[d.tid];
        if (!t) return;
        t.dead = true;
        t.term.write('\r\n\x1b[33m[终端已退出, 按回车键重新连接]\x1b[0m\r\n');
        tmRenderTabs();
    });
    TM.sock.on('connect', function () {
        // 断线重连后, 原有终端的进程已被结束, 标记为已退出
        for (var id in TM.terms) {
            if (TM.terms[id].opened && !TM.terms[id].dead && TM.terms[id].sockId && TM.terms[id].sockId != TM.sock.id) {
                TM.terms[id].dead = true;
                TM.terms[id].term.write('\r\n\x1b[33m[连接已断开, 按回车键重新连接]\x1b[0m\r\n');
            }
        }
        tmRenderTabs();
    });

    $(window).on('pagehide', function () {
        try {
            var fd = new FormData();
            fd.append('sid', TM.sock.id || '');
            navigator.sendBeacon('/terminal/close', fd);
        } catch (e) { }
    });
    $('#tmAdd').on('click', function () { tmNew(); });
    $('#tmFont').on('change', function () {
        TM.font = parseInt($(this).val()) || 14;
        try { localStorage.setItem('pmTermFont', TM.font); } catch (e) { }
        for (var id in TM.terms) { TM.terms[id].term.setOption('fontSize', TM.font); }
        tmFit();
    });
    $('#tmCmdToggle').on('click', function () {
        $('#tmSide').toggleClass('hide');
        try { localStorage.setItem('pmTermSide', $('#tmSide').hasClass('hide') ? '0' : '1'); } catch (e) { }
        tmFit();
    });
    $('#tmFull').on('click', function () {
        $('body').toggleClass('tm-full');
        $(this).text($('body').hasClass('tm-full') ? '退出全屏' : '全屏');
        tmFit();
    });
    $(document).on('keydown', function (e) { if (e.keyCode == 27 && $('body').hasClass('tm-full')) $('#tmFull').trigger('click'); });
    $('#tmCmdAdd').on('click', function () { tmCmdEdit(-1); });
    $(window).on('resize', function () { clearTimeout(TM.rt); TM.rt = setTimeout(tmFit, 150); });

    pmPost('/terminal/info', {}, function (r) {
        var d = r.data || {};
        $('#tmRemote').html(d.webssh ? '<a class="btn btn-default btn-sm" href="/plugins/menu?tag=webssh">远程服务器</a>'
            : '<a class="btn btn-default btn-sm" href="/soft/index" title="在应用市场安装「SSH终端」插件后可保存并连接其他服务器">远程服务器</a>');
    }, { silent: true });
    tmLoadCmds();

    var cwd = '';
    try { cwd = new URLSearchParams(window.location.search).get('path') || ''; } catch (e) { }
    tmNew(cwd);
});

function tmNew(cwd) {
    if (TM.order.length >= 8) { layer.msg('最多同时打开 8 个终端', { icon: 0 }); return; }
    var id = 't' + (++TM.seq) + Date.now().toString(36).slice(-4);
    var box = $('<div class="tm-screen" id="tm_' + id + '"></div>').appendTo('#tmScreens');
    var term = new Terminal({
        cursorBlink: true, fontSize: TM.font, scrollback: 5000,
        theme: { background: '#1e2430', foreground: '#e5e7eb', cursor: '#e5e7eb', selection: 'rgba(148, 163, 184, .35)' }
    });
    term.open(box[0]);
    var t = { id: id, term: term, title: '终端 ' + TM.seq, dead: false, opened: false, cwd: cwd || '' };
    TM.terms[id] = t;
    TM.order.push(id);
    term.on('data', function (data) {
        if (t.dead) {
            if (data == '\r') tmReopen(t);
            return;
        }
        tmQueue(t, data);
    });
    term.on('resize', function (size) {
        if (!t.dead) TM.sock.emit('pm_term_resize', { tid: id, cols: size.cols, rows: size.rows });
    });
    term.on('title', function (title) {
        if (title) { t.title = String(title).slice(0, 30); tmRenderTabs(); }
    });
    tmActivate(id);
    tmOpenRemote(t);
}

// 合并短时间内的多次输入为一条消息发送:
// 长轮询会把多条消息打包成一个请求, 超过服务端单包上限时整包被丢弃(快速输入/粘贴会丢字)
function tmQueue(t, data) {
    t.buf = (t.buf || '') + data;
    if (t.flushTimer) return;
    t.flushTimer = setTimeout(function () {
        var chunk = t.buf;
        t.buf = '';
        t.flushTimer = null;
        if (chunk && !t.dead) TM.sock.emit('pm_term_input', { tid: t.id, data: chunk });
    }, 15);
}

function tmOpenRemote(t) {
    t.term.fit();
    t.opened = true;
    t.sockId = TM.sock.id;
    TM.sock.emit('pm_term_open', { tid: t.id, cols: t.term.cols, rows: t.term.rows, cwd: t.cwd });
}

function tmReopen(t) {
    t.dead = false;
    t.term.reset();
    tmOpenRemote(t);
    tmRenderTabs();
}

function tmActivate(id) {
    TM.active = id;
    $('#tmScreens .tm-screen').removeClass('on');
    $('#tm_' + id).addClass('on');
    tmRenderTabs();
    setTimeout(function () {
        var t = TM.terms[id];
        if (!t) return;
        t.term.fit();
        t.term.focus();
    }, 30);
}

function tmClose(id) {
    var t = TM.terms[id];
    if (!t) return;
    TM.sock.emit('pm_term_close', { tid: id });
    t.term.destroy();
    $('#tm_' + id).remove();
    delete TM.terms[id];
    var i = TM.order.indexOf(id);
    TM.order.splice(i, 1);
    if (!TM.order.length) { tmNew(); return; }
    if (TM.active == id) tmActivate(TM.order[Math.min(i, TM.order.length - 1)]);
    else tmRenderTabs();
}

function tmRenderTabs() {
    var html = '';
    for (var i = 0; i < TM.order.length; i++) {
        var t = TM.terms[TM.order[i]];
        html += '<span class="tm-tab' + (t.id == TM.active ? ' on' : '') + (t.dead ? ' dead' : '') + '" data-id="' + t.id + '" title="' + pmEsc(t.title) + '">' +
            '<i class="tm-dot"></i>' + pmEsc(t.title) + '<span class="tm-x" title="关闭">&times;</span></span>';
    }
    $('#tmTabs').html(html);
    $('#tmTabs .tm-tab').on('click', function (e) {
        var id = $(this).attr('data-id');
        if ($(e.target).hasClass('tm-x')) { tmClose(id); return; }
        tmActivate(id);
    });
}

function tmFit() {
    var t = TM.terms[TM.active];
    if (t) { t.term.fit(); t.term.focus(); }
}

// ================================ 常用命令 ================================

function tmLoadCmds() {
    pmPost('/terminal/commands', {}, function (r) {
        TM.cmds = r.data || [];
        var html = '';
        for (var i = 0; i < TM.cmds.length; i++) {
            var c = TM.cmds[i];
            html += '<div class="tm-cmd" data-i="' + i + '" title="' + pmEsc(c.cmd) + '"><div class="n"><span>' + pmEsc(c.name) + '</span>' +
                '<span class="ops"><a class="btlink" data-act="edit">编辑</a><a class="btlink" style="color:#ef4444" data-act="del">删除</a></span></div>' +
                '<div class="c">' + pmEsc(c.cmd.split('\n')[0]) + '</div></div>';
        }
        if (!html) html = '<div class="tm-empty">还没有常用命令<br><a class="btlink" onclick="tmCmdEdit(-1)">添加一条</a></div>';
        $('#tmCmds').html(html);
        $('#tmCmds .tm-cmd').on('click', function (e) {
            var i = parseInt($(this).attr('data-i')), act = $(e.target).attr('data-act');
            if (act == 'edit') { tmCmdEdit(i); return; }
            if (act == 'del') {
                layer.confirm('确定删除常用命令 ' + pmEsc(TM.cmds[i].name) + ' 吗?', { icon: 3, title: '删除' }, function (idx) {
                    layer.close(idx);
                    pmPost('/terminal/command_del', { index: i }, function (r) { pmResult(r, tmLoadCmds); });
                });
                return;
            }
            tmSendCmd(TM.cmds[i].cmd);
        });
    }, { silent: true });
}

function tmSendCmd(cmd) {
    var t = TM.terms[TM.active];
    if (!t || t.dead) { layer.msg('当前终端未连接', { icon: 0 }); return; }
    tmQueue(t, cmd.replace(/\r?\n/g, '\r') + '\r');
    t.term.focus();
}

function tmCmdEdit(i) {
    var c = i >= 0 ? TM.cmds[i] : { name: '', cmd: '' };
    layer.open({
        type: 1, title: i >= 0 ? '编辑常用命令' : '添加常用命令', area: '520px', closeBtn: 1, btn: ['保存', '取消'],
        content: '<div class="pm-form pd20"><div class="line"><span class="tname">名称</span><input class="bt-input-text" id="tcName" style="width:340px" value="' + pmEsc(c.name) + '" placeholder="如: 查看磁盘"></div>' +
            '<div class="line"><span class="tname" style="vertical-align:top">命令</span><textarea class="bt-input-text pm-code" id="tcCmd" style="width:340px;height:120px" placeholder="如: df -h">' + pmEsc(c.cmd) + '</textarea></div></div>',
        yes: function (idx) {
            pmPost('/terminal/command_save', { index: i >= 0 ? i : '', name: $.trim($('#tcName').val()), cmd: $('#tcCmd').val() }, function (r) {
                pmResult(r, function () { layer.close(idx); tmLoadCmds(); });
            });
        }
    });
}
