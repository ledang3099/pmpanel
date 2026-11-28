import importlib.util
from pathlib import Path
import threading
import time
import unittest

path = Path(__file__).resolve().parents[1] / 'web/utils/ssh/pty_terminal.py'
spec = importlib.util.spec_from_file_location('pty_terminal', path)
pty_terminal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pty_terminal)


class PtyTerminalTests(unittest.TestCase):
    def setUp(self):
        self.pt = pty_terminal.PtyTerminal()
        self.events = []
        self.lock = threading.Lock()

    def tearDown(self):
        self.pt.closeClient('sid1')
        self.pt.closeClient('sid2')

    def emit(self, event, data):
        with self.lock:
            self.events.append((event, data))

    def output(self, tid):
        with self.lock:
            return ''.join(d['data'] for e, d in self.events if e == 'pm_term_out' and d['tid'] == tid)

    def wait_for(self, tid, text, timeout=5):
        end = time.time() + timeout
        while time.time() < end:
            if text in self.output(tid):
                return True
            time.sleep(0.05)
        return False

    def test_runs_commands_and_keeps_sessions_apart(self):
        self.assertEqual(self.pt.open('sid1', 'a', 80, 24, '/tmp', self.emit)[0], True)
        self.assertEqual(self.pt.open('sid1', 'b', 80, 24, '/', self.emit)[0], True)
        self.pt.write('sid1', 'a', 'echo one-$((40+2)); pwd\r')
        self.pt.write('sid1', 'b', 'echo two-$((1+1))\r')
        self.assertTrue(self.wait_for('a', 'one-42'))
        self.assertTrue(self.wait_for('a', '/tmp'))
        self.assertTrue(self.wait_for('b', 'two-2'))
        self.assertNotIn('two-2', self.output('a'))

    def test_resize_changes_columns(self):
        self.pt.open('sid1', 'r', 80, 24, '', self.emit)
        self.pt.resize('sid1', 'r', 132, 40)
        self.pt.write('sid1', 'r', 'stty size\r')
        self.assertTrue(self.wait_for('r', '40 132'))

    def test_exit_reports_and_cleans_up(self):
        self.pt.open('sid1', 'x', 80, 24, '', self.emit)
        self.pt.write('sid1', 'x', 'exit\r')
        end = time.time() + 5
        while time.time() < end and ('pm_term_exit', {'tid': 'x'}) not in self.events:
            time.sleep(0.05)
        self.assertIn(('pm_term_exit', {'tid': 'x'}), self.events)
        self.assertNotIn(('sid1', 'x'), self.pt.sessions)

    def test_close_client_ends_only_its_sessions(self):
        self.pt.open('sid1', 'a', 80, 24, '', self.emit)
        self.pt.open('sid2', 'a', 80, 24, '', self.emit)
        self.pt.closeClient('sid1')
        self.assertNotIn(('sid1', 'a'), self.pt.sessions)
        self.assertIn(('sid2', 'a'), self.pt.sessions)

    def test_per_client_limit(self):
        for i in range(pty_terminal.MAX_PER_CLIENT):
            self.assertTrue(self.pt.open('sid1', str(i), 80, 24, '', self.emit)[0])
        ok, msg = self.pt.open('sid1', 'extra', 80, 24, '', self.emit)
        self.assertFalse(ok)


if __name__ == '__main__':
    unittest.main()
