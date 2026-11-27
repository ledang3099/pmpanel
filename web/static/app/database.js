// PM-Linux面板 数据库: MySQL / PgSQL / MongoDB / Redis

var DB = { info: null, engine: 'mysql', plugin: '', page: 1, search: '', list: [], rd: { db: 0, cursor: 0, pattern: '*', keys: [] } };
var DB_ENGINE_TITLE = { mysql: 'MySQL', pgsql: 'PostgreSQL', mongodb: 'MongoDB', redis: 'Redis' };
var DB_MYSQL = ['mysql', 'mariadb', 'mysql-community'];

$(function () {
    pmPost('/database/info', {}, function (r) {
        DB.info = r.data || {};
        pmTabs('#dbPanel', function (name) {
            DB.engine = name;
            DB.page = 1;
            DB.search = '';
            dbOpen(name);
        });
    }, { silent: true });
});

function dbIsMysql() { return DB_MYSQL.indexOf(DB.plugin) > -1; }

// 调用数据库插件
function dbCall(func, args, cb, opts) {
    pmPost('/database/call', { name: DB.plugin, func: func, args: JSON.stringify(args || {}) }, function (r) {
        if (!r.status) { pmResult(r); return; }
        var d = r.data;
        if (d && typeof d == 'object' && d.status === false) { layer.msg(d.msg || '操作失败', { icon: 2, time: 4000 }); return; }
        if (d && typeof d == 'object' && (d.status === -1)) { layer.msg(d.msg || '操作失败', { icon: 2, time: 4000 }); return; }
        cb && cb(d);
    }, opts);
}

function dbRandom(n) {
    var chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789', out = '';
    var buf = new Uint32Array(n || 16);
    window.crypto.getRandomValues(buf);
    for (var i = 0; i < buf.length; i++) out += chars[buf[i] % chars.length];
    return out;
}

function dbCopy(text) {
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(function () { layer.msg('已复制', { icon: 1 }); });
        return;
    }
    var t = $('<textarea style="position:fixed;left:-9999px">').val(text).appendTo('body');
    t[0].select();
    try { document.execCommand('copy'); layer.msg('已复制', { icon: 1 }); } catch (e) { layer.msg('复制失败', { icon: 2 }); }
    t.remove();
}

// ================================ 入口 ================================

function dbOpen(engine) {
    var items = (DB.info[engine] || []);
    var installed = items.filter(function (x) { return x.installed; });
    if (!installed.length) {
        var names = items.map(function (x) { return x.title; }).join(' / ') || DB_ENGINE_TITLE[engine];
        $('#dbBody').html('<div class="db-empty-box"><div style="font-size:15px;color:#374151">尚未安装 ' + pmEsc(names) + '</div>' +
            '<div class="pm-muted" style="margin-top:6px">安装后即可在这里管理数据库、用户、备份与导入</div>' +
            '<a class="btn btn-success btn-sm" href="/soft/index">前往应用市场安装</a></div>');
        return;
    }
    var keep = installed.filter(function (x) { return x.name == DB.plugin; });
    DB.plugin = (keep.length ? keep[0] : installed[0]).name;
    if (engine == 'redis') { redisOpen(installed); return; }
    dbRenderShell(installed);
    dbLoad(1);
}

function dbEngineBar(installed) {
    var cur = installed.filter(function (x) { return x.name == DB.plugin; })[0];
    var sel = '';
    if (installed.length > 1) {
        sel = '<select class="bt-input-text" id="dbPlugin" style="width:150px">';
        for (var i = 0; i < installed.length; i++) {
            sel += '<option value="' + pmEsc(installed[i].name) + '"' + (installed[i].name == DB.plugin ? ' selected' : '') + '>' + pmEsc(installed[i].title) + '</option>';
        }
        sel += '</select>';
    }
    return '<div class="db-engine">' + sel + '<span>' + pmEsc(cur.title) + ' ' + pmEsc(cur.version) + '</span>' +
        (cur.status ? '<span class="pm-tag green">运行中</span>' : '<span class="pm-tag red">已停止</span>') +
        '<a class="btlink" href="/soft/index" title="在应用市场中设置">设置</a></div>';
}

