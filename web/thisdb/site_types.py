# coding:utf-8

# ---------------------------------------------------------------------------------
# PM-Linux面板
# ---------------------------------------------------------------------------------
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------

__FIELD = 'id,name'

import core.mw as mw

def addSiteTypes(name):
    return mw.M('site_types').add("name", (name,))

def getSiteTypesCount():
    return mw.M('site_types').count()

def getSiteTypesCountByName(name):
    return mw.M('site_types').where('name=?', (name,)).count()

def getSiteTypesList():
    # .debug(True)
    return mw.M('site_types').field(__FIELD).order("id asc").select()


