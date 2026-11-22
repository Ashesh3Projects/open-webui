"""Exercise the real retrieval handler without importing the application or its database."""

import ast
import asyncio
from pathlib import Path
import pytest


@pytest.mark.parametrize('attachment', [
    {'type': 'file', 'id': 'raw-file', 'context': 'raw'},
    {'type': 'file', 'id': 'raw-file', 'context': 'full', 'file': {'meta': {'data': {'upload_mode': 'raw'}}}},
])
def test_raw_attachments_never_generate_retrieval_queries_or_sources(attachment):
    path = Path(__file__).parents[1] / 'backend/open_webui/utils/middleware.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    handler = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'chat_completion_files_handler')
    handler.returns = None
    for arg in handler.args.args:
        arg.annotation = None

    async def unexpected_event(event):
        raise AssertionError('Raw files must not start retrieval: ' + str(event))

    namespace = {}
    exec(compile(ast.Module(body=[handler], type_ignores=[]), str(path), 'exec'), namespace)
    body = {'metadata': {'files': [attachment]}}
    result, flags = asyncio.run(namespace[handler.name](None, body, {'__event_emitter__': unexpected_event}, None))
    assert result is body
    assert flags == {'sources': []}
