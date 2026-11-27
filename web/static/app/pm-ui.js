// PM-Linux面板 新版页面公共工具(安全 / 数据库 / 日志等栏目共用)

// HTML 文本/属性转义
function pmEsc(s) {
    return String(s === undefined || s === null ? '' : s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// POST 请求: 自动显示加载层, 返回 JSON; opts.silent 不显示加载
function pmPost(url, data, callback, opts) {
    opts = opts || {};
    var loading = opts.silent ? null : layer.msg(opts.loading || '正在处理, 请稍候...', { icon: 16, time: 0, shade: [0.15, '#000'] });
    $.ajax({
        url: url, type: 'POST', data: data || {}, dataType: 'json',
        success: function (r) {
            if (loading !== null) layer.close(loading);
            callback && callback(r);
        },
        error: function (xhr) {
            if (loading !== null) layer.close(loading);
            layer.msg('请求失败: ' + (xhr.status || '网络错误'), { icon: 2 });
        }
    });
}

// 显示接口结果; 成功时执行 done
function pmResult(r, done) {
    layer.msg(r.msg || (r.status ? '操作成功' : '操作失败'), { icon: r.status ? 1 : 2, time: r.status ? 1500 : 4000 });
    if (r.status && done) done(r);
}

// 分页条: 返回 HTML, 点击时调用 onPage(page)
function pmPager(id, total, page, limit, onPage) {
    var pages = Math.max(1, Math.ceil(total / limit));
    page = Math.min(Math.max(1, page), pages);
    var html = '<span>共 ' + total + ' 条</span>';
    html += '<a data-p="' + (page - 1) + '" class="' + (page <= 1 ? 'disabled' : '') + '">上一页</a>';
    var start = Math.max(1, page - 2), end = Math.min(pages, start + 4);
    start = Math.max(1, end - 4);
    for (var i = start; i <= end; i++) {
        html += '<a data-p="' + i + '" class="' + (i == page ? 'on' : '') + '">' + i + '</a>';
    }
    html += '<a data-p="' + (page + 1) + '" class="' + (page >= pages ? 'disabled' : '') + '">下一页</a>';
    var box = $('#' + id).html(html).addClass('pm-pager');
    box.find('a').on('click', function () {
        var p = parseInt($(this).attr('data-p'));
        if (p >= 1 && p <= pages && p != page) onPage(p);
    });
}

// 开关 HTML
function pmSwitch(id, checked, disabled) {
    return '<label class="pm-switch"><input type="checkbox" id="' + pmEsc(id) + '"' + (checked ? ' checked' : '') +
        (disabled ? ' disabled' : '') + '><span></span></label>';
}

// 页面标签: 点击切换并记住到 location.hash
function pmTabs(container, onSwitch) {
    var box = $(container);
    box.find('.pm-tab').on('click', function () {
        var name = $(this).attr('data-tab');
        box.find('.pm-tab').removeClass('on');
        $(this).addClass('on');
        if (history.replaceState) history.replaceState(null, '', '#' + name);
        onSwitch(name);
    });
    var open = function () {
        var cur = (location.hash || '').replace('#', '');
        var target = box.find('.pm-tab[data-tab="' + cur + '"]');
        if (target.length && target.hasClass('on')) return;
        (target.length ? target : box.find('.pm-tab').first()).trigger('click');
    };
    $(window).on('hashchange', open);
    open();
}

// 让浏览器下载一段文本
function pmDownloadText(filename, text) {
    var blob = new Blob([text], { type: 'application/octet-stream' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
}
