"""Stage bounded browser uploads, then stream the original file to an authorized machine."""
import asyncio
import json
from pathlib import Path
import re

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

from open_webui.config import UPLOAD_DIR
from open_webui.utils.chunked_uploads import ChunkedUploadStore

MACHINE_UPLOADS = ChunkedUploadStore(Path(UPLOAD_DIR) / '.machine-chunks')


class MachineUploadInitForm(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    size: int = Field(gt=0)
    content_type: str = Field(default='application/octet-stream', max_length=255, pattern=r'^[^\r\n]+$')
    directory: str = Field(min_length=1, max_length=4096)


async def handle_machine_upload(server_id, path, request, user, *, context, forward):
    # Caller checks current machine access on every request; the manifest also prevents rebinding.
    target = {'server_id': server_id, **context}
    if path == 'files/upload/init' and request.method == 'POST':
        try:
            form = MachineUploadInitForm.model_validate(await request.json())
        except (ValidationError, ValueError) as error:
            raise HTTPException(400, 'Invalid machine upload metadata') from error
        return await asyncio.to_thread(MACHINE_UPLOADS.create, user.id, {**form.model_dump(), 'target': target})

    match = re.fullmatch(r'files/upload/([0-9a-f-]{36})(?:/(complete|chunk/(\d+)))?', path)
    if not match:
        raise HTTPException(404, 'Upload session not found')
    upload_id, action, index = match.groups()
    claimed, assembled = False, None
    try:
        manifest = await asyncio.to_thread(MACHINE_UPLOADS._manifest, user.id, upload_id)
        if manifest.get('target') != target:
            raise HTTPException(404, 'Upload session not found')
        if index is not None and request.method == 'POST':
            async with request.form(max_files=1, max_fields=0, max_part_size=MACHINE_UPLOADS.chunk_size + 1024) as form:
                file = form.get('file')
                if not hasattr(file, 'file'):
                    raise HTTPException(400, 'Missing upload chunk')
                await asyncio.to_thread(MACHINE_UPLOADS.write, user.id, upload_id, int(index), file.file)
            return {'status': True}
        if action == 'complete' and request.method == 'POST':
            manifest = await asyncio.to_thread(MACHINE_UPLOADS.claim, user.id, upload_id)
            claimed = True
            if 'result' in manifest:
                return JSONResponse(**manifest['result'])
            assembled = await asyncio.to_thread(MACHINE_UPLOADS.assemble, user.id, upload_id)
            response = await forward(server_id, 'files/upload', request, user, context=context,
                                     upload={**manifest, 'file': assembled})
            if response.status_code < 300:
                result = {'content': json.loads(response.body), 'status_code': response.status_code}
                await asyncio.to_thread(MACHINE_UPLOADS.complete, user.id, upload_id, result)
            return response
        if action is None and request.method == 'DELETE':
            await asyncio.to_thread(MACHINE_UPLOADS.cancel, user.id, upload_id)
            return {'status': True}
        raise HTTPException(405, 'Method not allowed')
    except (ValueError, FileNotFoundError, FileExistsError) as error:
        status = 404 if isinstance(error, FileNotFoundError) else 409 if isinstance(error, FileExistsError) else 400
        raise HTTPException(status, 'Upload session not found' if status == 404 else str(error)) from error
    finally:
        if assembled is not None:
            assembled.close()
        if claimed:
            await asyncio.to_thread(MACHINE_UPLOADS.release, user.id, upload_id)