function dbRenderShell(installed) {
    var cur = installed.filter(function (x) { return x.name == DB.plugin; })[0];
    var mysql = dbIsMysql();
    var html = (cur.status ? '' : '<div class="pm-alert warn">' + pmEsc(cur.title) + ' 未运行, 请先在应用市场中启动服务。</div>') +
        '<div class="pm-toolbar">' +
        '<button class="btn btn-success btn-sm" id="dbAdd">添加数据库</button>' +
        '<button class="btn btn-default btn-sm" id="dbRoot">' + (DB.plugin == 'postgresql' ? 'postgres 密码' : 'root 密码') + '</button>' +
        (mysql ? '<button class="btn btn-default btn-sm" id="dbPma">phpMyAdmin</button>' : '') +
        '<button class="btn btn-default btn-sm" id="dbSyncGet" title="把服务器中已存在、面板中没有记录的数据库加入面板">从服务器获取</button>' +
        (DB.plugin != 'postgresql' ? '<button class="btn btn-default btn-sm" id="dbSyncAll" title="把面板中的数据库与用户同步到服务器">同步所有</button>' : '') +
        '<button class="btn btn-default btn-sm" id="dbImportBtn">导入文件</button>' +
        '<span class="db-batch" id="dbBatch"><span class="pm-muted">已选 <b id="dbSelN">0</b> 项</span>' +
        '<button class="btn btn-default btn-sm" id="dbBatchBackup">批量备份</button>' +
        (DB.plugin != 'postgresql' ? '<button class="btn btn-default btn-sm" id="dbBatchSync">同步选中</button>' : '') +
        '<button class="btn btn-danger btn-sm" id="dbBatchDel">批量删除</button></span>' +
        dbEngineBar(installed) + '</div>' +
        '<div class="pm-toolbar" style="justify-content:flex-end;margin-top:-4px">' +
        '<input class="bt-input-text" id="dbSearch" style="width:220px" placeholder="搜索数据库名"><button class="btn btn-default btn-sm" id="dbSearchBtn">搜索</button></div>' +
        '<div class="divtable"><table class="table table-hover pm-table"><thead><tr>' +
        '<th width="30"><input type="checkbox" id="dbAll"></th><th>数据库名</th><th>用户名</th><th>密码</th><th>备份</th><th>访问权限</th><th>备注</th><th class="text-right">操作</th>' +
        '</tr></thead><tbody id="dbList"></tbody></table></div><div id="dbPager"></div>';
    $('#dbBody').html(html);
    $('#dbPlugin').on('change', function () { DB.plugin = $(this).val(); dbOpen(DB.engine); });
    $('#dbAdd').on('click', dbAddDialog);
    $('#dbRoot').on('click', dbRootDialog);
    $('#dbPma').on('click', function () { dbPhpMyAdmin(); });
    $('#dbSyncGet').on('click', function () {
        dbCall('sync_get_databases', {}, function (d) { layer.msg((d && d.msg) || '获取完成', { icon: 1 }); dbLoad(1); }, { loading: '正在从服务器获取数据库...' });
    });
    $('#dbSyncAll').on('click', function () { dbSync('0', []); });
    $('#dbImportBtn').on('click', function () { dbImportDialog(''); });
    $('#dbSearchBtn').on('click', function () { DB.search = $.trim($('#dbSearch').val()); dbLoad(1); });
    $('#dbSearch').on('keydown', function (e) { if (e.keyCode == 13) $('#dbSearchBtn').trigger('click'); });
    $('#dbAll').on('change', function () { $('#dbList .db-sel').prop('checked', this.checked); dbSelChange(); });
    $('#dbBatchDel').on('click', function () { dbDelete(dbSelected()); });
    $('#dbBatchBackup').on('click', function () { dbBatchBackup(dbSelected()); });
    $('#dbBatchSync').on('click', function () { dbSync('1', dbSelected().map(function (x) { return x.id; })); });
}

function dbSelected() {
    var ids = [];
    $('#dbList .db-sel:checked').each(function () { ids.push(parseInt($(this).val())); });
    return DB.list.filter(function (x) { return ids.indexOf(x.id) > -1; });
}

function dbSelChange() {
    var n = $('#dbList .db-sel:checked').length;
    $('#dbSelN').text(n);
    $('#dbBatch').css('display', n ? 'inline-flex' : 'none');
}

function dbLoad(page) {
    DB.page = page;
    dbCall('get_db_list', { page: page, page_size: 15, search: DB.search }, function (d) {
        DB.list = d.data || [];
        var rows = '';
        for (var i = 0; i < DB.list.length; i++) {
            var x = DB.list[i], id = x.id;
            var access = x.accept == '%' ? '所有人' : (x.accept == '127.0.0.1' || x.accept == 'localhost' ? '本地服务器' : x.accept);
            rows += '<tr><td><input type="checkbox" class="db-sel" value="' + id + '"></td>' +
                '<td><b>' + pmEsc(x.name) + '</b></td><td>' + pmEsc(x.username) + '</td>' +
                '<td class="db-pass"><span class="pw" data-i="' + i + '">**********</span><span class="eye" data-i="' + i + '" title="显示">显示</span><span class="copy" data-i="' + i + '" title="复制">复制</span></td>' +
                '<td><a class="btlink" data-op="backup" data-i="' + i + '">' + (x.is_backup ? '有备份' : '<span style="color:#f59e0b">无备份</span>') + '</a> | ' +
                '<a class="btlink" data-op="import" data-i="' + i + '">导入</a></td>' +
                '<td>' + pmEsc(access || '-') + '</td>' +
                '<td><span class="db-ps" data-op="ps" data-i="' + i + '" title="点击修改">' + (pmEsc(x.ps) || '<span class="pm-muted">点击添加</span>') + '</span></td>' +
                '<td class="text-right ops">' +
                (dbIsMysql() ? '<a class="btlink" data-op="pma" data-i="' + i + '">管理</a><a class="btlink" data-op="tools" data-i="' + i + '">工具</a>' : '') +
                '<a class="btlink" data-op="access" data-i="' + i + '">权限</a><a class="btlink" data-op="pwd" data-i="' + i + '">改密</a>' +
                '<a class="btlink" style="color:#ef4444" data-op="del" data-i="' + i + '">删除</a></td></tr>';
        }
        if (!rows) rows = '<tr><td colspan="8" class="pm-empty">' + (DB.search ? '没有找到匹配的数据库' : '还没有数据库, 点击"添加数据库"创建') + '</td></tr>';
        $('#dbList').html(rows);
        $('#dbAll').prop('checked', false);
        dbSelChange();
        $('#dbList .db-sel').on('change', dbSelChange);
        $('#dbList .eye').on('click', function () {
            var i = $(this).attr('data-i'), pw = $('#dbList .pw[data-i="' + i + '"]');
            var shown = pw.attr('data-shown') == '1';
            pw.text(shown ? '**********' : DB.list[i].password).attr('data-shown', shown ? '0' : '1');
            $(this).text(shown ? '显示' : '隐藏');
        });
        $('#dbList .copy').on('click', function () { dbCopy(DB.list[$(this).attr('data-i')].password); });
        $('#dbList [data-op]').on('click', function () {
            var x = DB.list[$(this).attr('data-i')], op = $(this).attr('data-op');
            if (op == 'backup') dbBackupDialog(x);
            if (op == 'import') dbImportDialog(x.name);
            if (op == 'ps') dbPsEdit(x);
            if (op == 'pma') dbPhpMyAdmin(x);
            if (op == 'tools') dbToolsDialog(x);
            if (op == 'access') dbAccessDialog(x);
            if (op == 'pwd') dbPwdDialog(x);
            if (op == 'del') dbDelete([x]);
        });
        pmPager('dbPager', d.count || 0, page, 15, dbLoad);
    }, { silent: true });
}

// ================================ 添加 / 删除 ================================

