# coding:utf-8

# ---------------------------------------------------------------------------------
# PM-Linux面板
# ---------------------------------------------------------------------------------
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------

from flask import request


import core.mw as mw
import thisdb

# 初始化用户信息
def init_admin_user():
    thisdb.initAdminUser()
    return True

