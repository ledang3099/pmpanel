# coding: utf-8
#-----------------------------
# 网站备份工具
#-----------------------------

import sys
import os
import time
import re
import gzip
import shutil
import subprocess
import tempfile

if sys.platform != 'darwin':
    os.chdir('/www/server/pmpanel')

web_dir = os.getcwd() + "/web"
if os.path.exists(web_dir):
    sys.path.append(web_dir)
    os.chdir(web_dir)

import core.mw as mw
import core.db as db

'''
DEBUG:
python3 /www/server/pmpanel/plugins/mysql-community/scripts/backup.py  database admin 3
'''
class backupTools:

    def getDbBackupList(self,dbname=''):
        bkDir = mw.getBackupDir() + '/database/mysql-community'
        if not os.path.isdir(bkDir):
            return []
        blist = os.listdir(bkDir)
        r = []

        bname = 'db_' + dbname + '_' + time.strftime('%Y', time.localtime())
        blen = len(bname)
        for x in blist:
            fbstr = x[0:blen]
            if fbstr == bname:
                r.append(x)
        # 文件名按时间戳命名,排序后即为时间顺序(旧->新)
        r.sort()
        return r

    def getConf(self, mtype='mysql'):
        path = mw.getServerDir() + '/' + mtype + '/etc/my.cnf'
        return path

    def recognizeDbMode(self, mtype='mysql'):
        conf = self.getConf(mtype)
        # print(conf)
        con = mw.readFile(conf)
        rep = r"!include %s/(.*)?\.cnf" % (mw.getServerDir() +'/'+ mtype +"/etc/mode",)
        mode = 'none'
        try:
            data = re.findall(rep, con, re.M)
            mode = data[0]
        except Exception as e:
            pass
        return mode

    def backupDatabase(self, params, count):
        params_args = params.split("@")
        name = params_args[0]
        table_name = ''
        if len(params_args) > 1:
            table_name = params_args[1]

        backup_name = name
        if table_name != '':
            backup_name = name+'@'+table_name

        db_path = mw.getServerDir() + '/mysql-community'
        db_name = 'mysql'
        find_name = mw.M('databases').dbPos(db_path, 'mysql').where(
            'name=?', (name,)).getField('name')
        startTime = time.time()
        if not find_name:
            endDate = time.strftime('%Y/%m/%d %X', time.localtime())
            log = "数据库[" + name + "]不存在!"
            print("★[" + endDate + "] " + log)
            print("----------------------------------------------------------------------------")
            return

        backup_path = mw.getBackupDir() + '/database/mysql-community'
        if not os.path.exists(backup_path):
            mw.execShell("mkdir -p " + backup_path)

        filename = backup_path + "/db_" + backup_name + "_" + \
            time.strftime('%Y%m%d_%H%M%S', time.localtime()) + ".sql.gz"

        mysql_root = mw.M('config').dbPos(db_path, db_name).where("id=?", (1,)).getField('mysql_root')

        my_conf_path = db_path + '/etc/my.cnf'
        command = [
            db_path + '/bin/mysqldump', '--defaults-file=' + my_conf_path,
            '--user=root', '--set-gtid-purged=off', '--single-transaction',
            '-q', '--default-character-set=utf8mb4', name,
        ]
        if table_name:
            command.append(table_name)

        with tempfile.NamedTemporaryFile(dir=backup_path, delete=False) as temporary:
            temporary_path = temporary.name
            try:
                with gzip.GzipFile(fileobj=temporary, mode='wb') as archive:
                    with subprocess.Popen(command, env=dict(os.environ, MYSQL_PWD=mysql_root),
                                          stdout=subprocess.PIPE) as dump:
                        shutil.copyfileobj(dump.stdout, archive)
                        if dump.wait():
                            raise SystemExit("数据库[{}]备份失败".format(backup_name))
                temporary.flush()
                os.replace(temporary_path, filename)
            finally:
                if os.path.exists(temporary_path):
                    os.unlink(temporary_path)

        endDate = time.strftime('%Y/%m/%d %X', time.localtime())
        outTime = time.time() - startTime
        
        log = "数据库[" + backup_name + "]备份成功,用时[" + str(round(outTime, 2)) + "]秒"
        mw.writeLog('计划任务', log)
        print("★[" + endDate + "] " + log)
        print("|---保留最新的[" + count + "]份备份")
        print("|---文件名:" + filename)

        backups = self.getDbBackupList(backup_name)
        # 清理多余备份
        num = len(backups) - int(count)
        if num > 0:
            for backup in backups:
                mw.execShell("rm -f " + backup_path + "/"+backup)
                num -= 1
                print("|---已清理过期文件：" + backup)
                if num < 1:
                    break


    def backupDatabaseAll(self, save):
        db_path = mw.getServerDir() + '/mysql-community'
        db_name = 'mysql'
        databases = mw.M('databases').dbPos(db_path, db_name).field('name').select()
        for database in databases:
            self.backupDatabase(database['name'], save)


if __name__ == "__main__":
    backup = backupTools()
    type = sys.argv[1]
    if type == 'database':
        if sys.argv[2].startswith('ALL@'):
            backup.backupDatabaseAll(sys.argv[3])
        else:
            backup.backupDatabase(sys.argv[2], sys.argv[3])
