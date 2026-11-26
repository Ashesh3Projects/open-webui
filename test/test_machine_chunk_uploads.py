"""Run the actual proxy entry point and disk staging, substituting only auth and the remote machine."""
import ast
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
import pytest

from open_webui.utils.chunked_uploads import ChunkedUploadStore


@pytest.fixture
def machine_client(tmp_path, monkeypatch):
    monkeypatch.setenv('WEBUI_SECRET_KEY', 'test-only-machine-upload-secret-key')
    monkeypatch.setenv('DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.setenv('STATIC_DIR', str(tmp_path / 'static'))
    monkeypatch.setenv('FRONTEND_BUILD_DIR', str(tmp_path / 'frontend'))
    monkeypatch.setenv('ENABLE_DB_MIGRATIONS', 'False')
    allowed = {'general', 'other'}
    received = []

    async def verified(authorization: str | None = Header(default=None)):
        if not authorization:
            raise HTTPException(401)
        return SimpleNamespace(id=authorization.removeprefix('Bearer '))

    async def find(user, server_id, context, **kwargs):
        return {'url': 'http://terminal:8000'} if server_id in allowed else None

    async def forward(server_id, path, request, user, *, context, upload=None):
        if upload is None:
            return JSONResponse({'unexpected_direct_upload': path})
        received.append((upload['file'].read(), upload['directory'], context.copy()))
        return JSONResponse({'path': '/home/user/data.csv', 'size': 6})

    async def chunks(*args, **kwargs):
        from open_webui.utils import machine_uploads
        monkeypatch.setattr(machine_uploads, 'MACHINE_UPLOADS', ChunkedUploadStore(tmp_path, chunk_size=4))
        from open_webui.models.config import Config
        async def config_get(*args): return client.rag_limit
        monkeypatch.setattr(Config, 'get', config_get)
        return await machine_uploads.handle_machine_upload(*args, **kwargs)

    namespace = dict(globals(), router=APIRouter(), PROXY_METHODS=['GET','POST','DELETE'],
                     get_verified_user=verified, _proxy_machine=forward, ENABLE_TOOL_SERVERS=True,
                     find_machine_connection=find, get_machine_url=lambda c: c['url'], handle_machine_upload=chunks)
    source = Path(__file__).parents[1] / 'backend/open_webui/routers/machines.py'
    node = next(n for n in ast.parse(source.read_text(encoding='utf-8')).body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'proxy_machine')
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), namespace)
    app = FastAPI(); app.include_router(namespace['router'], prefix='/machines')
    client = TestClient(app)
    client.rag_limit = None
    return client, received, allowed


def test_machine_chunks_preserve_bytes_and_bind_owner_machine_and_chat(machine_client):
    client, received, _ = machine_client
    headers = {'Authorization': 'Bearer alice', 'X-Session-Id': 'chat-a'}
    form = {'filename':'data.csv', 'size':6, 'content_type':'text/csv', 'directory':'/home/user'}
    assert client.post('/machines/general/files/upload/init', json=form).status_code == 401
    r = client.post('/machines/general/files/upload/init', json=form, headers=headers)
    assert 'upload_id' in r.json()
    base = '/machines/general/files/upload/' + r.json()['upload_id']
    part = {'file':('data.csv', b'abcd')}
    assert client.post(base+'/chunk/0', files=part, headers={**headers,'Authorization':'Bearer bob'}).status_code == 404
    assert client.post(base+'/chunk/0', files=part, headers={**headers,'X-Session-Id':'chat-b'}).status_code == 404
    assert client.post(base.replace('/general/','/other/')+'/chunk/0', files=part, headers=headers).status_code == 404
    assert client.post(base+'/chunk/0', files=part, headers=headers).status_code == 200
    assert client.post(base+'/complete', headers=headers).status_code == 400
    assert client.post(base+'/chunk/1', files={'file':('data.csv', b'ef')}, headers=headers).status_code == 200
    r = client.post(base+'/complete', headers=headers)
    assert r.json() == {'path':'/home/user/data.csv', 'size':6}
    assert client.post(base+'/complete', headers=headers).json() == r.json()
    assert received == [(b'abcdef','/home/user',{'instance_user_id':None,'chat_id':'chat-a','model_id':None})]


def test_machine_access_is_rechecked_and_cancel_discards_staged_parts(machine_client):
    client, received, allowed = machine_client
    headers = {'Authorization':'Bearer alice'}
    r = client.post('/machines/general/files/upload/init', json={'filename':'data.csv','size':6,'directory':'/home/user'}, headers=headers)
    assert 'upload_id' in r.json()
    base = '/machines/general/files/upload/' + r.json()['upload_id']
    allowed.remove('general')
    assert client.post(base+'/chunk/0', files={'file':('p',b'abcd')}, headers=headers).status_code == 404
    allowed.add('general')
    assert client.post(base+'/chunk/0', files={'file':('p',b'abcd')}, headers=headers).status_code == 200
    assert client.delete(base, headers=headers).status_code == 200
    assert client.post(base+'/complete', headers=headers).status_code == 404
    assert received == []


def test_machine_filesystem_upload_is_independent_of_rag_size_limit(machine_client):
    client, _, _ = machine_client
    client.rag_limit = 1
    r = client.post('/machines/general/files/upload/init',
                    json={'filename':'large.csv','size':67108865,'directory':'/home/user'},
                    headers={'Authorization':'Bearer alice'})
    assert r.status_code == 200
    assert 'upload_id' in r.json()
