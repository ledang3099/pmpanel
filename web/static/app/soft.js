// ---------------------------------------------------------------------------------
// PM-Linux面板 软件管理 / 应用商店
// Licensed under the Apache License 2.0. See LICENSE and NOTICE.
// ---------------------------------------------------------------------------------
// 插件数据保存在 __softList 中, 页面按钮只携带下标(data-idx), 通过事件委托调用,
// 不再把插件名/标题/说明拼接进 onclick, 避免注入。

var __softList = [];
var __softPageSize = 24;

function softEsc(s) {
    if (typeof htmlAttrEscape === 'function') return htmlAttrEscape(s);
    return String(s == null ? '' : s).replace(/[&<>"'`]/g, function (c) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;', '`': '&#96;' }[c];
    });
}

// 插件说明里可能带有HTML标签, 只取纯文本(DOMParser 不会执行脚本或加载图片)
function softPlainText(html) {
    if (html == null) return '';
    try {
        var doc = new DOMParser().parseFromString('<body>' + html + '</body>', 'text/html');
        return (doc.body.textContent || '').trim();
    } catch (e) {
        return String(html).replace(/<[^>]*>/g, '');
    }
}

function softSafeUrl(url) {
    url = String(url || '').trim();
    return /^https?:\/\//i.test(url) ? url : '';
}

function softVersions(plugin) {
    if (typeof plugin.versions == 'string') return [plugin.versions];
    return plugin.versions || [];
}

function softIsEol(plugin, ver) {
    return (plugin.eol || []).indexOf(String(ver)) > -1;
}

//重置插件弹出框宽度
function resetPluginWinWidth(width){
    $("div[id^='layui-layer'][class*='layui-layer-page']").width(width);
}

//重置插件弹出框宽度
function resetPluginWinHeight(height){
    $("div[id^='layui-layer'][class*='layui-layer-page']").height(height);
    $(".bt-form .bt-w-main").height(height-42);
}

//软件管理窗口
function softMain(name, title, version) {
    var _title = String(title).replace('-' + version, '');
    var loadT = layer.msg("正在处理,请稍后...", { icon: 16, time: 0, shade: [0.3, '#000'] });
    $.get('/plugins/setting', { name: name }, function(rdata) {
        layer.close(loadT);
        layer.open({
            type: 1,
            area: '640px',
            title: softEsc(_title) + '【' + softEsc(version) + "】管理",
            closeBtn: 1,
            shift: 0,
            content: rdata
        });
        $(".bt-w-menu p").click(function() {
            $(this).addClass("bgw").siblings().removeClass("bgw");
        });
        $(".plugin_version").attr('version', version).hide();
    });
}

// ------------------------------- 应用商店列表 ------------------------------------

function softCurrentType() {
    var t = getCookie('soft_type');
    if (t == 'undefined' || t == 'null' || !t) t = '0';
    return t;
}

//取软件列表
function getSList(page) {
    var istype = softCurrentType();
    if (page === undefined || page === true || isNaN(parseInt(page))) {
        page = getCookie('p' + istype) || 1;
    }
    page = parseInt(page) || 1;
    setCookie('p' + istype, page);

    var params = { type: istype, p: page, row: __softPageSize };
    var search = $.trim($("#SearchValue").val() || '');
    if (search != '') params.search = search;

    if (!$('#softStore').length) return;
    $('#softStore').addClass('pm-loading');

    $.get('/plugins/list', params, function(rdata) {
        $('#softStore').removeClass('pm-loading');
        renderSoftTypes(rdata.type || [], istype);
        __softList = rdata.data || [];
        renderSoftCards(__softList, search);
        $("#softPage").html(rdata.list);
        for (var i = 0; i < __softList.length; i++) {
            if (__softList[i].setup && __softList[i].task == '1') {
                checkUpdate(i);
            }
        }
        loadImage();
    }, 'json').fail(function() {
        $('#softStore').removeClass('pm-loading');
        layer.msg('获取软件列表失败!', { icon: 2 });
    });
}

