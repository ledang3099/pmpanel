import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest

# ssh_manage 依赖面板核心模块 core.mw, 测试中用最小替身代替
core = types.ModuleType('core')
mw = types.ModuleType('core.mw')
mw.returnData = lambda status, msg, data=None: {'status': status, 'msg': msg, 'data': data}
mw.readFile = lambda path: open(path).read() if os.path.exists(path) else False
mw.writeFile = lambda path, content: open(path, 'w').write(content)
mw.writeLog = lambda *a: None
core.mw = mw
sys.modules.setdefault('core', core)
sys.modules.setdefault('core.mw', mw)

path = Path(__file__).resolve().parents[1] / 'web/utils/ssh_manage.py'
spec = importlib.util.spec_from_file_location('ssh_manage', path)
ssh_manage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ssh_manage)

SAMPLE = '''\
2026-11-27T09:13:54.551290+00:00 vm sshd[781]: Failed password for sshtest from 127.0.0.1 port 44426 ssh2
2026-11-27T09:14:03.373690+00:00 vm sshd[796]: Accepted password for sshtest from 127.0.0.1 port 38434 ssh2
2026-11-27T09:14:03.375047+00:00 vm sshd[796]: pam_unix(sshd:session): session opened for user sshtest(uid=1001) by (uid=0)
2026-11-27T09:14:05.656436+00:00 vm sshd[811]: Failed password for invalid user nouser from 203.0.113.9 port 38448 ssh2
Nov 26 08:00:01 web1 sshd[100]: Accepted publickey for root from 2001:db8::5 port 50000 ssh2: ED25519 SHA256:abc
Nov 26 08:00:02 web1 sshd-session[101]: Failed publickey for deploy from 198.51.100.7 port 50001 ssh2: RSA SHA256:def
Nov  3 07:00:00 web1 sshd[102]: Accepted keyboard-interactive/pam for alice from 192.0.2.1 port 1 ssh2
Nov 26 08:00:03 web1 CRON[200]: pam_unix(cron:session): session opened for user root
2026-11-27T09:20:00+0000 vm sshd[900]: Connection closed by authenticating user x 1.2.3.4 port 1 [preauth]
'''


class SshLogTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.log = Path(tmp.name) / 'auth.log'
        self.log.write_text(SAMPLE)
        self.m = ssh_manage.SshManage()
        self.m.logSources = lambda: [str(self.log)]

    def test_parses_iso_bsd_and_sshd_session(self):
        rows = self.m.records()
        self.assertEqual(len(rows), 6)
        by = {(r['user'], r['status']) for r in rows}
        self.assertIn(('sshtest', 1), by)
        self.assertIn(('nouser', 0), by)
        self.assertIn(('root', 1), by)
        self.assertIn(('deploy', 0), by)
        self.assertIn(('alice', 1), by)
        root = [r for r in rows if r['user'] == 'root'][0]
        self.assertEqual(root['ip'], '2001:db8::5')
        self.assertEqual(root['method'], 'publickey')
        self.assertTrue([r for r in rows if r['user'] == 'nouser'][0]['invalid'])

    def test_sorted_newest_first(self):
        times = [r['time'] for r in self.m.records()]
        self.assertEqual(times, sorted(times, reverse=True))

    def test_filters_and_search(self):
        self.assertEqual(self.m.getLogs(status='fail')['data']['total'], 3)
        self.assertEqual(self.m.getLogs(status='success')['data']['total'], 3)
        self.assertEqual(self.m.getLogs(search='203.0.113.9')['data']['total'], 1)
        self.assertEqual(self.m.getLogs(page=2, limit=4)['data']['list'][0]['time'], self.m.records()[4]['time'])

    def test_stats(self):
        st = self.m.getStats()['data']
        self.assertEqual(st['success_total'], 3)
        self.assertEqual(st['fail_total'], 3)
        self.assertEqual(st['fail_ip_count'], 3)

    def test_cache_invalidated_on_change(self):
        self.assertEqual(len(self.m.records()), 6)
        with open(self.log, 'a') as f:
            f.write('2026-11-27T10:00:00+00:00 vm sshd[1]: Accepted password for bob from 192.0.2.9 port 2 ssh2\n')
        self.assertEqual(len(self.m.records()), 7)

    def test_rejects_bad_settings(self):
        self.assertFalse(self.m.setValues({'Port': '0'})['status'])
        self.assertFalse(self.m.setValues({'Banner': '/etc/shadow'})['status'])
        self.assertFalse(self.m.setValues({'PermitRootLogin': 'yes\nPermitEmptyPasswords yes'})['status'])


if __name__ == '__main__':
    unittest.main()
