import { afterEach, expect, test, vi } from 'vitest';

vi.mock('$lib/apis/files', () => ({ uploadFile: vi.fn() }));
import { uploadFile } from '$lib/apis/files';
import { publishGeneratedFiles } from './publishGeneratedFiles';

afterEach(() => {
	vi.resetAllMocks();
	vi.useRealTimers();
});

test('publishes the original output bytes as unprocessed files and returns only saved IDs', async () => {
	vi.mocked(uploadFile).mockImplementation(async (_token, file, metadata, process, stream) => {
		expect(process).toBe(false);
		expect(stream).toBe(false);
		expect(metadata).toMatchObject({ upload_mode: 'raw', generated_by: 'code_interpreter' });
		expect(file.name).toBe('playbook.pdf');
		expect(file.type).toBe('application/pdf');
		expect([...new Uint8Array(await file.arrayBuffer())]).toEqual([37, 80, 68, 70, 0, 255]);
		return {
			id: 'saved-pdf',
			user_id: 'owner',
			filename: file.name,
			data: {},
			meta: { name: file.name, size: 6, content_type: file.type },
			created_at: 1,
			updated_at: 1
		};
	});
	const bytes = new Uint8Array([37, 80, 68, 70, 0, 255]).buffer;
	const result = await publishGeneratedFiles('token', [
		{ path: '/mnt/uploads/playbook.pdf', name: 'playbook.pdf', data: bytes }
	]);
	expect(result.files).toEqual([{ id: 'saved-pdf' }]);
	expect(result.file_errors).toEqual([]);
});

test('reports publication failure without inventing a downloadable file', async () => {
	vi.mocked(uploadFile).mockRejectedValue(new Error('Upload failed'));
	const result = await publishGeneratedFiles('token', [
		{ path: '/mnt/uploads/report.pdf', name: 'report.pdf', data: new ArrayBuffer(4) }
	]);
	expect(result.files).toEqual([]);
	expect(result.file_errors[0]).toContain('report.pdf');
});

test('aborts a stalled publication and returns an explicit file error', async () => {
	vi.useFakeTimers();
	vi.mocked(uploadFile).mockImplementation(
		async (_token, _file, _metadata, _process, _stream, _uploaded, signal) =>
			new Promise((_resolve, reject) =>
				signal!.addEventListener('abort', () => reject(new Error('aborted')))
			)
	);
	const result = publishGeneratedFiles(
		'token',
		[{ path: '/mnt/uploads/report.pdf', name: 'report.pdf', data: new ArrayBuffer(4) }],
		1000
	);
	await vi.advanceTimersByTimeAsync(1000);
	expect((await result).files).toEqual([]);
	expect((await result).file_errors[0]).toContain('timed out');
});