function renderSoftTypes(types, istype) {
    var html = '';
    for (var i = 0; i < types.length; i++) {
        var on = String(istype) == String(types[i].type) ? ' on' : '';
        html += '<button type="button" class="pm-store-tab' + on + '" data-type="' + softEsc(types[i].type) + '">' + softEsc(types[i].title) + '</button>';
    }
    $('#softTypes').html(html);
}

function softStatusBadge(plugin) {
    if (plugin.task == '-2') return '<span class="pm-badge pm-badge-busy">正在卸载</span>';
    if (plugin.task == '-1') return '<span class="pm-badge pm-badge-busy">正在安装</span>';
    if (plugin.task == '0') return '<span class="pm-badge pm-badge-wait">等待中</span>';
    if (!plugin.setup) return '<span class="pm-badge">未安装</span>';
    if (plugin.status) return '<span class="pm-badge pm-badge-run">运行中</span>';
    return '<span class="pm-badge pm-badge-stop">已停止</span>';
}

function renderSoftCards(list, search) {
    if (!list.length) {
        var empty = search ? '没有找到与"' + softEsc(search) + '"相关的软件' : '这里还没有软件';
        $('#softStore').html('<div class="pm-store-empty">' + empty + '</div>');
        return;
    }
    var html = '';
    for (var i = 0; i < list.length; i++) {
        var p = list[i];
        var vers = softVersions(p);
        var title = p.title;
        var verLabel = '';
        if (p.setup && p.setup_version) {
            verLabel = p.coexist ? '' : softEsc(p.setup_version);
            if (softIsEol(p, p.coexist ? vers[0] : p.setup_version)) {
                verLabel += ' <span class="pm-eol" title="该版本已停止维护, 不再提供安全更新">停止维护</span>';
            }
        } else if (vers.length > 1) {
            verLabel = vers.length + ' 个版本';
        } else if (vers.length == 1) {
            verLabel = softEsc(vers[0]);
            if (softIsEol(p, vers[0])) {
                verLabel += ' <span class="pm-eol" title="该版本已停止维护, 不再提供安全更新">停止维护</span>';
            }
        }

        var icon = '/plugins/file?name=' + encodeURIComponent(p.name) + '&f=' + encodeURIComponent(p.icon ? p.icon : 'ico.png');
        var busy = (p.task == '-1' || p.task == '-2' || p.task == '0');

        var actions = '';
        if (busy) {
            actions = '<button type="button" class="btn btn-default btn-xs" data-act="task">查看进度</button>';
        } else if (p.setup) {
            actions = '<button type="button" class="btn btn-success btn-xs" data-act="setting">设置</button>' +
                '<button type="button" class="btn btn-default btn-xs" data-act="uninstall">卸载</button>';
        } else {
            actions = '<button type="button" class="btn btn-success btn-xs" data-act="install">安装</button>';
        }

        var tools = '';
        if (p.setup && !busy) {
            tools += '<button type="button" class="pm-app-tool' + (p.display ? ' on' : '') + '" data-act="index" title="' + (p.display ? '已在首页显示' : '在首页显示') + '">' +
                '<svg viewBox="0 0 24 24"><path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/></svg></button>';
            if (p.path) {
                tools += '<button type="button" class="pm-app-tool" data-act="path" title="打开安装目录">' +
                    '<svg viewBox="0 0 24 24"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg></button>';
            }
        }

        html += '<div class="pm-app' + (p.setup ? ' installed' : '') + '" data-idx="' + i + '">' +
            '<div class="pm-app-head">' +
                '<div class="pm-app-icon"><img data-src="' + softEsc(icon) + '" src="/static/img/loading.gif" alt=""></div>' +
                '<div class="pm-app-meta">' +
                    '<div class="pm-app-title" title="' + softEsc(title) + '"' + (p.setup ? ' data-act="setting"' : '') + '>' + softEsc(title) + '</div>' +
                    '<div class="pm-app-sub">' + softStatusBadge(p) + '<span class="pm-app-ver">' + verLabel + '</span></div>' +
                '</div>' +
                '<div class="pm-app-tools">' + tools + '</div>' +
            '</div>' +
            '<p class="pm-app-desc" title="' + softEsc(softPlainText(p.ps)) + '">' + softEsc(softPlainText(p.ps)) + '</p>' +
            '<div class="pm-app-foot"><span class="pm-app-upd"></span><span class="pm-app-actions">' + actions + '</span></div>' +
        '</div>';
    }
    $('#softStore').html(html);
}

