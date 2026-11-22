import io
import json
import os
import time

import pytest

from open_webui.utils.chunked_uploads import ChunkedUploadStore


def test_reassembles_original_bytes_and_caches_completion(tmp_path):
    store = ChunkedUploadStore(tmp_path, chunk_size=4)
    upload = store.create('alice', {'filename': 'data.csv', 'size': 10, 'process': False})
    uid = upload['upload_id']
    store.write('alice', uid, 0, io.BytesIO(b'abcd'))
    store.write('alice', uid, 1, io.BytesIO(b'efgh'))
    store.write('alice', uid, 2, io.BytesIO(b'ij'))
    manifest = store.claim('alice', uid)
    assert manifest['process'] is False
    with store.assemble('alice', uid) as stream:
        assert stream.read() == b'abcdefghij'
    store.complete('alice', uid, {'id': 'stored-file', 'data': {}})
    store.release('alice', uid)
    assert store.claim('alice', uid)['result'] == {'id': 'stored-file', 'data': {}}
    store.release('alice', uid)
    assert not list(tmp_path.rglob('*.part'))


def test_enforces_owner_and_chunk_boundaries(tmp_path):
    store = ChunkedUploadStore(tmp_path, chunk_size=4)
    uid = store.create('alice', {'filename': 'data.csv', 'size': 6})['upload_id']
    with pytest.raises(FileNotFoundError):
        store.write('bob', uid, 0, io.BytesIO(b'abcd'))
    for index, content in [(-1, b'abcd'), (2, b'abcd'), (0, b'abc'), (0, b'abcde'), (1, b'xyz')]:
        with pytest.raises(ValueError):
            store.write('alice', uid, index, io.BytesIO(content))
    assert not list(tmp_path.rglob('*.part'))


def test_missing_chunks_cannot_finalize_and_finalizers_are_exclusive(tmp_path):
    store = ChunkedUploadStore(tmp_path, chunk_size=4)
    uid = store.create('alice', {'filename': 'data.csv', 'size': 6})['upload_id']
    store.write('alice', uid, 0, io.BytesIO(b'abcd'))
    store.claim('alice', uid)
    with pytest.raises(FileExistsError):
        store.claim('alice', uid)
    with pytest.raises(ValueError):
        store.assemble('alice', uid)
    store.release('alice', uid)
    store.write('alice', uid, 1, io.BytesIO(b'ef'))
    with store.assemble('alice', uid) as stream:
        assert stream.read() == b'abcdef'


@pytest.mark.parametrize('upload_id', ['../outside', '/tmp/outside', 'not-a-uuid'])
def test_rejects_path_traversal(tmp_path, upload_id):
    store = ChunkedUploadStore(tmp_path, chunk_size=4)
    with pytest.raises(ValueError):
        store.claim('alice', upload_id)


def test_abandoned_uploads_expire_and_cancel_respects_finalization(tmp_path):
    store = ChunkedUploadStore(tmp_path, chunk_size=4)
    uid = store.create('alice', {'filename': 'data.csv', 'size': 4})['upload_id']
    store.claim('alice', uid)
    with pytest.raises(FileExistsError):
        store.cancel('alice', uid)
    store.release('alice', uid)
    directory = next(tmp_path.rglob('manifest.json')).parent
    os.utime(directory, (time.time() - 90000, time.time() - 90000))
    store.create('alice', {'filename': 'new.csv', 'size': 4})
    assert not directory.exists()


def test_global_cleanup_preserves_live_locks_and_reclaims_crashed_sessions(tmp_path):
    store = ChunkedUploadStore(tmp_path, chunk_size=4)
    alice = store.create('alice', {'filename': 'data.csv', 'size': 4})['upload_id']
    store.claim('alice', alice)
    directory = next(tmp_path.rglob('manifest.json')).parent
    old = time.time() - 90000
    os.utime(directory, (old, old))
    store.create('bob', {'filename': 'fresh.csv', 'size': 4})
    store.cleanup_all()
    assert directory.exists()
    (directory / '.lock').write_text(json.dumps({'pid': 999999999, 'started_at': 0}))
    os.utime(directory, (old, old))
    store.cleanup_all()
    assert not directory.exists()
    assert len(list(tmp_path.rglob('manifest.json'))) == 1
