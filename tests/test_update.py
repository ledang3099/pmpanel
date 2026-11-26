import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / 'scripts/update/apply_release.py'
spec = importlib.util.spec_from_file_location('apply_release', path)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class UpdateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.source = root / 'archive'
        self.dest = root / 'panel'
        (self.source / 'web').mkdir(parents=True)
        (self.dest / 'data').mkdir(parents=True)
        (self.source / 'web/app.py').write_text('new app')
        (self.source / 'a').write_text('new file')
        (self.source / 'b').write_text('new version')
        (self.dest / 'b').write_text('old version')
        (self.dest / 'data/panel.db').write_text('runtime')

    def test_success_keeps_runtime_files(self):
        release.apply_release(self.source, self.dest)
        self.assertEqual((self.dest / 'b').read_text(), 'new version')
        self.assertEqual((self.dest / 'data/panel.db').read_text(), 'runtime')

    def test_interrupted_copy_rolls_back(self):
        copy = release.shutil.copy2

        def interrupted_copy(source, target):
            if source.name == 'app.py':
                raise OSError('copy interrupted')
            return copy(source, target)

        with patch.object(release.shutil, 'copy2', interrupted_copy):
            with self.assertRaises(OSError):
                release.apply_release(self.source, self.dest)
        self.assertFalse((self.dest / 'a').exists())
        self.assertFalse((self.dest / 'web').exists())
        self.assertEqual((self.dest / 'b').read_text(), 'old version')
        self.assertEqual((self.dest / 'data/panel.db').read_text(), 'runtime')
