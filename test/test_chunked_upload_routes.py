"""Exercise the real upload routes with only authentication and final storage substituted."""

import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace

from fastapi import APIRouter, BackgroundTasks, Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, Field, model_validator
from starlette.datastructures import Headers

from open_webui.utils.chunked_uploads import ChunkedUploadStore


def test_http_upload_preserves_raw_metadata_auth_and_completion_idempotency(tmp_path):
    root = Path(__file__).parents[1]
    namespace = dict(globals())
    model_tree = ast.parse((root / 'backend/open_webui/models/files.py').read_text(encoding='utf-8'))
    models = [n for n in model_tree.body if isinstance(n, ast.ClassDef) and n.name in {'FileMeta', 'FileModelResponse'}]
    exec(compile(ast.Module(body=models, type_ignores=[]), '<file-response-models>', 'exec'), namespace)

    async def verified(authorization: str | None = Header(default=None)):
        if not authorization:
            raise HTTPException(401, 'Authentication required')
        return SimpleNamespace(id=authorization.removeprefix('Bearer '))

    async def session():
        yield None

    class Config:
        @staticmethod
        async def get(key):
            return None

    saved = []

    async def store_file(**kwargs):
        file = kwargs['file']
        saved.append(
            {
                'bytes': file.file.read(),
                'process': kwargs['process'],
                'metadata': kwargs['metadata'],
                'content_type': file.content_type,
            }
        )
        return {
            'id': 'stored-file',
            'user_id': kwargs['user'].id,
            'filename': file.filename,
            'created_at': 1,
            'updated_at': 1,
            'meta': {'size': file.size},
            'data': {},
        }

    router = APIRouter()
    namespace.update(
        router=router,
        CHUNKED_UPLOADS=ChunkedUploadStore(tmp_path, chunk_size=4),
        get_verified_user=verified,
        get_async_session=session,
        AsyncSession=object,
        Config=Config,
        upload_file=store_file,
    )
    tree = ast.parse((root / 'backend/open_webui/routers/files.py').read_text(encoding='utf-8'))
    names = {
        'ChunkedUploadInitForm',
        '_chunk_upload_error',
        'init_chunked_upload',
        'upload_file_chunk',
        'complete_chunked_upload',
        'cancel_chunked_upload',
    }
    nodes = [
        n for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names
    ]
    assert len(nodes) == 6
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<chunk-upload-routes>', 'exec'), namespace)
    app = FastAPI()
    app.include_router(router, prefix='/files')
    client = TestClient(app)
    manifest = {
        'filename': 'data.csv',
        'size': 6,
        'content_type': 'text/csv',
        'process': False,
        'metadata': {'upload_mode': 'raw'},
    }
    assert client.post('/files/upload/init', json=manifest).status_code == 401
    headers = {'Authorization': 'Bearer alice'}
    response = client.post('/files/upload/init', json=manifest, headers=headers)
    assert response.status_code == 200
    uid = response.json()['upload_id']
    base = f'/files/upload/{uid}'
    assert (
        client.post(
            base + '/chunk/0', files={'file': ('part', b'abcd')}, headers={'Authorization': 'Bearer bob'}
        ).status_code
        == 404
    )
    assert client.post(base + '/chunk/0', files={'file': ('part', b'abcd')}, headers=headers).status_code == 200
    assert client.post(base + '/complete', headers=headers).status_code == 400
    assert client.post(base + '/chunk/1', files={'file': ('part', b'ef')}, headers=headers).status_code == 200
    first = client.post(base + '/complete', headers=headers)
    assert first.status_code == 200, first.text
    assert first.json() == client.post(base + '/complete', headers=headers).json()
    assert saved == [
        {'bytes': b'abcdef', 'process': False, 'metadata': {'upload_mode': 'raw'}, 'content_type': 'text/csv'}
    ]
