"""Owner-scoped staging for uploads that exceed a proxy's single-request limit."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
import uuid

import psutil

CHUNK_SIZE = 64 * 1024 * 1024
SESSION_TTL = 24 * 3600


class ChunkedUploadStore:
    def __init__(self, root, chunk_size=CHUNK_SIZE):
        self.root = Path(root)
        self.chunk_size = chunk_size

    def _owner(self, owner):
        return self.root / hashlib.sha256(owner.encode()).hexdigest()

    def _directory(self, owner, upload_id):
        identifier = str(uuid.UUID(upload_id))
        directory = self._owner(owner) / identifier
        if directory.is_symlink() or directory.resolve().parent != self._owner(owner).resolve():
            raise ValueError('Invalid upload session')
        return directory

    def _manifest(self, owner, upload_id):
        directory = self._directory(owner, upload_id)
        return json.loads((directory / 'manifest.json').read_text())

    def _active_lock(self, directory):
        lock = directory / '.lock'
        if not lock.exists():
            return False
        try:
            identity = json.loads(lock.read_text())
            return psutil.Process(identity['pid']).create_time() == identity['started_at']
        except psutil.NoSuchProcess:
            return False
        except psutil.AccessDenied:
            return True
        except (ValueError, KeyError, FileNotFoundError):
            return lock.exists() and time.time() - lock.stat().st_mtime < SESSION_TTL

    def _cleanup_owner(self, parent):
        for directory in parent.iterdir():
            try:
                if str(uuid.UUID(directory.name)) != directory.name:
                    continue
                if directory.is_symlink() or directory.resolve().parent != parent.resolve():
                    continue
                if directory.is_dir() and time.time() - directory.stat().st_mtime > SESSION_TTL:
                    if not self._active_lock(directory):
                        shutil.rmtree(directory)
            except (ValueError, FileNotFoundError):
                continue

    def cleanup_all(self):
        if not self.root.exists():
            return
        for parent in self.root.iterdir():
            if parent.is_symlink() or not parent.is_dir() or len(parent.name) != 64:
                continue
            try:
                int(parent.name, 16)
            except ValueError:
                continue
            if parent.resolve().parent == self.root.resolve():
                self._cleanup_owner(parent)

    def create(self, owner, manifest):
        if manifest['size'] <= 0:
            raise ValueError('An upload must contain data')
        parent = self._owner(owner)
        parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._cleanup_owner(parent)
        upload_id = str(uuid.uuid4())
        directory = self._directory(owner, upload_id)
        directory.mkdir(mode=0o700)
        manifest = {**manifest, 'chunk_size': self.chunk_size}
        (directory / 'manifest.json').write_text(json.dumps(manifest))
        return {'upload_id': upload_id, 'chunk_size': self.chunk_size}

    def claim(self, owner, upload_id):
        self._manifest(owner, upload_id)
        lock = self._directory(owner, upload_id) / '.lock'
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            with os.fdopen(descriptor, 'w') as stream:
                json.dump({'pid': os.getpid(), 'started_at': psutil.Process().create_time()}, stream)
            return self._manifest(owner, upload_id)
        except Exception:
            lock.unlink(missing_ok=True)
            raise

    def release(self, owner, upload_id):
        (self._directory(owner, upload_id) / '.lock').unlink(missing_ok=True)

    def write(self, owner, upload_id, index, stream):
        manifest = self.claim(owner, upload_id)
        temporary = None
        try:
            if 'result' in manifest:
                raise ValueError('Upload is already complete')
            chunk_size, size = manifest['chunk_size'], manifest['size']
            count = (size + chunk_size - 1) // chunk_size
            if not 0 <= index < count:
                raise ValueError('Invalid chunk index')
            expected = min(chunk_size, size - index * chunk_size)
            directory = self._directory(owner, upload_id)
            temporary = directory / f'{index}.{uuid.uuid4().hex}.tmp'
            written = 0
            with temporary.open('xb') as destination:
                while data := stream.read(1024 * 1024):
                    written += len(data)
                    if written > expected:
                        raise ValueError('Incorrect chunk size')
                    destination.write(data)
            if written != expected:
                raise ValueError('Incorrect chunk size')
            temporary.replace(directory / f'{index}.part')
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            self.release(owner, upload_id)

    def assemble(self, owner, upload_id):
        manifest = self._manifest(owner, upload_id)
        directory = self._directory(owner, upload_id)
        size, chunk_size = manifest['size'], manifest['chunk_size']
        result = tempfile.TemporaryFile(dir=directory)
        try:
            for index in range((size + chunk_size - 1) // chunk_size):
                part = directory / f'{index}.part'
                expected = min(chunk_size, size - index * chunk_size)
                if not part.is_file() or part.stat().st_size != expected:
                    raise ValueError('Upload is missing a complete chunk')
                with part.open('rb') as source:
                    shutil.copyfileobj(source, result, 1024 * 1024)
            result.seek(0)
            return result
        except Exception:
            result.close()
            raise

    def complete(self, owner, upload_id, result):
        directory = self._directory(owner, upload_id)
        manifest = {**self._manifest(owner, upload_id), 'result': result}
        temporary = directory / 'manifest-result.tmp'
        temporary.write_text(json.dumps(manifest))
        temporary.replace(directory / 'manifest.json')
        for part in directory.glob('*.part'):
            part.unlink()

    def cancel(self, owner, upload_id):
        manifest = self.claim(owner, upload_id)
        if 'result' in manifest:
            self.release(owner, upload_id)
            return
        shutil.rmtree(self._directory(owner, upload_id))
