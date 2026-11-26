# coding:utf-8

# ---------------------------------------------------------------------------------
# PM-Linux面板
# ---------------------------------------------------------------------------------
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------

import core.mw as mw

from .option  import getOption

__FIELD = 'id,name,path,status,ps,edate,type_id,add_time,update_time'

def checkSitesDomainIsExist(domain, port):
    nums = mw.M('domain').where("name=? AND port=?", (domain, port,)).count()
    if nums>0:
        return True

    nums = mw.M('binding').where("name=? AND port=?", (domain, port,)).count()
    if nums>0:
        return True
    return False

def getSitesCount():
    return mw.M('sites').count()

def getSitesById(site_id):
    return mw.M('sites').field(__FIELD).where("id=?", (site_id,)).find()

def getSitesByName(site_name):
    return mw.M('sites').field(__FIELD).where("name=?", (site_name,)).find()

def getSitesDomainById(site_id):
    data = {}
    domains = mw.M('domain').where('pid=?', (site_id,)).field('name,id').select()
    binding = mw.M('binding').where('pid=?', (site_id,)).field('domain,id').select()
    for b in binding:
        t = {}
        t['name'] = b['domain']
        t['id'] = b['id']
        domains.append(t)
    data['domains'] = domains
    data['email'] = getOption('ssl_email', default='')
    return data

def addSites(name, path):
    now_time = mw.getDateFromNow()
    insert_data = {
        'name': name,
        'path': path,
        'status': 1,
        'ps':name,
        'type_id':0,
        'edate':'0000-00-00',
        'add_time': now_time,
        'update_time': now_time
    }
    return mw.M('sites').insert(insert_data)


def isSitesExist(name):
    if mw.M('sites').where("name=?", (name,)).count() > 0:
        return True
    return False

def getSitesEdateList(edate):
    elist = mw.M('sites').field(__FIELD).where('edate>? AND edate<? AND status=?', ('0000-00-00', edate, 1,)).select()
    return elist

def getSitesList(
    page = 1,
    size = 10,
    type_id = 0,
    search = '',
    order = None,
):
    sql_where = ''
    sql_param = ()
    has_type = str(type_id) != '' and str(type_id).lstrip('-').isdigit() and int(type_id) >= 0
    if search != '' :
        kw = '%' + search + '%'
        sql_where = "(name like ? or ps like ?)"
        sql_param = (kw, kw)
    if has_type:
        if sql_where != '':
            sql_where = sql_where + " and type_id=?"
        else:
            sql_where = "type_id=?"
        sql_param = sql_param + (int(type_id),)

    dbM = mw.M('sites').field(__FIELD)
    dbC = mw.M('sites').field(__FIELD)

    if sql_where != '':
        count = dbC.where(sql_where, sql_param).count()
        dbM.where(sql_where, sql_param)
    else:
        count = dbC.count()

    start = (int(page) - 1) * (int(size))
    limit = str(start) + ',' +str(size)

    import re
    # 排序字段使用白名单, 防止 ORDER BY 注入
    order_ok = order is not None and re.match(r'^(id|name|path|status|edate|add_time|addtime|ps|type_id)( (asc|desc))?$', order.strip().lower())
    if order is not None and order.find("none") > -1:
        site_list = dbM.limit(limit).order('').select()
    elif order_ok:
        site_list = dbM.limit(limit).order(order.strip()).select()
    else:
        site_list = dbM.limit(limit).order('id desc').select()

    data = {}
    data['list'] = site_list
    data['count'] = count
    return data


def deleteSitesById(site_id):
    return mw.M('sites').where("id=?", (site_id,)).delete()

def setSitesData(site_id, edate = None, ps = None, path = None,status = None):
    update_data = {}
    if edate is not None:
        update_data['edate'] = edate
    if ps is not None:
        update_data['ps'] = ps

    if path is not None:
        update_data['path'] = path

    if status is not None:
        update_data['status'] = status

    return mw.M('sites').where('id=?',(site_id,)).update(update_data)

