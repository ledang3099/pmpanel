"""Overlay a staged release, preserving runtime data and undoing failed copies."""
import fcntl
import os
from pathlib import Path
import shutil
import sys
import tempfile


def apply_release(source, destination):
    if not (source / 'web/app.py').is_file():
        raise ValueError('Incomplete panel archive')
    with (destination / 'data/.update.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with tempfile.TemporaryDirectory(dir=destination) as temporary:
            temporary = Path(temporary)
            changes = []
            directories = []
            try:
                for file in sorted(source.rglob('*')):
                    relative = file.relative_to(source)
                    if relative.parts[0].startswith('.'):
                        continue
                    target = destination / relative
                    if file.is_symlink() or target.is_symlink():
                        raise ValueError('Unexpected symlink: ' + str(relative))
                    if file.is_dir():
                        if not target.exists():
                            target.mkdir()
                            directories.append(target)
                        continue
                    backup = None
                    if target.exists():
                        backup = temporary / str(len(changes))
                        os.link(target, backup)
                    candidate = temporary / 'candidate'
                    shutil.copy2(file, candidate)
                    os.replace(candidate, target)
                    changes.append((target, backup))
            except BaseException:
                for target, backup in reversed(changes):
                    if backup is None:
                        target.unlink()
                    else:
                        os.replace(backup, target)
                for directory in reversed(directories):
                    directory.rmdir()
                raise


if __name__ == '__main__':
    apply_release(Path(sys.argv[1]), Path(sys.argv[2]))