function dbAccessField(prefix, value) {
    value = value || '127.0.0.1';
    var mode = value == '%' ? '%' : (value == '127.0.0.1' || value == 'localhost' ? '127.0.0.1' : 'ip');
    return '<select class="bt-input-text" id="' + prefix + 'Mode" style="width:130px">' +
        '<option value="127.0.0.1"' + (mode == '127.0.0.1' ? ' selected' : '') + '>本地服务器</option>' +
        '<option value="%"' + (mode == '%' ? ' selected' : '') + '>所有人(不安全)</option>' +
        '<option value="ip"' + (mode == 'ip' ? ' selected' : '') + '>指定 IP</option></select> ' +
        '<input class="bt-input-text" id="' + prefix + 'Ip" style="width:150px;' + (mode == 'ip' ? '' : 'display:none') + '" placeholder="多个 IP 用逗号分隔" value="' + (mode == 'ip' ? pmEsc(value) : '') + '">';
}

function dbAccessValue(prefix) {
    var m = $('#' + prefix + 'Mode').val();
    return m == 'ip' ? $.trim($('#' + prefix + 'Ip').val()).replace(/\s+/g, '') : m;
}

function dbAccessBind(prefix) {
    $('#' + prefix + 'Mode').on('change', function () { $('#' + prefix + 'Ip').toggle($(this).val() == 'ip'); });
}

function dbAddDialog() {
    var mysql = dbIsMysql(), pg = DB.plugin == 'postgresql';
    var charset = mysql ? '<div class="line"><span class="tname">字符集</span><select class="bt-input-text" id="daCode" style="width:130px">' +
        '<option value="utf8mb4">utf8mb4</option><option value="utf8">utf8</option><option value="gbk">gbk</option><option value="big5">big5</option></select></div>' : '';
    var html = '<div class="pm-form pd20">' +
        '<div class="line"><span class="tname">数据库名</span><input class="bt-input-text" id="daName" placeholder="字母、数字、下划线"></div>' +
        '<div class="line"><span class="tname">用户名</span><input class="bt-input-text" id="daUser" placeholder="默认与数据库名相同"></div>' +
        '<div class="line"><span class="tname">密码</span><input class="bt-input-text" id="daPass" style="width:200px" value="' + dbRandom(16) + '"> <a class="btlink" id="daGen">随机</a></div>' +
        charset +
        (DB.plugin != 'mongodb' ? '<div class="line"><span class="tname">访问权限</span>' + dbAccessField('daAcc') + '</div>' : '') +
        '<div class="line"><span class="tname">备注</span><input class="bt-input-text" id="daPs" placeholder="可选"></div></div>';
    layer.open({
        type: 1, title: '添加数据库', area: '500px', closeBtn: 1, btn: ['提交', '取消'], content: html,
        success: function () {
            var userEdited = false;
            $('#daUser').on('input', function () { userEdited = true; });
            $('#daName').on('input', function () { if (!userEdited) $('#daUser').val($(this).val().substring(0, 32)); });
            $('#daGen').on('click', function () { $('#daPass').val(dbRandom(16)); });
            dbAccessBind('daAcc');
        },
        yes: function (idx) {
            var name = $.trim($('#daName').val()), user = $.trim($('#daUser').val()) || name;
            var access = DB.plugin == 'mongodb' ? '127.0.0.1' : dbAccessValue('daAcc');
            var args = { name: name, db_user: user, password: $.trim($('#daPass').val()), ps: $.trim($('#daPs').val()) || name };
            // 插件按 address 创建用户和授权(dataAccess 只做存在性检查)
            if (DB.plugin != 'mongodb') { args.dataAccess = access; args.address = access; }
            if (mysql) args.codeing = $('#daCode').val();
            dbCall('add_db', args, function (d) { pmResult(d, function () { layer.close(idx); dbLoad(1); }); });
        }
    });
}

function dbDelete(items) {
    if (!items.length) return;
    var names = items.map(function (x) { return x.name; });
    var a = Math.floor(Math.random() * 9) + 1, b = Math.floor(Math.random() * 9) + 1;
    var html = '<div class="pd20"><div class="pm-alert danger">删除后数据库中的所有数据将被清除且无法恢复, 建议先备份。</div>' +
        '<div style="margin-bottom:10px">将删除: <b>' + pmEsc(names.join(', ')) + '</b></div>' +
        '<div>请计算 <b>' + a + ' + ' + b + '</b> = <input class="bt-input-text" id="ddSum" style="width:80px"></div></div>';
    layer.open({
        type: 1, title: '删除数据库', area: '460px', closeBtn: 1, btn: ['确认删除', '取消'], content: html,
        yes: function (idx) {
            if (parseInt($('#ddSum').val()) !== a + b) { layer.msg('计算结果不正确', { icon: 2 }); return; }
            layer.close(idx);
            var i = 0, okN = 0;
            (function next() {
                if (i >= items.length) { layer.msg('已删除 ' + okN + ' 个数据库', { icon: 1 }); dbLoad(1); return; }
                var x = items[i++];
                pmPost('/database/call', { name: DB.plugin, func: 'del_db', args: JSON.stringify({ id: x.id, name: x.name }) }, function (r) {
                    if (r.status && r.data && r.data.status) okN++;
                    else layer.msg(x.name + ': ' + ((r.data && r.data.msg) || r.msg), { icon: 2 });
                    next();
                }, { loading: '正在删除 ' + x.name + '...' });
            })();
        }
    });
}

function dbSync(type, ids) {
    var tip = type == '0' ? '确定把面板中的所有数据库同步到服务器吗? 服务器中不存在的数据库和用户会被创建。' : '确定同步选中的 ' + ids.length + ' 个数据库吗?';
    layer.confirm(tip, { icon: 3, title: '同步到服务器' }, function (idx) {
        layer.close(idx);
        dbCall('sync_to_databases', { type: type, ids: JSON.stringify(ids) }, function (d) { pmResult(d, function () { dbLoad(DB.page); }); }, { loading: '正在同步...' });
    });
}

