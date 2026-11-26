export const UPLOAD_PART_SIZE = 64 * 1024 * 1024;

export const readUploadResponse = async (response: Response) => {
	if (!response.ok) {
		throw await response.json().catch(() => ({
			detail: `Upload failed (HTTP ${response.status})`
		}));
	}
	return response.json();
};

export const uploadFileInParts = async (
	base: string,
	headers: Record<string, string>,
	file: File,
	manifest: Record<string, unknown>,
	signal?: AbortSignal
) => {
	const session = await fetch(`${base}/init`, {
		method: 'POST',
		signal,
		headers: { ...headers, 'Content-Type': 'application/json' },
		body: JSON.stringify({
			...manifest,
			filename: file.name,
			size: file.size,
			content_type: file.type || 'application/octet-stream'
		})
	}).then(readUploadResponse);
	try {
		const partSize = session.chunk_size;
		if (!Number.isInteger(partSize) || partSize <= 0 || partSize > UPLOAD_PART_SIZE) {
			throw new Error('Invalid upload part size');
		}
		for (let offset = 0, index = 0; offset < file.size; offset += partSize, index++) {
			const body = new FormData();
			body.append('file', file.slice(offset, offset + partSize), file.name);
			await fetch(`${base}/${session.upload_id}/chunk/${index}`, {
				method: 'POST',
				signal,
				headers,
				body
			}).then(readUploadResponse);
		}
		return await fetch(`${base}/${session.upload_id}/complete`, {
			method: 'POST',
			headers,
			signal
		}).then(readUploadResponse);
	} catch (error) {
		await fetch(`${base}/${session.upload_id}`, {
			method: 'DELETE',
			headers,
			signal: AbortSignal.timeout(5000)
		}).catch(() => null);
		throw error;
	}
};
