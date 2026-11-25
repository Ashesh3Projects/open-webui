from urllib.parse import quote


async def resolve_code_output_files(candidates, user_id):
    """Resolve client-reported artifacts using their owned, authoritative file records."""
    from open_webui.models.files import Files

    if not isinstance(user_id, str) or not user_id:
        return []
    result = []
    seen = set()
    for candidate in candidates or []:
        if not isinstance(candidate, dict) or not isinstance(candidate.get('id'), str):
            continue
        file_id = candidate['id']
        if file_id in seen:
            continue
        seen.add(file_id)
        file = await Files.get_file_by_id(file_id)
        if not file or file.user_id != user_id:
            continue
        meta = file.meta or {}
        data = meta.get('data') or {}
        if not isinstance(data, dict) or data.get('generated_by') != 'code_interpreter':
            continue
        path = f'/api/v1/files/{quote(file.id, safe="")}/content'
        result.append({
            'type': 'file', 'id': file.id, 'name': file.filename,
            'source': 'open_webui', 'generated_by': 'code_interpreter', 'context': 'raw',
            'path': path, 'url': path + '?attachment=true',
            'content_type': meta.get('content_type') or 'application/octet-stream',
            'size': meta.get('size'),
        })
    return result