// ================================ 密码 / 权限 / 备注 ================================

function dbRootDialog() {
    var pg = DB.plugin == 'postgresql', who = pg ? 'postgres' : 'root';
    pmPost('/database/root_pwd', { name: DB.plugin }, function (r) {
        var pw = r.status ? r.data.password : '';
        var html = '<div class="pm-form pd20"><div class="line"><span class="tname">' + who + ' 密码</span>' +
            '<input class="bt-input-text" id="drPass" style="width:220px" value="' + pmEsc(pw) + '"> <a class="btlink" id="drGen">随机</a> <a class="btlink" id="drCopy">复制</a></div>' +
            '<div class="pm-alert info" style="margin-top:6px">修改后会同时更新数据库服务中的密码和面板记录。</div></div>';
        layer.open({
            type: 1, title: '管理员(' + who + ')密码', area: '480px', closeBtn: 1, btn: ['修改', '关闭'], content: html,
            success: function () {
                $('#drGen').on('click', function () { $('#drPass').val(dbRandom(16)); });
                $('#drCopy').on('click', function () { dbCopy($('#drPass').val()); });
            },
            yes: function (idx) {
                var np = $.trim($('#drPass').val());
                if (np == pw) { layer.msg('密码未修改', { icon: 0 }); return; }
                dbCall(pg ? 'set_postgres_pwd' : 'set_root_pwd', { password: np }, function (d) { pmResult(d, function () { layer.close(idx); }); });
            }
        });
    }, { silent: true });
}

function dbPwdDialog(x) {
    var html = '<div class="pm-form pd20"><div class="line"><span class="tname">用户名</span><b>' + pmEsc(x.username) + '</b></div>' +
        '<div class="line"><span class="tname">新密码</span><input class="bt-input-text" id="dpPass" style="width:220px" value="' + dbRandom(16) + '"> <a class="btlink" id="dpGen">随机</a></div></div>';
    layer.open({
        type: 1, title: '修改数据库密码', area: '460px', closeBtn: 1, btn: ['修改', '取消'], content: html,
        success: function () { $('#dpGen').on('click', function () { $('#dpPass').val(dbRandom(16)); }); },
        yes: function (idx) {
            dbCall('set_user_pwd', { id: x.id, name: x.username, password: $.trim($('#dpPass').val()) }, function (d) {
                pmResult(d, function () { layer.close(idx); dbLoad(DB.page); });
            });
        }
    });
}

function dbAccessDialog(x) {
    dbCall('get_db_access', { username: x.username }, function (d) {
        // 插件返回的是逗号分隔的主机列表, 可能带有多余的逗号
        var hosts = String((d && d.msg) || x.accept || '127.0.0.1').split(',').map($.trim).filter(function (h) { return h; });
        var cur = hosts.filter(function (h) { return h != 'localhost' && h != '127.0.0.1'; }).join(',') || '127.0.0.1';
        if (hosts.indexOf('%') > -1) cur = '%';
        var html = '<div class="pm-form pd20"><div class="line"><span class="tname">用户名</span><b>' + pmEsc(x.username) + '</b></div>' +
            '<div class="line"><span class="tname">访问权限</span>' + dbAccessField('dxAcc', cur) + '</div>' +
            '<div class="pm-muted">选择"所有人"时请确保使用强密码, 并在防火墙中只对可信 IP 开放数据库端口。</div></div>';
        layer.open({
            type: 1, title: '设置访问权限', area: '500px', closeBtn: 1, btn: ['保存', '取消'], content: html,
            success: function () { dbAccessBind('dxAcc'); },
            yes: function (idx) {
                var v = dbAccessValue('dxAcc');
                if (!v) { layer.msg('请输入 IP', { icon: 2 }); return; }
                dbCall('set_db_access', { username: x.username, access: v }, function (r) { pmResult(r, function () { layer.close(idx); dbLoad(DB.page); }); });
            }
        });
    }, { silent: true });
}

function dbPsEdit(x) {
    layer.prompt({ title: '修改备注: ' + x.name, value: x.ps || '', maxlength: 200 }, function (val, idx) {
        dbCall('set_db_ps', { id: x.id, name: x.name, ps: $.trim(val) }, function (d) { pmResult(d, function () { layer.close(idx); dbLoad(DB.page); }); });
    });
}

function dbPhpMyAdmin(x) {
    pmPost('/plugins/run', { name: 'phpmyadmin', func: 'plugins_db_support' }, function (r) {
        var d = null;
        try { d = JSON.parse(r.data).data; } catch (e) { }
        if (!d || d.installed != 'ok') { layer.msg('phpMyAdmin 未安装, 请先在应用市场中安装', { icon: 2 }); return; }
        if (d.status != 'start') { layer.msg('phpMyAdmin 未启动', { icon: 2 }); return; }
        if (d.cfg && d.cfg.choose && d.cfg.choose != 'mysql') { layer.msg('phpMyAdmin 当前连接的是 ' + pmEsc(d.cfg.choose) + ', 请在 phpMyAdmin 设置中切换', { icon: 2 }); return; }
        if (x) dbCopy(x.password);
        window.open(d.home_page, '_blank', 'noopener');
        if (x) layer.msg('已复制 ' + pmEsc(x.username) + ' 的密码, 请在 phpMyAdmin 中登录', { icon: 1, time: 3000 });
    }, { silent: true });
}

// ================================ 备份 / 导入 ================================

function dbBackupDialog(x) {
    var html = '<div class="pd15"><div class="pm-toolbar"><b>' + pmEsc(x.name) + '</b>' +
        '<div class="pm-right"><button class="btn btn-success btn-sm" id="dbkNow">立即备份</button></div></div>' +
        '<div class="divtable" style="max-height:330px;overflow:auto"><table class="table table-hover pm-table"><thead><tr><th>文件名</th><th>大小</th><th>备份时间</th><th class="text-right">操作</th></tr></thead>' +
        '<tbody id="dbkList"></tbody></table></div><div class="pm-muted" style="margin-top:6px">备份目录: ' + pmEsc(DB.info.backup_dir) + '/database</div></div>';
    layer.open({
        type: 1, title: '数据库备份', area: ['720px', '500px'], closeBtn: 1, content: html,
        success: function () {
            dbBackupList(x);
            $('#dbkNow').on('click', function () {
                dbCall(DB.plugin == 'postgresql' ? 'pg_back' : 'set_db_backup', { name: x.name }, function () {
                    layer.msg('备份完成', { icon: 1 });
                    dbBackupList(x);
                }, { loading: '正在备份, 数据量大时需要较长时间...' });
            });
        },
        end: function () { dbLoad(DB.page); }
    });
}

