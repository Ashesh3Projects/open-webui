import asyncio
import sys
from types import SimpleNamespace

from open_webui.utils.code_artifacts import resolve_code_output_files


def test_published_code_files_use_owned_server_records_and_safe_download_urls(monkeypatch):
    records = {
        'owned': SimpleNamespace(id='owned', user_id='owner', filename='report.pdf', meta={'content_type': 'application/pdf', 'size': 42, 'data': {'generated_by': 'code_interpreter'}}),
        'foreign': SimpleNamespace(id='foreign', user_id='someone-else', filename='secret.pdf', meta={'data': {'generated_by': 'code_interpreter'}}),
        'input': SimpleNamespace(id='input', user_id='owner', filename='input.csv', meta={'data': {'upload_mode': 'raw'}}),
    }

    async def get_file(fid):
        return records.get(fid)

    monkeypatch.setitem(sys.modules, 'open_webui.models.files', SimpleNamespace(Files=SimpleNamespace(get_file_by_id=get_file)))
    result = asyncio.run(resolve_code_output_files([
        {'id': 'owned', 'name': 'spoofed', 'url': 'https://untrusted.invalid/'},
        {'id': 'foreign'}, {'id': 'input'}, {'id': 'owned'}, {'id': 'missing'},
    ], 'owner'))
    assert len(result) == 1
    assert result[0]['name'] == 'report.pdf'
    assert result[0]['url'] == '/api/v1/files/owned/content?attachment=true'
    assert result[0]['path'] == '/api/v1/files/owned/content'
    assert result[0]['generated_by'] == 'code_interpreter'


def test_execute_code_returns_and_emits_the_saved_download_attachment(monkeypatch):
    import ast
    import json
    import logging
    from pathlib import Path

    file = SimpleNamespace(id='owned', user_id='owner', filename='report.pdf', meta={'content_type': 'application/pdf', 'size': 42, 'data': {'generated_by': 'code_interpreter'}})

    async def get_file(fid):
        return file if fid == 'owned' else None

    async def get_user(uid):
        return SimpleNamespace(id=uid)

    async def image(*args, **kwargs):
        return None

    async def config_get(*args):
        return 'pyodide'

    async def run_code(event):
        return {'stdout': 'Saved /mnt/uploads/report.pdf', 'stderr': None, 'result': None, 'files': [{'id': 'owned'}]}

    events = []

    async def emit(event):
        events.append(event)

    monkeypatch.setitem(sys.modules, 'open_webui.models.files', SimpleNamespace(Files=SimpleNamespace(get_file_by_id=get_file)))
    monkeypatch.setitem(sys.modules, 'open_webui.models.users', SimpleNamespace(Users=SimpleNamespace(get_user_by_id=get_user)))
    monkeypatch.setitem(sys.modules, 'open_webui.utils.files', SimpleNamespace(get_image_url_from_base64=image))
    monkeypatch.setitem(sys.modules, 'open_webui.config', SimpleNamespace(CODE_INTERPRETER_BLOCKED_MODULES=[]))
    source = Path(__file__).parents[1] / 'backend/open_webui/tools/builtin.py'
    function = next(n for n in ast.parse(source.read_text(encoding='utf-8')).body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'execute_code')
    for argument in function.args.args:
        argument.annotation = None
    function.returns = None
    namespace = {'Config': SimpleNamespace(get=config_get), 'JSONCodec': json, 'sanitize_code': lambda value: value, 'log': logging.getLogger(__name__)}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), 'exec'), namespace)
    result = json.loads(asyncio.run(namespace['execute_code']('print(1)', __request__=object(), __user__={'id': 'owner'}, __event_call__=run_code, __event_emitter__=emit)))
    assert result['files'][0]['url'] == '/api/v1/files/owned/content?attachment=true'
    assert events == [{'type': 'files', 'data': {'files': result['files']}}]
