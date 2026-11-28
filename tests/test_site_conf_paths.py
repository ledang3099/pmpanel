import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]

# site.py 依赖面板核心模块, 测试中用最小替身代替
core = types.ModuleType('core')
mw_stub = types.ModuleType('core.mw')
mw_stub.returnData = lambda status, msg, data=None: {'status': status, 'msg': msg, 'data': data}
sys.modules.setdefault('core', core)
sys.modules.setdefault('core.mw', mw_stub)
for _k in ('returnData',):
    if not hasattr(sys.modules['core.mw'], _k):
        setattr(sys.modules['core.mw'], _k, getattr(mw_stub, _k))

SITES = {'a.example.com'}
thisdb_stub = types.ModuleType('thisdb')
thisdb_stub.isSitesExist = lambda name: name in SITES
_saved_thisdb = sys.modules.get('thisdb')
sys.modules['thisdb'] = thisdb_stub

spec = importlib.util.spec_from_file_location('site_conf_paths', ROOT / 'web/utils/site.py')
site_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(site_mod)

if _saved_thisdb is not None:
    sys.modules['thisdb'] = _saved_thisdb


class SiteConfPathTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = self.tmp.name
        self.site = site_mod.sites.__new__(site_mod.sites)
        self.site.rewritePath = os.path.join(base, 'rewrite')
        self.site.proxyPath = os.path.join(base, 'proxy')
        os.makedirs(self.site.rewritePath)
        os.makedirs(self.site.proxyPath)
        site_mod.thisdb = thisdb_stub

    def tearDown(self):
        self.tmp.cleanup()

    def test_rewrite_path_inside_rewrite_dir(self):
        p = os.path.join(self.site.rewritePath, 'a.example.com.conf')
        self.assertTrue(self.site.isRewriteConfPath(p))
        self.assertTrue(self.site.isRewriteConfPath(os.path.join(self.site.rewritePath, 'a.example.com_sub.conf')))

    def test_rewrite_path_rejects_other_locations(self):
        self.assertFalse(self.site.isRewriteConfPath('/etc/cron.d/evil.conf'))
        self.assertFalse(self.site.isRewriteConfPath(os.path.join(self.site.rewritePath, '..', 'x.conf')))
        self.assertFalse(self.site.isRewriteConfPath(os.path.join(self.site.rewritePath, 'sub', 'x.conf')))
        self.assertFalse(self.site.isRewriteConfPath(os.path.join(self.site.rewritePath, 'a.example.com.txt')))
        self.assertFalse(self.site.isRewriteConfPath(''))

    def test_rewrite_path_rejects_symlink(self):
        target = os.path.join(self.tmp.name, 'outside.conf')
        open(target, 'w').close()
        link = os.path.join(self.site.rewritePath, 'link.conf')
        os.symlink(target, link)
        self.assertFalse(self.site.isRewriteConfPath(link))

    def test_conf_dir_created_for_existing_site(self):
        d = self.site.ensureSiteConfDir(self.site.proxyPath, 'a.example.com')
        self.assertEqual(d, os.path.join(self.site.proxyPath, 'a.example.com'))
        self.assertTrue(os.path.isdir(d))

    def test_conf_dir_rejects_unknown_or_traversal_site(self):
        self.assertIsNone(self.site.ensureSiteConfDir(self.site.proxyPath, 'nope.example.com'))
        self.assertIsNone(self.site.ensureSiteConfDir(self.site.proxyPath, '../../etc'))
        self.assertIsNone(self.site.ensureSiteConfDir(self.site.proxyPath, ''))
        self.assertEqual(os.listdir(self.site.proxyPath), [])


if __name__ == '__main__':
    unittest.main()