function dbBackupList(x) {
    dbCall('get_db_backup_list', { name: x.name }, function (d) {
        var list = (d && d.data) || [], rows = '';
        for (var i = 0; i < list.length; i++) {
            var b = list[i];
            rows += '<tr><td class="pm-code">' + pmEsc(b.name) + '</td><td>' + pmEsc(b.size) + '</td><td>' + pmEsc(b.time) + '</td>' +
                '<td class="text-right ops"><a class="btlink" data-act="restore" data-i="' + i + '">恢复</a>' +
                '<a class="btlink" href="/files/download?filename=' + encodeURIComponent(b.file) + '">下载</a>' +
                '<a class="btlink" style="color:#ef4444" data-act="del" data-i="' + i + '">删除</a></td></tr>';
        }
        if (!rows) rows = '<tr><td colspan="4" class="pm-empty">暂无备份</td></tr>';
        $('#dbkList').html(rows);
        $('#dbkList [data-act]').on('click', function () {
            var b = list[$(this).attr('data-i')], act = $(this).attr('data-act');
            if (act == 'restore') {
                layer.confirm('恢复会用备份覆盖数据库 <b>' + pmEsc(x.name) + '</b> 中的现有数据, 确定继续吗?', { icon: 0, title: '恢复备份' }, function (idx) {
                    layer.close(idx);
                    dbCall('import_db_backup', { file: b.name, name: x.name }, function (r) { pmResult(r.status === undefined ? { status: true, msg: '恢复完成' } : r); }, { loading: '正在恢复...' });
                });
            }
            if (act == 'del') {
                layer.confirm('确定删除备份 ' + pmEsc(b.name) + ' 吗?', { icon: 3, title: '删除备份' }, function (idx) {
                    layer.close(idx);
                    dbCall('delete_db_backup', { filename: b.name, path: '' }, function (r) { pmResult(r, function () { dbBackupList(x); }); });
                });
            }
        });
    }, { silent: true });
}

function dbImportDialog(dbname) {
    pmPost('/database/import_dir', {}, function (dr) {
        var dir = dr.data;
        var options = '';
        for (var i = 0; i < DB.list.length; i++) {
            options += '<option value="' + pmEsc(DB.list[i].name) + '"' + (DB.list[i].name == dbname ? ' selected' : '') + '>' + pmEsc(DB.list[i].name) + '</option>';
        }
        var html = '<div class="pd15"><div class="pm-toolbar"><span>导入到</span><select class="bt-input-text" id="diDb" style="width:180px">' + options + '</select>' +
            '<div class="pm-right"><button class="btn btn-success btn-sm" id="diUpload">从本地上传</button><button class="btn btn-default btn-sm" id="diRefresh">刷新</button></div></div>' +
            '<div class="divtable" style="max-height:300px;overflow:auto"><table class="table table-hover pm-table"><thead><tr><th>文件名</th><th>大小</th><th>时间</th><th class="text-right">操作</th></tr></thead>' +
            '<tbody id="diList"></tbody></table></div>' +
            '<div class="pm-muted" style="margin-top:6px">支持 .sql / .sql.gz / .zip / .tar.gz, 文件名只能包含字母、数字、下划线、点和连字符。导入目录: ' + pmEsc(dir) + '</div></div>';
        layer.open({
            type: 1, title: '导入数据库', area: ['720px', '480px'], closeBtn: 1, content: html,
            success: function () {
                dbImportList(dir);
                $('#diRefresh').on('click', function () { dbImportList(dir); });
                $('#diUpload').on('click', function () { dbUpload(dir, function () { dbImportList(dir); }); });
            }
        });
    }, { silent: true });
}

function dbImportList(dir) {
    dbCall('get_db_backup_import_list', {}, function (d) {
        var list = (d && d.data) || [], rows = '';
        if (!$.isArray(list)) list = list.list || [];
        for (var i = 0; i < list.length; i++) {
            var f = list[i];
            rows += '<tr><td class="pm-code">' + pmEsc(f.name) + '</td><td>' + pmEsc(f.size) + '</td><td>' + pmEsc(f.time) + '</td>' +
                '<td class="text-right ops"><a class="btlink" data-act="import" data-i="' + i + '">导入</a>' +
                '<a class="btlink" style="color:#ef4444" data-act="del" data-i="' + i + '">删除</a></td></tr>';
        }
        if (!rows) rows = '<tr><td colspan="4" class="pm-empty">导入目录中还没有文件, 请先上传</td></tr>';
        $('#diList').html(rows);
        $('#diList [data-act]').on('click', function () {
            var f = list[$(this).attr('data-i')], act = $(this).attr('data-act'), db = $('#diDb').val();
            if (act == 'import') {
                if (!db) { layer.msg('请先选择要导入的数据库', { icon: 2 }); return; }
                layer.confirm('确定把 ' + pmEsc(f.name) + ' 导入到数据库 <b>' + pmEsc(db) + '</b> 吗? 同名数据表会被覆盖。', { icon: 0, title: '导入' }, function (idx) {
                    layer.close(idx);
                    dbCall('import_db_external', { file: f.name, name: db }, function (r) { pmResult(r.status === undefined ? { status: true, msg: '导入完成' } : r); }, { loading: '正在导入...' });
                });
            }
            if (act == 'del') {
                layer.confirm('确定删除 ' + pmEsc(f.name) + ' 吗?', { icon: 3, title: '删除文件' }, function (idx) {
                    layer.close(idx);
                    dbCall('delete_db_backup', { filename: f.name, path: dir }, function (r) { pmResult(r, function () { dbImportList(dir); }); });
                });
            }
        });
    }, { silent: true });
}

