// PM-Linux面板 全局文件编辑器
//
// - 非模态窗口: 不遮挡左侧菜单与页面, 编辑时可以继续操作其他功能
// - 多标签: 同时打开多个文件, 未保存的标签带圆点标记
// - 跨栏目保留: 切换到其他栏目(页面跳转)后自动恢复打开的文件和未保存的修改
//   (状态保存在当前浏览器标签页的 sessionStorage 中, 关闭浏览器标签即清除)
// - 最小化到右下角, 可最大化、拖动、调整大小

var PmEditor = (function () {
    var KEY = 'pmEditorState';
    var ENCODINGS = ['utf-8', 'GBK', 'GB2312', 'BIG5'];
    var tabs = [];          // {path, doc, encoding, saved, dirty, callback}
    var active = -1;
    var cm = null;
    var win = null, dock = null;
    var state = { open: false, minimized: false, max: false, rect: null };
    var autoTimer = null;
    var saveTimer = null;

    function store() {
        clearTimeout(saveTimer);
        saveTimer = setTimeout(persist, 300);
    }

    function persist() {
        try {
            var files = tabs.map(function (t) {
                var c = t.doc.getCursor();
                return {
                    path: t.path, encoding: t.encoding, dirty: t.dirty,
                    content: t.dirty ? t.doc.getValue() : null,
                    cursor: { line: c.line, ch: c.ch }
                };
            });
            if (!files.length) { sessionStorage.removeItem(KEY); return; }
            sessionStorage.setItem(KEY, JSON.stringify({
                files: files, active: active, open: state.open, minimized: state.minimized, max: state.max, rect: state.rect
            }));
        } catch (e) { /* 存储空间不足时忽略 */ }
    }

    function modeOf(path) {
        var ext = (path.split('/').pop().split('.').pop() || '').toLowerCase();
        var name = path.split('/').pop().toLowerCase();
        if (name == 'nginx.conf' || /\.conf$/.test(name) && path.indexOf('nginx') > -1) return 'text/x-nginx-conf';
        return {
            html: 'htmlmixed', htm: 'htmlmixed', vue: 'htmlmixed', tpl: 'application/x-httpd-php',
            js: 'text/javascript', mjs: 'text/javascript', ts: 'text/typescript', json: 'application/json',
            css: 'text/css', less: 'text/x-less', scss: 'text/x-scss',
            php: 'application/x-httpd-php', xml: 'application/xml', svg: 'application/xml',
            sql: 'text/x-sql', conf: 'text/x-nginx-conf'
        }[ext] || 'text/plain';
    }

    function esc(s) { return typeof pmEsc == 'function' ? pmEsc(s) : $('<div>').text(s).html(); }
    function base(p) { return p.split('/').pop(); }

    // ------------------------------- 窗口 ---------------------------------------

    function build() {
        if (win) return;
        win = $('<div id="pmEditor" class="pm-editor" style="display:none">' +
            '<div class="pe-head"><span class="pe-title">文件编辑器</span><span class="pe-path"></span>' +
            '<span class="pe-btns"><a data-act="min" title="最小化">&#8212;</a><a data-act="max" title="最大化/还原">&#9633;</a><a data-act="close" title="关闭">&#10005;</a></span></div>' +
            '<div class="pe-tabs"></div>' +
            '<div class="pe-bar"><button class="btn btn-success btn-xs" data-act="save">保存</button>' +
            '<button class="btn btn-default btn-xs" data-act="saveall">全部保存</button>' +
            '<button class="btn btn-default btn-xs" data-act="reload">刷新</button>' +
            '<label class="pe-auto"><input type="checkbox" data-act="auto"> 自动刷新</label>' +
            '<select class="pe-enc"></select>' +
            '<span class="pe-tip">Ctrl+S 保存 · Ctrl+F 搜索 · Ctrl+H 替换</span></div>' +
            '<div class="pe-body"><textarea></textarea></div></div>').appendTo('body');
        dock = $('<div id="pmEditorDock" class="pm-editor-dock" style="display:none"></div>').appendTo('body');
        win.find('.pe-enc').html(ENCODINGS.map(function (e) { return '<option value="' + e + '">' + e + '</option>'; }).join(''));

        cm = CodeMirror.fromTextArea(win.find('textarea')[0], {
            lineNumbers: true, matchBrackets: true, autoMatchParens: true, matchtags: true, lineWrapping: false,
            extraKeys: {
                'Ctrl-S': function () { save(active); }, 'Cmd-S': function () { save(active); },
                'Ctrl-F': 'findPersistent', 'Cmd-F': 'findPersistent', 'Ctrl-H': 'replaceAll'
            }
        });

        win.on('click', '[data-act]', function (e) {
            var act = $(this).attr('data-act');
            if (act == 'min') minimize();
            if (act == 'max') toggleMax();
            if (act == 'close') closeAll();
            if (act == 'save') save(active);
            if (act == 'saveall') saveAll();
            if (act == 'reload') reload(active);
        });
        win.find('[data-act=auto]').on('change', function () {
            clearInterval(autoTimer);
            if (this.checked) autoTimer = setInterval(function () { if (active > -1 && !tabs[active].dirty) reload(active, true); }, 5000);
        });
        win.find('.pe-enc').on('change', function () {
            if (active > -1) { tabs[active].encoding = $(this).val(); tabs[active].encodingChanged = true; markDirty(active, true); }
        });
        win.find('.pe-tabs').on('click', '.pe-tab', function (e) {
            var i = parseInt($(this).attr('data-i'));
            if ($(e.target).hasClass('pe-x')) { closeTab(i); return; }
            activate(i);
        }).on('mousedown', '.pe-tab', function (e) {
            if (e.which == 2) { e.preventDefault(); closeTab(parseInt($(this).attr('data-i'))); }
        });
        dock.on('click', function () { restore(); });

        dragAndResize();
        $(window).on('beforeunload', persist);
        $(window).on('resize', function () { if (state.max) applyRect(); });
    }

    function contentRect() {
        // 默认占据右侧内容区, 不遮挡左侧菜单
        var side = $('.sidebar-scroll').is(':visible') ? ($('.sidebar-scroll').outerWidth() || 200) : 0;
        if ($(window).width() < 900) side = 0;
        return { left: side + 16, top: 16, width: $(window).width() - side - 32, height: $(window).height() - 32 };
    }

    function applyRect() {
        var r = state.max || !state.rect ? contentRect() : state.rect;
        r.width = Math.min(r.width, $(window).width() - 8);
        r.height = Math.min(r.height, $(window).height() - 8);
        r.left = Math.max(0, Math.min(r.left, $(window).width() - 120));
        r.top = Math.max(0, Math.min(r.top, $(window).height() - 60));
        win.css({ left: r.left, top: r.top, width: r.width, height: r.height });
        refreshSize();
    }

    function refreshSize() {
        if (!cm) return;
        var h = win.height() - win.find('.pe-head').outerHeight() - win.find('.pe-tabs').outerHeight() - win.find('.pe-bar').outerHeight();
        cm.setSize('100%', Math.max(120, h));
        cm.refresh();
    }

    function dragAndResize() {
        var head = win.find('.pe-head')[0];
        head.addEventListener('mousedown', function (e) {
            if ($(e.target).closest('.pe-btns').length || state.max) return;
            var sx = e.clientX, sy = e.clientY, o = win.offset();
            var ox = o.left - $(window).scrollLeft(), oy = o.top - $(window).scrollTop();
            var move = function (ev) {
                win.css({ left: Math.max(0, ox + ev.clientX - sx), top: Math.max(0, oy + ev.clientY - sy) });
            };
            var up = function () {
                document.removeEventListener('mousemove', move);
                document.removeEventListener('mouseup', up);
                saveRect();
            };
            document.addEventListener('mousemove', move);
            document.addEventListener('mouseup', up);
            e.preventDefault();
        });
        head.addEventListener('dblclick', function (e) { if (!$(e.target).closest('.pe-btns').length) toggleMax(); });
        if (window.ResizeObserver) {
            new ResizeObserver(function () { refreshSize(); }).observe(win[0]);
        }
        win[0].addEventListener('mouseup', function () { if (!state.max) saveRect(); });
    }

    function saveRect() {
        var o = win[0].getBoundingClientRect();
        state.rect = { left: o.left, top: o.top, width: o.width, height: o.height };
        store();
    }

    function show() {
        build();
        state.open = true;
        state.minimized = false;
        dock.hide();
        win.show();
        applyRect();
        win.toggleClass('pe-max', !!state.max);
        if (active > -1) cm.focus();
        store();
    }

    function minimize() {
        state.minimized = true;
        win.hide();
        renderDock();
        store();
    }

    function restore() { show(); }

    function toggleMax() {
        state.max = !state.max;
        win.toggleClass('pe-max', state.max);
        applyRect();
        store();
    }

    function renderDock() {
        var dirty = tabs.filter(function (t) { return t.dirty; }).length;
        if (!tabs.length) { dock.hide(); return; }
        dock.html('<span class="pe-dock-ico">&#9998;</span> 编辑器 · ' + tabs.length + ' 个文件' +
            (dirty ? ' <span class="pe-dock-dirty">' + dirty + ' 个未保存</span>' : '')).show();
    }

    // ------------------------------- 标签 ---------------------------------------

    function renderTabs() {
        var html = '';
        for (var i = 0; i < tabs.length; i++) {
            html += '<span class="pe-tab' + (i == active ? ' on' : '') + '" data-i="' + i + '" title="' + esc(tabs[i].path) + '">' +
                (tabs[i].dirty ? '<i class="pe-dot"></i>' : '') + esc(base(tabs[i].path)) + '<span class="pe-x" title="关闭">&times;</span></span>';
        }
        win.find('.pe-tabs').html(html);
        if (active > -1) {
            win.find('.pe-path').text(tabs[active].path);
            win.find('.pe-enc').val(tabs[active].encoding || 'utf-8');
        } else {
            win.find('.pe-path').text('');
        }
        if (state.minimized) renderDock();
    }

    function activate(i) {
        if (i < 0 || i >= tabs.length) return;
        active = i;
        cm.swapDoc(tabs[i].doc);
        renderTabs();
        cm.focus();
        store();
    }

    function markDirty(i, dirty) {
        if (!tabs[i] || tabs[i].dirty == dirty) return;
        tabs[i].dirty = dirty;
        renderTabs();
        store();
    }

    function addTab(path, content, encoding, dirty, savedContent, callback, cursor) {
        var doc = CodeMirror.Doc(content, modeOf(path));
        var tab = { path: path, doc: doc, encoding: encoding || 'utf-8', saved: savedContent, dirty: !!dirty, callback: callback };
        doc.on('change', function () {
            var idx = tabs.indexOf(tab);
            if (idx > -1) markDirty(idx, doc.getValue() !== tab.saved || tab.encodingChanged);
            store();
        });
        if (cursor) doc.setCursor(cursor);
        tabs.push(tab);
        return tabs.length - 1;
    }

    function fetchBody(path, cb) {
        $.post('/files/get_body', { path: path }, function (r) {
            if (!r || r.status === false) { layer.msg((r && r.msg) || '读取失败', { icon: 2 }); cb(null); return; }
            cb(r.data);
        }, 'json').fail(function () { layer.msg('读取文件失败', { icon: 2 }); cb(null); });
    }

    function open(path, callback) {
        build();
        for (var i = 0; i < tabs.length; i++) {
            if (tabs[i].path == path) {
                if (callback) tabs[i].callback = callback;
                show();
                activate(i);
                return;
            }
        }
        var loading = layer.msg('正在读取文件...', { icon: 16, time: 0 });
        fetchBody(path, function (d) {
            layer.close(loading);
            if (!d) return;
            var idx = addTab(path, d.data, d.encoding, false, d.data, callback);
            show();
            activate(idx);
        });
    }

    function save(i, done) {
        var t = tabs[i];
        if (!t) return;
        var content = t.doc.getValue();
        var loading = layer.msg('正在保存...', { icon: 16, time: 0 });
        $.post('/files/save_body', { data: content, path: t.path, encoding: t.encoding }, function (r) {
            layer.close(loading);
            if (r && r.status) {
                t.saved = content;
                t.encodingChanged = false;
                markDirty(tabs.indexOf(t), false);
                if (!done) layer.msg(r.msg || '已保存', { icon: 1, time: 1200 });
                if (typeof t.callback == 'function') { try { t.callback(1, t.path); } catch (e) { } }
            } else {
                layer.msg((r && r.msg) || '保存失败', { icon: 2, time: 4000 });
            }
            done && done(r && r.status);
        }, 'json').fail(function () {
            layer.close(loading);
            layer.msg('保存失败: 网络错误', { icon: 2 });
            done && done(false);
        });
    }

    function saveAll() {
        var list = tabs.filter(function (t) { return t.dirty; });
        if (!list.length) { layer.msg('没有需要保存的文件', { icon: 0, time: 1200 }); return; }
        var n = 0, okN = 0;
        list.forEach(function (t) {
            save(tabs.indexOf(t), function (good) {
                n++; if (good) okN++;
                if (n == list.length) layer.msg('已保存 ' + okN + ' / ' + list.length + ' 个文件', { icon: okN == list.length ? 1 : 2 });
            });
        });
    }

    function reload(i, quiet) {
        var t = tabs[i];
        if (!t) return;
        var go = function () {
            fetchBody(t.path, function (d) {
                if (!d) return;
                var c = t.doc.getCursor(), info = cm.getScrollInfo();
                t.saved = d.data;
                t.doc.setValue(d.data);
                t.encoding = d.encoding || t.encoding;
                markDirty(i, false);
                if (quiet) cm.scrollTo(null, cm.getScrollInfo().height);
                else { t.doc.setCursor(c); cm.scrollTo(info.left, info.top); }
                renderTabs();
            });
        };
        if (t.dirty && !quiet) {
            layer.confirm('文件有未保存的修改, 刷新将丢弃这些修改, 确定吗?', { icon: 3, title: '刷新' }, function (idx) { layer.close(idx); go(); });
        } else go();
    }

    function closeTab(i) {
        var t = tabs[i];
        if (!t) return;
        var go = function () {
            tabs.splice(i, 1);
            if (!tabs.length) {
                active = -1;
                cm.swapDoc(CodeMirror.Doc(''));
                hideAll();
                return;
            }
            active = Math.min(active >= i ? active - 1 : active, tabs.length - 1);
            if (active < 0) active = 0;
            cm.swapDoc(tabs[active].doc);
            renderTabs();
            store();
        };
        if (t.dirty) {
            layer.confirm(esc(base(t.path)) + ' 有未保存的修改, 确定关闭吗?', { icon: 3, title: '关闭文件', btn: ['保存并关闭', '不保存', '取消'] },
                function (idx) { layer.close(idx); save(i, function (good) { if (good) go(); }); },
                function (idx) { layer.close(idx); go(); });
        } else go();
    }

    function hideAll() {
        state.open = false;
        state.minimized = false;
        clearInterval(autoTimer);
        win.find('[data-act=auto]').prop('checked', false);
        win.hide();
        dock.hide();
        persist();
    }

    function closeAll() {
        var dirty = tabs.filter(function (t) { return t.dirty; });
        var go = function () { tabs = []; active = -1; cm.swapDoc(CodeMirror.Doc('')); hideAll(); };
        if (dirty.length) {
            layer.confirm('有 ' + dirty.length + ' 个文件未保存, 确定关闭编辑器吗?', { icon: 3, title: '关闭编辑器', btn: ['全部保存后关闭', '不保存', '取消'] },
                function (idx) {
                    layer.close(idx);
                    var n = 0, bad = 0;
                    dirty.forEach(function (t) { save(tabs.indexOf(t), function (good) { n++; if (!good) bad++; if (n == dirty.length && !bad) go(); }); });
                },
                function (idx) { layer.close(idx); go(); });
        } else go();
    }

    // ------------------------------- 恢复 ---------------------------------------

    function resume() {
        var s = null;
        try { s = JSON.parse(sessionStorage.getItem(KEY) || 'null'); } catch (e) { }
        if (!s || !s.files || !s.files.length || typeof CodeMirror == 'undefined') return;
        build();
        state.minimized = !!s.minimized;
        state.max = !!s.max;
        state.rect = s.rect || null;
        var pending = s.files.length;
        var results = new Array(s.files.length);
        s.files.forEach(function (f, i) {
            fetchBody(f.path, function (d) {
                results[i] = { f: f, d: d };
                if (--pending) return;
                results.forEach(function (x) {
                    if (!x) return;
                    if (x.f.dirty && x.f.content !== null) {
                        // 未保存的修改: 恢复修改内容, 保留与服务器版本的对比
                        addTab(x.f.path, x.f.content, x.f.encoding, true, x.d ? x.d.data : '', null, x.f.cursor);
                    } else if (x.d) {
                        addTab(x.f.path, x.d.data, x.d.encoding, false, x.d.data, null, x.f.cursor);
                    }
                });
                if (!tabs.length) { persist(); return; }
                active = Math.min(Math.max(0, s.active), tabs.length - 1);
                cm.swapDoc(tabs[active].doc);
                if (s.open && !s.minimized) show();
                else { state.open = true; state.minimized = true; renderTabs(); renderDock(); }
                renderTabs();
            });
        });
    }

    $(function () { setTimeout(resume, 50); });

    return { open: open, save: function (path) { for (var i = 0; i < tabs.length; i++) if (tabs[i].path == path) return save(i); }, minimize: minimize, show: show };
})();