// 卡片按钮事件委托
$(document).on('click', '#softStore [data-act]', function(e) {
    e.stopPropagation();
    var idx = parseInt($(this).closest('.pm-app').attr('data-idx'));
    var p = __softList[idx];
    if (!p) return;
    var act = $(this).attr('data-act');
    var vers = softVersions(p);
    if (act == 'install') {
        addVersion(p.name, vers.join('|'), p.tip, this, p.title, p.install_pre_inspection, p.eol || [], p.recommend, p.release_versions);
    } else if (act == 'setting') {
        softMain(p.name, p.title, p.setup_version);
    } else if (act == 'uninstall') {
        uninstallVersion(p.name, p.title, p.setup_version, p.uninstall_pre_inspection);
    } else if (act == 'path') {
        openPath(p.path);
    } else if (act == 'task') {
        task();
    } else if (act == 'index') {
        var ver = p.coexist ? vers[0] : p.setup_version;
        setIndexDisplay(p.name, ver, !p.display, function(ok) {
            if (ok) { p.display = !p.display; renderSoftCards(__softList, $.trim($("#SearchValue").val() || '')); loadImage(); }
        });
    } else if (act == 'upgrade') {
        upgradeToNewVersion(p.name, p.setup_version, $(this).attr('data-new'));
    }
});

$(document).on('click', '#softTypes .pm-store-tab', function() {
    setCookie('soft_type', $(this).attr('data-type'));
    $(this).addClass('on').siblings().removeClass('on');
    getSList(1);
});

function checkUpdate(idx){
    var info = __softList[idx];
    if (!info || !info.upgrade) return;
    $.post("/plugins/run", {'name': info.name, 'version': info.setup_version, 'func': 'upgrade_check'}, function(rdata) {
        try {
            var data = $.parseJSON(rdata.data);
        } catch (e) {
            return;
        }
        if (data.status == 1 && __softList[idx] === info) {
            $('#softStore .pm-app[data-idx="' + idx + '"] .pm-app-upd').html(
                '<button type="button" class="pm-upd-btn" data-act="upgrade" data-new="' + softEsc(data.data) + '">可更新到 ' + softEsc(data.data) + '</button>');
        }
    }, 'json');
}

function runInstall(data){
    var loadT = layer.msg('正在添加到安装器...', { icon: 16, time: 0, shade: [0.3, '#000'] });
    $.post("/plugins/install", data, function(rdata) {
        layer.closeAll();
        layer.msg(rdata.msg, { icon: rdata.status ? 1 : 2 });
        getSList();
    },'json');
}

function upgradeToNewVersion(name, version, show_version){
    layer.confirm(msgTpl('您真的要更新【{1}-{2}】到{3}吗?', [softEsc(name), softEsc(version), softEsc(show_version)]), { icon: 3, closeBtn: 1 }, function() {
        runInstall({ name: name, version: version, upgrade: 'true' });
        flySlow('layui-layer-btn0');
    });
}

function installPreInspection(name, ver, callback){
    var loading = layer.msg('正在检查安装环境...', { icon: 16, time: 0, shade: [0.3, '#000'] });
    $.post("/plugins/run", {'name':name,'version':ver,'func':'install_pre_inspection'}, function(rdata) {
        layer.close(loading);
        if (rdata.status && rdata.data == 'ok'){
            callback();
        } else {
            layer.msg(softEsc(rdata.data || rdata.msg), { icon: 2 });
        }
    },'json');
}

