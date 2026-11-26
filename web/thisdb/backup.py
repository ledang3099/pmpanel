# coding:utf-8

# ---------------------------------------------------------------------------------
# PM-Linux面板
# ---------------------------------------------------------------------------------
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------

import core.mw as mw

__FIELD = 'id,pid,type,name,filename,size,add_time'

def addBackup(pid,name,filename,size,type=0):

    add_time = mw.formatDate()
    insert_data = {
        'type':type,
        'name':name,
        'pid':pid,
        'filename':filename,
        'size':size,
        'add_time':add_time,
    }
    mw.M('backup').insert(insert_data)
    return True

def getBackupById(bp_id):
    return mw.M('backup').field(__FIELD).where("id=?", (bp_id,)).find()

def getBackupPage(site_id,page = 1,size = 10):
    start = (int(page) - 1) * int(size)
    limit = str(start) + ',' + str(size)
    bk_list = mw.M('backup').where('pid=?', (site_id,)).field(__FIELD).limit(limit).order('id desc').select()
    count = mw.M('backup').where('pid=?', (site_id,)).count()

    rdata = {}
    rdata['list'] = bk_list
    rdata['count'] = count
    return rdata

def deleteBackupById(bp_id):
    return mw.M('backup').where("id=?", (bp_id,)).delete()