// 复用面板的上传组件(upload.js)
function dbUpload(dir, done) {
    var box = layer.open({
        type: 1, closeBtn: 1, title: '上传导入文件', area: ['520px', '320px'], shadeClose: false,
        content: '<div class="fileUploadDiv"><input type="hidden" id="input-val" value="' + pmEsc(dir) + '" />' +
            '<input type="file" id="file_input" multiple="true" autocomplete="off" accept=".sql,.gz,.zip,.tgz" />' +
            '<button type="button" id="opt" autocomplete="off">添加文件</button><button type="button" id="up" autocomplete="off">开始上传</button>' +
            '<span id="totalProgress" style="position:absolute;top:7px;right:147px;"></span>' +
            '<span style="float:right;margin-top:9px;"><font>文件编码:</font><select id="fileCodeing"><option value="byte">二进制</option></select></span>' +
            '<button type="button" id="filesClose" autocomplete="off">关闭</button><ul id="up_box"></ul></div>',
        success: function () { $('#filesClose').on('click', function () { layer.close(box); }); }
    });
    uploadStart(function () { layer.close(box); done && done(); });
}

function dbBatchBackup(items) {
    if (!items.length) return;
    var i = 0;
    (function next() {
        if (i >= items.length) { layer.msg('已备份 ' + items.length + ' 个数据库', { icon: 1 }); dbLoad(DB.page); return; }
        var x = items[i++];
        dbCall(DB.plugin == 'postgresql' ? 'pg_back' : 'set_db_backup', { name: x.name }, next, { loading: '正在备份 ' + x.name + ' (' + i + '/' + items.length + ')...' });
    })();
}

// ================================ 工具(MySQL) ================================

function dbToolsDialog(x) {
    dbCall('get_db_info', { name: x.name }, function (d) {
        var tables = (d && d.tables) || [], rows = '';
        for (var i = 0; i < tables.length; i++) {
            var t = tables[i];
            rows += '<tr><td><input type="checkbox" class="dt-sel" value="' + pmEsc(t.table_name) + '"></td><td class="pm-code">' + pmEsc(t.table_name) + '</td>' +
                '<td>' + pmEsc(t.type) + '</td><td>' + pmEsc(t.collation) + '</td><td>' + pmEsc(t.rows_count) + '</td><td>' + pmEsc(t.data_size) + '</td></tr>';
        }
        if (!rows) rows = '<tr><td colspan="6" class="pm-empty">该数据库还没有数据表</td></tr>';
        var html = '<div class="pd15"><div class="pm-toolbar"><span>数据库 <b>' + pmEsc(x.name) + '</b>, 大小 ' + pmEsc(d.data_size || '-') + '</span>' +
            '<div class="pm-right"><button class="btn btn-default btn-sm" data-t="repair_table">修复</button><button class="btn btn-default btn-sm" data-t="opt_table">优化</button>' +
            '<button class="btn btn-default btn-sm" data-t="InnoDB">转为 InnoDB</button><button class="btn btn-default btn-sm" data-t="MyISAM">转为 MyISAM</button></div></div>' +
            '<div class="divtable" style="max-height:360px;overflow:auto"><table class="table table-hover pm-table"><thead><tr><th width="30"><input type="checkbox" id="dtAll"></th>' +
            '<th>表名</th><th>引擎</th><th>字符集</th><th>行数</th><th>大小</th></tr></thead><tbody>' + rows + '</tbody></table></div></div>';
        layer.open({
            type: 1, title: '数据库工具', area: ['780px', '540px'], closeBtn: 1, content: html,
            success: function (el) {
                el.find('#dtAll').on('change', function () { el.find('.dt-sel').prop('checked', this.checked); });
                el.find('[data-t]').on('click', function () {
                    var t = $(this).attr('data-t'), sel = [];
                    el.find('.dt-sel:checked').each(function () { sel.push($(this).val()); });
                    if (!sel.length) { layer.msg('请先选择数据表', { icon: 0 }); return; }
                    var func = t == 'InnoDB' || t == 'MyISAM' ? 'alter_table' : t;
                    var args = { db_name: x.name, tables: JSON.stringify(sel) };
                    if (func == 'alter_table') args.table_type = t;
                    dbCall(func, args, function (r) { pmResult(r); });
                });
            }
        });
    }, { loading: '正在读取数据表...' });
}

// ================================ Redis ================================

function redisOpen(installed) {
    var bar = dbEngineBar(installed);
    $('#dbBody').html('<div class="pm-toolbar"><div class="pm-stats" id="rdStats" style="flex:1;margin:0"></div></div>' +
        '<div class="pm-toolbar"><button class="btn btn-success btn-sm" id="rdAdd">添加键</button>' +
        '<button class="btn btn-default btn-sm" id="rdDelSel">删除选中</button><button class="btn btn-danger btn-sm" id="rdFlush">清空当前库</button>' +
        '<div class="pm-right"><input class="bt-input-text" id="rdPattern" style="width:220px" placeholder="键名匹配, 如 user:*"><button class="btn btn-default btn-sm" id="rdSearch">搜索</button>' +
        '<button class="btn btn-default btn-sm" id="rdRefresh">刷新</button>' + bar + '</div></div>' +
        '<div class="rd-layout"><div class="rd-dbs" id="rdDbs"></div><div><div class="divtable"><table class="table table-hover pm-table"><thead><tr>' +
        '<th width="30"><input type="checkbox" id="rdAll"></th><th>键名</th><th>类型</th><th>过期时间</th><th class="text-right">操作</th></tr></thead><tbody id="rdList"></tbody></table></div>' +
        '<div style="text-align:center;margin-top:10px"><button class="btn btn-default btn-sm" id="rdMore" style="display:none">加载更多</button></div></div></div>');
    $('#dbPlugin').on('change', function () { DB.plugin = $(this).val(); dbOpen('redis'); });
    $('#rdAdd').on('click', function () { redisEdit(null); });
    $('#rdSearch').on('click', function () { DB.rd.pattern = $.trim($('#rdPattern').val()) || '*'; redisScan(true); });
    $('#rdPattern').on('keydown', function (e) { if (e.keyCode == 13) $('#rdSearch').trigger('click'); });
    $('#rdRefresh').on('click', function () { redisInfo(); redisScan(true); });
    $('#rdMore').on('click', function () { redisScan(false); });
    $('#rdAll').on('change', function () { $('#rdList .rd-sel').prop('checked', this.checked); });
    $('#rdDelSel').on('click', function () {
        var keys = [];
        $('#rdList .rd-sel:checked').each(function () { keys.push(DB.rd.keys[$(this).val()].key); });
        if (!keys.length) { layer.msg('请先选择键', { icon: 0 }); return; }
        redisDelete(keys);
    });
    $('#rdFlush').on('click', function () {
        layer.confirm('确定清空 db' + DB.rd.db + ' 中的所有键吗? 此操作不可恢复。', { icon: 0, title: '清空数据库' }, function (idx) {
            layer.close(idx);
            pmPost('/database/redis_flush', { name: DB.plugin, db: DB.rd.db }, function (r) { pmResult(r, function () { redisInfo(); redisScan(true); }); });
        });
    });
    redisInfo();
    redisScan(true);
}