// 安装弹窗: 版本列表(标出停止维护的版本), 默认选中最新的受支持版本
function addVersion(name, ver, type, obj, title, install_pre_inspection, eol, recommend, releases) {
    eol = eol || [];
    var vers = String(ver).split('|').filter(function(v){ return v !== ''; });
    var titlename = String(title).replace("-" + ver, "");
    // 默认选中: 插件指定的推荐版本, 否则为最新的受支持版本
    var defIdx = vers.indexOf(String(recommend || ''));
    if (defIdx < 0) {
        defIdx = vers.length - 1;
        for (var k = vers.length - 1; k >= 0; k--) {
            if (eol.indexOf(vers[k]) < 0 && vers[k] != 'rtmp') { defIdx = k; break; }
        }
    }

    var opts = '';
    for (var i = 0; i < vers.length; i++) {
        var isEol = eol.indexOf(vers[i]) > -1;
        var release = releases && releases[vers[i]];
        var label = release && release !== vers[i] ? vers[i] + ' · ' + release : vers[i];
        opts += '<label class="pm-ver-opt' + (isEol ? ' eol' : '') + '">' +
            '<input type="radio" name="pm_install_ver" value="' + softEsc(vers[i]) + '"' + (i == defIdx ? ' checked' : '') + '>' +
            '<span>' + softEsc(label) + (isEol ? '<em>停止维护</em>' : (vers[i] == recommend ? '<em class="rec">推荐</em>' : '')) + '</span></label>';
    }

    layer.open({
        type: 1,
        title: "安装【" + softEsc(titlename) + "】",
        area: ['460px', 'auto'],
        closeBtn: 1,
        shadeClose: true,
        btn: ['安装', '取消'],
        content: '<div class="pm-install-box">' +
            '<div class="pm-install-label">选择版本</div>' +
            '<div class="pm-ver-list">' + opts + '</div>' +
            '<div class="pm-install-tip" style="display:none">该版本已停止维护, 不再有安全更新, 仅建议在兼容旧程序时使用。</div>' +
            '</div>',
        success: function(layero) {
            var sync = function() {
                var cur = layero.find('input[name="pm_install_ver"]:checked').val();
                layero.find('.pm-install-tip').toggle(eol.indexOf(cur) > -1);
            };
            layero.find('input[name="pm_install_ver"]').on('change', sync);
            sync();
        },
        yes: function(index, layero) {
            var version = layero.find('input[name="pm_install_ver"]:checked').val();
            if (!version) { layer.msg('请选择版本', { icon: 2 }); return; }
            var request_args = { name: name, version: version, type: '0' };
            if (install_pre_inspection){
                installPreInspection(name, version, function(){
                    runInstall(request_args);
                    flySlow('layui-layer-btn0');
                });
                return;
            }
            runInstall(request_args);
            flySlow('layui-layer-btn0');
        }
    });
}

//卸载软件
function uninstallPreInspection(name, title, ver, callback){
    var loading = layer.msg('正在检查卸载环境...', { icon: 16, time: 0, shade: [0.3, '#000'] });
    $.post("/plugins/run", {'name':name,'version':ver,'func':'uninstall_pre_inspection'}, function(rdata) {
        layer.close(loading);
        if (rdata.status && rdata.data == 'ok'){
            if (typeof(callback) == 'function'){
                callback();
            }
        } else {
            layer.msg(softEsc(rdata.data || rdata.msg), { icon: 2 , time: 6666});
        }
    },'json');
}

function runUninstallVersion(name, title, version){
    var t = String(title).replace("-" + version, "");
    layer.confirm(msgTpl('您真的要卸载【{1}-{2}】吗?', [softEsc(t), softEsc(version)]), { icon: 3, closeBtn: 1 }, function() {
        var loadT = layer.msg('正在处理,请稍候...', { icon: 16, time: 0, shade: [0.3, '#000'] });
        $.post('/plugins/uninstall', { name: name, version: version }, function(rdata) {
            layer.close(loadT);
            getSList();
            layer.msg(rdata.msg, { icon: rdata.status ? 1 : 2 });
        },'json');
    });
}

