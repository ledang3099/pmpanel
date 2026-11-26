from contextlib import redirect_stdout
from io import StringIO
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


class PanelCliTests(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.panel = Path(work.name)
        (self.panel / 'web').mkdir()
        (self.panel / 'data').mkdir()
        script = self.panel / 'scripts/init.d/pm'
        script.parent.mkdir(parents=True)
        script.write_text('printf "%s\\n" "$1" >> ' + str(self.panel / 'actions') + '\n')
        self.db = Mock()
        self.firewall = Mock()
        self.mw = Mock()
        self.mw.getPanelDir.return_value = str(self.panel)
        modules = {name: ModuleType(name) for name in ('core', 'utils', 'utils.firewall')}
        modules['core.mw'] = self.mw
        modules['thisdb'] = self.db
        modules['utils.firewall'].Firewall = self.firewall
        security = ModuleType('utils.security')
        security.__dict__.update(runpy.run_path(str(ROOT / 'web/utils/security.py')))
        modules['utils.security'] = security
        cwd = os.getcwd()
        sys_path = sys.path[:]
        try:
            os.chdir(self.panel)
            with patch.dict(sys.modules, modules):
                self.cli = runpy.run_path(str(ROOT / 'panel_tools.py'))['mwcli']
        finally:
            os.chdir(cwd)
            sys.path[:] = sys_path

    def actions(self):
        return (self.panel / 'actions').read_text().splitlines()

    def test_interactive_and_direct_service_options(self):
        real_isfile = os.path.isfile
        with patch('os.path.isfile', side_effect=lambda p: not p.startswith('/etc/') and real_isfile(p)):
            with patch('builtins.input', return_value='1'), redirect_stdout(StringIO()):
                self.assertEqual(self.cli(), 0)
            for selection in (2, 3, 4, 10):
                self.assertEqual(self.cli(selection), 0)
        self.assertEqual(self.actions(), ['restart', 'stop', 'start', 'reload', 'default'])

    def test_service_failure_is_returned_to_caller(self):
        with patch('os.path.isfile', return_value=True), patch('subprocess.call', return_value=4):
            self.assertEqual(self.cli(1), 4)

    def test_port_input_is_validated_before_changes(self):
        with patch('builtins.input', return_value='invalid'):
            self.assertEqual(self.cli(6), 1)
        self.firewall.instance.assert_not_called()
        self.mw.writeFile.assert_not_called()

    def test_port_change_restarts_before_showing_defaults(self):
        with patch('builtins.input', return_value=' 18080 '), patch('os.path.isfile', return_value=True):
            with patch('subprocess.call', return_value=0) as call:
                self.assertEqual(self.cli(6), 0)
        self.mw.writeFile.assert_called_once_with(str(self.panel / 'data/port.pl'), '18080')
        self.assertEqual([args.args[0][-1] for args in call.call_args_list], ['restart_panel', 'default'])

    def test_disabling_ssl_restarts_panel_without_unbinding_domain(self):
        self.db.getOptionByJson.return_value = {'open': True, 'choose': 'local'}
        with patch('os.path.isfile', return_value=True), patch('subprocess.call', return_value=0) as call:
            self.cli(22)
        self.db.setOption.assert_called_once_with('panel_ssl', '{"open": false, "choose": "local"}')
        self.assertEqual(call.call_args.args[0][-1], 'restart_panel')

    def test_shell_aliases_call_the_expected_menu_items(self):
        setup = (ROOT / 'scripts/init.d/pm.tpl').read_text()
        script = self.panel / 'pm'
        script.write_text(setup.replace('{$SERVER_PATH}', str(self.panel)))
        venv = self.panel / 'bin'
        venv.mkdir()
        (venv / 'activate').write_text('export PATH="' + str(venv) + ':$PATH"\n')
        python = venv / 'python3'
        python.write_text('#!/bin/sh\nprintf "%s\\n" "$3"\n')
        python.chmod(0o755)
        for alias, number in [('close_admin_path', '7'), ('unbind_domain', '21'), ('unbind_ssl', '22')]:
            with self.subTest(alias=alias):
                result = subprocess.check_output(['bash', str(script), alias], text=True)
                self.assertEqual(result.strip(), number)


if __name__ == '__main__':
    unittest.main()