function redisInfo() {
    pmPost('/database/redis_info', { name: DB.plugin }, function (r) {
        if (!r.status) {
            $('#rdStats').html('<div class="pm-alert danger" style="margin:0">' + pmEsc(r.msg) + '</div>');
            return;
        }
        var d = r.data;
        $('#rdStats').html(
            '<div class="pm-stat"><div class="pm-stat-label">版本</div><div class="pm-stat-value" style="font-size:18px">' + pmEsc(d.version) + '</div><div class="pm-stat-sub">端口 ' + d.port + (d.has_password ? ' · 已设密码' : ' · <span style="color:#ef4444">未设密码</span>') + '</div></div>' +
            '<div class="pm-stat"><div class="pm-stat-label">内存使用</div><div class="pm-stat-value" style="font-size:18px">' + pmEsc(d.used_memory) + '</div><div class="pm-stat-sub">峰值 ' + pmEsc(d.peak_memory) + '</div></div>' +
            '<div class="pm-stat"><div class="pm-stat-label">键总数</div><div class="pm-stat-value">' + d.total_keys + '</div><div class="pm-stat-sub">命中率 ' + d.hit_rate + '%</div></div>' +
            '<div class="pm-stat"><div class="pm-stat-label">连接数</div><div class="pm-stat-value">' + d.clients + '</div><div class="pm-stat-sub">' + d.ops + ' 次/秒</div></div>');
        var dbs = '';
        for (var i = 0; i < d.dbs.length; i++) {
            dbs += '<div data-db="' + d.dbs[i].db + '" class="' + (d.dbs[i].db == DB.rd.db ? 'on' : '') + '"><span>db' + d.dbs[i].db + '</span><span class="pm-muted">' + d.dbs[i].keys + '</span></div>';
        }
        $('#rdDbs').html(dbs);
        $('#rdDbs [data-db]').on('click', function () {
            DB.rd.db = parseInt($(this).attr('data-db'));
            $('#rdDbs [data-db]').removeClass('on');
            $(this).addClass('on');
            redisScan(true);
        });
    }, { silent: true });
}

function redisTtl(t) {
    if (t < 0) return '<span class="pm-muted">永久</span>';
    if (t < 60) return t + ' 秒';
    if (t < 3600) return Math.floor(t / 60) + ' 分钟';
    if (t < 86400) return Math.floor(t / 3600) + ' 小时';
    return Math.floor(t / 86400) + ' 天';
}

function redisScan(reset) {
    if (reset) { DB.rd.cursor = 0; DB.rd.keys = []; }
    pmPost('/database/redis_scan', { name: DB.plugin, db: DB.rd.db, pattern: DB.rd.pattern, cursor: DB.rd.cursor, count: 100 }, function (r) {
        if (!r.status) { $('#rdList').html('<tr><td colspan="5" class="pm-empty">' + pmEsc(r.msg) + '</td></tr>'); return; }
        DB.rd.cursor = r.data.cursor;
        DB.rd.keys = DB.rd.keys.concat(r.data.list);
        var rows = '';
        for (var i = 0; i < DB.rd.keys.length; i++) {
            var k = DB.rd.keys[i];
            rows += '<tr><td><input type="checkbox" class="rd-sel" value="' + i + '"></td><td class="pm-code" style="max-width:420px;word-break:break-all">' + pmEsc(k.key) + '</td>' +
                '<td><span class="pm-tag blue">' + pmEsc(k.type) + '</span></td><td>' + redisTtl(k.ttl) + '</td>' +
                '<td class="text-right ops"><a class="btlink" data-act="view" data-i="' + i + '">查看</a><a class="btlink" data-act="ttl" data-i="' + i + '">过期时间</a>' +
                '<a class="btlink" style="color:#ef4444" data-act="del" data-i="' + i + '">删除</a></td></tr>';
        }
        if (!rows) rows = '<tr><td colspan="5" class="pm-empty">' + (DB.rd.pattern != '*' ? '没有匹配的键' : '当前库没有数据') + '</td></tr>';
        $('#rdList').html(rows);
        $('#rdAll').prop('checked', false);
        $('#rdMore').toggle(DB.rd.cursor != 0);
        $('#rdList [data-act]').on('click', function () {
            var k = DB.rd.keys[$(this).attr('data-i')], act = $(this).attr('data-act');
            if (act == 'view') redisView(k.key);
            if (act == 'ttl') redisSetTtl(k);
            if (act == 'del') redisDelete([k.key]);
        });
    }, { silent: true });
}

