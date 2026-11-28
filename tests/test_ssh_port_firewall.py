import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]

# ssh_manage 依赖面板核心模块 core.mw, 测试中用最小替身代替
core = types.ModuleType('core')
mw_stub = types.ModuleType('core.mw')
mw_stub.returnData = lambda status, msg, data=None: {'status': status, 'msg': msg, 'data': data}
mw_stub.readFile = lambda path: open(path).read() if os.path.exists(path) else False
mw_stub.writeFile = lambda path, content: open(path, 'w').write(content)
mw_stub.writeLog = lambda *a: None
core.mw = mw_stub
sys.modules.setdefault('core', core)
sys.modules.setdefault('core.mw', mw_stub)
# 其他测试可能先注册了 core.mw 替身, 补齐本测试需要的函数
for _k in ('returnData', 'readFile', 'writeFile', 'writeLog'):
    if not hasattr(sys.modules['core.mw'], _k):
        setattr(sys.modules['core.mw'], _k, getattr(mw_stub, _k))

spec = importlib.util.spec_from_file_location('ssh_manage_port', ROOT / 'web/utils/ssh_manage.py')
ssh_manage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ssh_manage)


class FakeFirewall(object):
    result = None
    calls = []

    @classmethod
    def instance(cls):
        return cls()

    def ensurePortOpen(self, port, ps, protocol='tcp'):
        FakeFirewall.calls.append(port)
        return FakeFirewall.result


class SshPortFirewallTests(unittest.TestCase):
    def setUp(self):
        mod = types.ModuleType('utils.firewall')
        mod.Firewall = FakeFirewall
        pkg = sys.modules.get('utils') or types.ModuleType('utils')
        self._saved = {k: sys.modules.get(k) for k in ('utils', 'utils.firewall')}
        sys.modules['utils'] = pkg
        sys.modules['utils.firewall'] = mod
        FakeFirewall.calls = []
        self.sm = ssh_manage.SshManage.__new__(ssh_manage.SshManage)
        self.written = []
        self.sm.effective = lambda: {'port': '22'}
        self.sm.setValues = lambda values: (self.written.append(values), {'status': True, 'msg': 'ok'})[1]
        self.sm.applyAndReload = lambda port_changed=False: {'status': True, 'msg': '设置成功'}

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v

    def test_port_not_changed_when_firewall_open_fails(self):
        FakeFirewall.result = {'status': False, 'msg': '防火墙放行端口[2222/tcp]失败'}
        r = self.sm.setPort('2222')
        self.assertFalse(r['status'])
        self.assertIn('已取消', r['msg'])
        self.assertEqual(self.written, [])
        self.assertEqual(FakeFirewall.calls, ['2222'])

    def test_port_changed_after_firewall_opened(self):
        FakeFirewall.result = {'status': True, 'msg': '端口已放行'}
        r = self.sm.setPort('2222')
        self.assertTrue(r['status'])
        self.assertEqual(self.written, [{'Port': '2222'}])


class ClearTermSizeEnvTests(unittest.TestCase):
    def test_child_process_does_not_inherit_columns(self):
        # readline 通过 C 层 setenv 写入 COLUMNS, os.environ 看不到, 这里用 os.putenv 模拟
        code = (
            "import importlib.util, os, subprocess, sys\n"
            "spec = importlib.util.spec_from_file_location('mw', sys.argv[1])\n"
            "mw = importlib.util.module_from_spec(spec); spec.loader.exec_module(mw)\n"
            "os.putenv('COLUMNS', '80'); os.putenv('LINES', '24')\n"
            "before = subprocess.run(['env'], capture_output=True, text=True).stdout\n"
            "mw.clearTermSizeEnv()\n"
            "after = subprocess.run(['env'], capture_output=True, text=True).stdout\n"
            "print('BEFORE' if 'COLUMNS=80' in before else '', 'AFTER' if ('COLUMNS=' in after or 'LINES=' in after) else '')\n"
        )
        env = {k: v for k, v in os.environ.items() if k not in ('COLUMNS', 'LINES')}
        out = subprocess.run([sys.executable, '-c', code, str(ROOT / 'web/core/mw.py')],
                             capture_output=True, text=True, env=env, cwd=str(ROOT / 'web')).stdout
        self.assertIn('BEFORE', out)
        self.assertNotIn('AFTER', out)


if __name__ == '__main__':
    unittest.main()
