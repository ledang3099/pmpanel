# coding:utf-8

# ---------------------------------------------------------------------------------
# PM-Linux面板
# ---------------------------------------------------------------------------------
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------

import json


import core.mw as mw

def clearLog():
    mw.M('logs').where('id>?', (0,)).delete()
    mw.M('logs').execute("update sqlite_sequence set seq=0 where name='logs'")
    return True

def addLog(type, log, uid = 1) -> bool:
    '''
    添加日志
    :type -> str 类型 (必填)
    :log -> str 日志内容 (必填)
    :uid -> int 用户ID
    '''

    # if log.find("eval") > -1:
    #     return False

    add_time = mw.formatDate()
    insert_data = {
        'type':type,
        'log':log,
        'add_time':add_time,
    }
    mw.M('logs').insert(insert_data)
    return True

def getLogsList(page = 1,size = 10,search = ''):
    field = 'id,type,log,uid,add_time'
    start = (int(page) - 1) * (int(size))
    limit = str(start) + ',' +str(size)

    # 参数化查询, 防止SQL注入; 旧版的搜索条件也没有作用到列表上
    if search != '' :
        kw = '%' + search + '%'
        count = mw.M('logs').field(field).where("type like ? or log like ?", (kw, kw)).count()
        logs_list = mw.M('logs').field(field).where("type like ? or log like ?", (kw, kw)).limit(limit).order('id desc').select()
    else:
        count = mw.M('logs').field(field).count()
        logs_list = mw.M('logs').field(field).limit(limit).order('id desc').select()

    data = {}
    data['list'] = logs_list
    data['count'] = count
    return data