function redisView(key) {
    pmPost('/database/redis_get', { name: DB.plugin, db: DB.rd.db, key: key }, function (r) {
        if (!r.status) { pmResult(r); return; }
        var d = r.data, body = '';
        if (d.type == 'string') {
            body = '<textarea class="bt-input-text rd-val" id="rvVal">' + pmEsc(d.value) + '</textarea>';
        } else {
            var head = { hash: '<th>字段</th><th>值</th>', zset: '<th>成员</th><th>分值</th>', list: '<th>#</th><th>值</th>', set: '<th>#</th><th>成员</th>' }[d.type] || '<th>值</th>';
            var rows = '';
            var vals = $.isArray(d.value) ? d.value : [d.value];
            for (var i = 0; i < vals.length; i++) {
                var v = vals[i];
                if (d.type == 'hash') rows += '<tr><td class="pm-code">' + pmEsc(v.field) + '</td><td class="pm-code" style="word-break:break-all">' + pmEsc(v.value) + '</td></tr>';
                else if (d.type == 'zset') rows += '<tr><td class="pm-code" style="word-break:break-all">' + pmEsc(v.member) + '</td><td>' + pmEsc(v.score) + '</td></tr>';
                else rows += '<tr><td>' + i + '</td><td class="pm-code" style="word-break:break-all">' + pmEsc(v) + '</td></tr>';
            }
            body = '<div class="divtable" style="max-height:330px;overflow:auto"><table class="table pm-table"><thead><tr>' + head + '</tr></thead><tbody>' + rows + '</tbody></table></div>';
        }
        var html = '<div class="pd15"><div class="pm-toolbar"><span class="pm-tag blue">' + pmEsc(d.type) + '</span><span class="pm-code" style="word-break:break-all">' + pmEsc(d.key) + '</span>' +
            '<div class="pm-right pm-muted">长度 ' + d.size + ' · 过期 ' + redisTtl(d.ttl) + '</div></div>' + body +
            (d.truncated ? '<div class="pm-alert warn" style="margin-top:8px">内容较大, 仅显示前一部分。</div>' : '') + '</div>';
        layer.open({
            type: 1, title: '查看键', area: ['720px', '520px'], closeBtn: 1, content: html,
            btn: d.type == 'string' && !d.truncated ? ['保存', '关闭'] : (d.type == 'string' ? ['关闭'] : ['添加成员', '关闭']),
            yes: function (idx) {
                if (d.type == 'string') {
                    if (d.truncated) { layer.close(idx); return; }
                    pmPost('/database/redis_set', { name: DB.plugin, db: DB.rd.db, key: d.key, value: $('#rvVal').val(), ttl: d.ttl > 0 ? d.ttl : -1, type: 'string' }, function (res) {
                        pmResult(res, function () { layer.close(idx); redisScan(true); });
                    });
                } else {
                    layer.close(idx);
                    redisEdit({ key: d.key, type: d.type });
                }
            }
        });
    }, { silent: true });
}

function redisEdit(k) {
    var type = k ? k.type : 'string';
    var html = '<div class="pm-form pd20">' +
        '<div class="line"><span class="tname">类型</span><select class="bt-input-text" id="reType" style="width:130px"' + (k ? ' disabled' : '') + '>' +
        ['string', 'hash', 'list', 'set', 'zset'].map(function (t) { return '<option value="' + t + '"' + (t == type ? ' selected' : '') + '>' + t + '</option>'; }).join('') + '</select></div>' +
        '<div class="line"><span class="tname">键名</span><input class="bt-input-text" id="reKey" style="width:380px" value="' + (k ? pmEsc(k.key) : '') + '"' + (k ? ' readonly' : '') + '></div>' +
        '<div class="line" id="reFieldLine" style="display:none"><span class="tname" id="reFieldName">字段</span><input class="bt-input-text" id="reField" style="width:380px"></div>' +
        '<div class="line"><span class="tname" style="vertical-align:top">值</span><textarea class="bt-input-text pm-code" id="reVal" style="width:380px;height:120px"></textarea></div>' +
        '<div class="line"><span class="tname">过期时间</span><input class="bt-input-text" id="reTtl" style="width:120px" value="-1"> 秒<span class="pm-help">-1 表示永久</span></div></div>';
    layer.open({
        type: 1, title: k ? '添加成员' : '添加键', area: '560px', closeBtn: 1, btn: ['保存', '取消'], content: html,
        success: function () {
            var upd = function () {
                var t = $('#reType').val();
                $('#reFieldLine').toggle(t == 'hash' || t == 'zset');
                $('#reFieldName').text(t == 'zset' ? '分值' : '字段');
            };
            $('#reType').on('change', upd);
            upd();
        },
        yes: function (idx) {
            var key = $.trim($('#reKey').val());
            if (!key) { layer.msg('请输入键名', { icon: 2 }); return; }
            pmPost('/database/redis_set', { name: DB.plugin, db: DB.rd.db, key: key, value: $('#reVal').val(), ttl: $.trim($('#reTtl').val()) || '-1', type: $('#reType').val(), field: $.trim($('#reField').val()) }, function (r) {
                pmResult(r, function () { layer.close(idx); redisInfo(); redisScan(true); });
            });
        }
    });
}

function redisSetTtl(k) {
    layer.prompt({ title: '过期时间(秒), -1 为永久', value: k.ttl > 0 ? String(k.ttl) : '-1' }, function (val, idx) {
        pmPost('/database/redis_ttl', { name: DB.plugin, db: DB.rd.db, key: k.key, ttl: $.trim(val) }, function (r) { pmResult(r, function () { layer.close(idx); redisScan(true); }); });
    });
}

function redisDelete(keys) {
    layer.confirm('确定删除 ' + (keys.length == 1 ? pmEsc(keys[0]) : keys.length + ' 个键') + ' 吗?', { icon: 3, title: '删除键' }, function (idx) {
        layer.close(idx);
        pmPost('/database/redis_del', { name: DB.plugin, db: DB.rd.db, keys: JSON.stringify(keys) }, function (r) { pmResult(r, function () { redisInfo(); redisScan(true); }); });
    });
}
