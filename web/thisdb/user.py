# coding:utf-8

# ---------------------------------------------------------------------------------
# PM-Linux面板
# ---------------------------------------------------------------------------------
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------

import core.mw as mw
import utils.security as security

__field = 'id,name,password,login_ip,login_time,phone,email,add_time,update_time'

# 初始化用户信息
def initAdminUser():
    data = mw.M('users').field(__field).where('id=?', (1,)).find()
    if data is None:
        name = mw.getRandomString(8).lower()
        password = mw.getRandomString(16)
        now_time = mw.formatDate()
        login_ip = '127.0.0.1'
        add_user = {
            'name':name, 
            'password':security.hash_password(password),
            'login_ip':login_ip,
            'login_time':now_time,
            'phone':'',
            'email':'',
            'add_time':now_time,
            'update_time':now_time
        }
        file_pass_pl = mw.getPanelDataDir() + '/default.pl'
        mw.writeFile(file_pass_pl, password)
        security.restrict_file(file_pass_pl)
        mw.M('users').insert(add_user)
    return True


def getUserByName(name) -> None:
    '''
    获取用户信息通过用户名
    '''
    data =  mw.M('users').field(__field).where('name=?', (name,)).find()
    if data is None:
        return None
    row = {}
    row['id'] = data['id']
    row['name'] = data['name']
    row['password'] = data['password']
    row['login_ip'] = data['login_ip']
    row['login_time'] = data['login_time']
    row['phone'] = data['phone']
    row['email'] = data['email']
    row['add_time'] = data['add_time']
    row['update_time'] = data['update_time']
    return row

def getUserById(id) -> None:
    '''
    获取用户信息通过用户名
    '''
    data =  mw.M('users').field(__field).where('id=?', (id,)).find()
    if data is None:
        return None
    row = {}
    row['id'] = data['id']
    row['name'] = data['name']
    row['password'] = data['password']
    row['login_ip'] = data['login_ip']
    row['login_time'] = data['login_time']
    row['phone'] = data['phone']
    row['email'] = data['email']
    row['add_time'] = data['add_time']
    row['update_time'] = data['update_time']
    return row


def getUserByRoot() -> None:
    '''
    获取用户信息通过用户名
    '''
    return getUserById(1)

def updateUserLoginTime():
    now_time = mw.formatDate()
    mw.M('users').field(__field).where('id=?', (1,)).update({'login_time':now_time})
    return True

def setUserByName(name, new_name):
    return mw.M('users').where("name=?", (name,)).setField('name', new_name.strip())

def checkUserPassword(info, password):
    '''
    校验用户密码; 旧版md5哈希校验通过后自动升级为bcrypt
    '''
    if info is None:
        return False
    ok, need_upgrade = security.verify_password(password, info['password'])
    if ok and need_upgrade:
        mw.M('users').where('id=?', (info['id'],)).setField('password', security.hash_password(password))
    return ok

def setUserPwdByName(name, password):
    pwd = security.hash_password(password)
    return mw.M('users').where("name=?", (name,)).setField('password', pwd)

def setUserByRoot(name = None,password = None) -> bool:
    '''
    设置配置的值
    :name -> str 名称 (必填)
    :value -> object值 (必填)
    :type -> str 类型 (可选|默认common)
    '''
    data = {}
    if name is not None:
        mw.M('users').where('id=?', (1,)).setField('name', name)

    if password is not None:
        pwd = security.hash_password(password)
        mw.M('users').where('id=?', (1,)).setField('password', pwd)

    if not data:
        return False
    return True