function uninstallVersion(name, title, version, uninstall_pre_inspection) {
    if (uninstall_pre_inspection) {
        uninstallPreInspection(name, title, version, function(){
            runUninstallVersion(name, title, version);
        });
    } else {
        runUninstallVersion(name, title, version);
    }
}

// 首页显示开关
function setIndexDisplay(name, version, show, callback) {
    $.post("/plugins/set_index", { name: name, status: show ? '1' : '0', version: version }, function(rdata) {
        layer.msg(rdata.msg, { icon: rdata.status ? 1 : 2 });
        if (typeof callback == 'function') callback(rdata.status);
    },'json');
}

// 兼容旧调用
function toIndexDisplay(name, version, coexist) {
    var id = coexist == "true" ? "#index_" + name + String(version).replace(/\./g, "") : "#index_" + name;
    var show = !$(id).prop("checked");
    setIndexDisplay(name, version, show);
}

// ------------------------------- 首页软件 ----------------------------------------

function indexListHtml(callback){
    $("#indexsoft").html('');
    var index_soft = '';
    for (var i = 0; i < 12; i++) {
        index_soft += '<div class="col-sm-3 col-md-3 col-lg-3 no-bg"></div>';
    }
    $("#indexsoft").html(index_soft);

    $.get('/plugins/index_list', function(rdata) {
        var list = rdata.data || [];
        window.__indexSoftList = list;
        $("#indexsoft").html('');
        var con = '';
        for (var i = 0; i < list.length; i++) {
            var plugin = list[i];
            var state = plugin.status ?
                '<span style="color:#20a53a" class="glyphicon glyphicon-play"></span>' :
                '<span style="color:red" class="glyphicon glyphicon-pause"></span>';

            var name = plugin.title + ' ' + plugin.setup_version + '  ';
            var data_id = plugin.name + '-' + plugin.setup_version;
            if (plugin.coexist){
                name = plugin.title + '  ';
                data_id = plugin.name + '-' + plugin.versions;
            }

            con += '<div class="col-sm-3 col-md-3 col-lg-3" data-id="' + softEsc(data_id) + '">\
                <span class="spanmove"></span>\
                <div class="pm-index-soft" data-i="' + i + '">\
                <div class="image"><img src="/plugins/file?name=' + encodeURIComponent(plugin.name) + '&f=ico.png" style="max-width:48px;"></div>\
                <div class="sname">' + softEsc(name) + state + '</div>\
                </div>\
            </div>';
        }

        $("#indexsoft").html(con);
        var softboxlen = $("#indexsoft > div").length;
        var softboxsum = 12;
        var softboxcon = '';
        if (softboxlen <= softboxsum) {
            for (var i = 0; i < softboxsum - softboxlen; i++) {
                softboxcon += '<div class="col-sm-3 col-md-3 col-lg-3 no-bg" data-id=""></div>';
            }
            $("#indexsoft").append(softboxcon);
        }

        if (typeof callback == 'function'){
            callback();
        }
    },'json');
}

$(document).on('click', '#indexsoft .pm-index-soft', function() {
    var p = (window.__indexSoftList || [])[parseInt($(this).attr('data-i'))];
    if (p) softMain(p.name, p.title, p.setup_version);
});

