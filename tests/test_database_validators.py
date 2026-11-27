import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest

core = sys.modules.get('core') or types.ModuleType('core')
mw = sys.modules.get('core.mw') or types.ModuleType('core.mw')
mw.returnData = lambda status, msg, data=None: {'status': status, 'msg': msg, 'data': data}
BACKUP = tempfile.mkdtemp()
mw.getBackupDir = lambda: BACKUP
mw.getServerDir = lambda: '/nonexistent'
core.mw = mw
sys.modules['core'] = core
sys.modules['core.mw'] = mw

path = Path(__file__).resolve().parents[1] / 'web/utils/database.py'
spec = importlib.util.spec_from_file_location('database', path)
database = importlib.util.module_from_spec(spec)
spec.loader.exec_module(database)
V = database.VALIDATORS


class DatabaseValidatorTests(unittest.TestCase):
    def test_password_rejects_sql_breakers(self):
        self.assertTrue(V['password']('Abc_123!@#'))
        for bad in ["a'b123", 'a"b123', 'a\\b123', 'a`b123', 'a b123', '12345']:
            self.assertFalse(V['password'](bad), bad)

    def test_names(self):
        self.assertTrue(V['name']('wp_site-1'))
        for bad in ['a`b', 'a b', 'a;b', '', 'x' * 65, '../x']:
            self.assertFalse(V['name'](bad), bad)

    def test_files_and_paths(self):
        self.assertTrue(V['file']('db_2026.sql.gz'))
        self.assertFalse(V['file']('../../etc/passwd'))
        self.assertFalse(V['file']('a/b.sql'))
        self.assertTrue(V['path'](''))
        self.assertTrue(V['path'](os.path.join(BACKUP, 'import')))
        self.assertFalse(V['path']('/tmp'))
        self.assertFalse(V['path'](BACKUP + '/../etc'))

    def test_json_lists(self):
        self.assertTrue(V['tables'](json.dumps(['posts', 'wp_users'])))
        self.assertFalse(V['tables'](json.dumps(['posts`; drop table x'])))
        self.assertFalse(V['tables']('not json'))
        self.assertTrue(V['ids'](json.dumps([1, 2])))
        self.assertFalse(V['ids'](json.dumps(['1 or 1=1'])))

    def test_access_and_charset(self):
        self.assertTrue(V['access']('%'))
        self.assertTrue(V['access']('10.0.0.1,10.0.0.0/24'))
        self.assertFalse(V['access']("%' or 1=1"))
        self.assertFalse(V['codeing']('utf8mb4 COLLATE x'))

    def test_call_rejects_unknown(self):
        db = database.Database()
        self.assertFalse(db.call('../../etc', 'get_db_list', {})['status'])
        self.assertFalse(db.call('mysql', 'dump_mysql_data', {})['status'])


if __name__ == '__main__':
    unittest.main()
