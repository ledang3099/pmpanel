import os
from pathlib import Path
import re
import subprocess
import sys

import core.mw as mw
from utils.security import is_safe_name


def generate(stype, name, count, echo=''):
    keep = int(count)
    if keep < 1:
        raise ValueError('备份保留数量必须大于零。')
    panel = Path(mw.getPanelDir())
    backup_dir = Path(mw.getBackupDir())
    script = panel / 'scripts' / 'backup.py'
    args = [stype, name, count]
    if stype.startswith('database_'):
        plugin = stype[len('database_'):]
        if not is_safe_name(plugin):
            raise ValueError('无效的数据库备份插件。')
        script = panel / 'plugins' / plugin / 'scripts' / 'backup.py'
        args[0] = 'database'
        folder, prefix, kind = backup_dir / 'database' / plugin, 'db_' + name, 'database'
    elif stype == 'database':
        folder, prefix, kind = backup_dir / 'database' / 'mysql', 'db_' + name, stype
    elif stype == 'site':
        args.append(echo)
        folder, prefix, kind = backup_dir / 'site', 'web_' + name, stype
    elif stype == 'path':
        args.append(echo)
        folder, prefix, kind = backup_dir / 'path', 'path_' + os.path.basename(os.path.normpath(name)), stype
    else:
        raise ValueError('无效的备份类型。')

    archive_name = re.compile(re.escape(prefix) + r'_\d{8}_\d{6}\.(tar|sql)\.gz')

    def archives():
        if not folder.is_dir():
            return {}
        return {
            file: file.stat().st_mtime_ns for file in folder.iterdir()
            if archive_name.fullmatch(file.name) and file.is_file()
        }

    before = archives()
    subprocess.run([sys.executable, str(script), *args], check=True)
    new = [file for file, mtime in archives().items() if before.get(file) != mtime]
    if not new:
        raise SystemExit('未生成新的备份文件。')
    latest = max(new)
    previous = sorted(file for file in before if file != latest)
    return str(latest), kind, previous[:max(0, len(previous) + 1 - keep)]


def upload(stype, client):
    filename, kind, expired = generate(stype, *sys.argv[2:5])
    mw.echoInfo('准备上传文件 {}'.format(filename))
    if not client.upload_file(filename, kind):
        raise SystemExit('备份上传失败。')
    mw.echoEnd('上传')
    for file in expired:
        if not client.delete_file(file.name, kind):
            raise SystemExit('备份已上传，但无法清理远程旧备份。')
        mw.echoInfo('已清理远程过期备份文件：' + file.name)
    return ''