//首页软件列表
function indexSoft() {
    indexListHtml(function(){
        $("#indexsoft").dragsort({
            dragSelector: ".spanmove",
            dragBetween: true,
            dragEnd: saveOrder,
            placeHolderTemplate: "<div class='col-sm-3 col-md-3 col-lg-3 dashed-border'></div>"
        });
    });

    function saveOrder() {
        var data = $("#indexsoft > div").map(function() { return $(this).attr("data-id"); }).get();
        var tmp = [];
        for (var i = 0; i < data.length; i++) {
            if (data[i]) tmp.push($.trim(data[i]));
        }
        $.post("/plugins/index_sort", { ssort: tmp.join("|") }, function(rdata) {
            if (!rdata.status){
                layer.msg('设置失败:' + rdata.msg, { icon: 2 });
                indexListHtml();
            }
        },'json');
    }
}

// ------------------------------- 导入第三方插件 ----------------------------------

function importPluginOpen(){
    $("#update_zip").off("change").on("change", function () {
        var files = $("#update_zip")[0].files;
        if (files.length == 0) {
            return;
        }
        importPlugin(files[0]);
        $("#update_zip").val('');
    });
    $("#update_zip").click();
}

function importPlugin(file){
    var formData = new FormData();
    formData.append("plugin_zip", file);
    $.ajax({
        url: "/plugins/update_zip",
        type: "POST",
        data: formData,
        processData: false,
        dataType: 'json',
        contentType: false,
        success: function (data) {
            if (data.status === false) {
                layer.msg(data.msg, { icon: 2 });
                return;
            }
            window.__importPlugin = { name: data.name, tmp_path: data.tmp_path };
            var home = softSafeUrl(data.home);
            layer.open({
                type: 1,
                area: "500px",
                title: "安装第三方插件包",
                closeBtn: 1,
                shift: 5,
                shadeClose: false,
                content: '<div class="pm-install-box">\
                    <div class="pm-import-info">\
                        <p><b>名称：</b>' + softEsc(data.title) + '</p>\
                        <p><b>版本：</b>' + softEsc(data.versions) + '</p>\
                        <p><b>描述：</b>' + softEsc(softPlainText(data.ps)) + '</p>\
                        <p><b>大小：</b>' + toSize(data.size) + '</p>\
                        <p><b>作者：</b>' + softEsc(data.author) + '</p>\
                        <p><b>来源：</b>' + (home ? '<a class="btlink" href="' + softEsc(home) + '" target="_blank" rel="noopener noreferrer">' + softEsc(home) + '</a>' : '-') + '</p>\
                    </div>\
                    <ul class="help-info-text c7">\
                        <li style="color:red;">此为第三方开发的插件，无法验证其可靠性! 插件拥有服务器 root 权限，请只安装可信来源的插件。</li>\
                        <li>安装过程可能需要几分钟时间，请耐心等候!</li>\
                        <li>如果已存在此插件，将被替换!</li>\
                    </ul>\
                    <div class="bt-form-submit-btn"><button type="button" class="btn btn-sm btn-default mr5" onclick="layer.closeAll()">取消</button><button type="button" class="btn btn-sm btn-success" onclick="importPluginInstall()">确定安装</button></div>\
                </div>'
            });
        },
        error: function () {
            layer.msg('上传失败!', { icon: 2 });
        }
    });
}

function importPluginInstall() {
    var info = window.__importPlugin || {};
    layer.msg('正在安装,这可能需要几分钟时间...', { icon: 16, time: 0, shade: [0.3, '#000'] });
    $.post('/plugins/input_zip', { plugin_name: info.name, tmp_path: info.tmp_path }, function (rdata) {
        layer.closeAll();
        if (rdata.status) {
            getSList();
        }
        setTimeout(function () { layer.msg(rdata.msg, { icon: rdata.status ? 1 : 2 }) }, 1000);
    },'json');
}

$(function() {
    if (window.document.location.pathname.indexOf('/soft/') === 0) {
        // 有安装/卸载任务时自动刷新状态
        setInterval(function() {
            var busy = false;
            for (var i = 0; i < __softList.length; i++) {
                if (__softList[i].task == '-1' || __softList[i].task == '-2' || __softList[i].task == '0') { busy = true; break; }
            }
            if (busy && !$('.layui-layer-page').length) getSList();
        }, 8000);
    }
});
