import { afterEach, expect, test, vi } from 'vitest';

vi.mock('$lib/constants', () => ({ WEBUI_API_BASE_URL: 'https://chat.test/api/v1' }));
vi.mock('$lib/utils', () => ({ splitStream: vi.fn() }));

import { uploadFile } from './index';

afterEach(() => {
	vi.unstubAllGlobals();
	vi.restoreAllMocks();
});

test('raw uploads finish after storage without opening a processing stream', async () => {
	const file = new File(['header\noriginal bytes\n'], 'data.csv', { type: 'text/csv' });
	const uploaded = { id: 'raw-file', data: {}, meta: { size: file.size } };
	const fetch = vi.fn(async (url: string, _options?: RequestInit) =>
		url.includes('/process/status')
			? new Response('Unexpected processing request', { status: 404 })
			: new Response(JSON.stringify(uploaded))
	);
	vi.stubGlobal('fetch', fetch);

	expect(await uploadFile('test-token', file, null, false)).toEqual(uploaded);
	expect(fetch).toHaveBeenCalledTimes(1);
	expect(fetch.mock.calls[0][0]).toBe('https://chat.test/api/v1/files/?process=false');
	const body = fetch.mock.calls[0][1].body as FormData;
	expect(await (body.get('file') as File).text()).toBe('header\noriginal bytes\n');
});

test('large raw uploads use bounded parts and preserve their final bytes', async () => {
	const limit = 64 * 1024 * 1024;
	const bytes = new Uint8Array(limit + 3);
	bytes.set([97, 98, 99], limit);
	const file = new File([bytes], 'large.csv', { type: 'text/csv' });
	const uploaded = { id: 'large-file', data: {}, meta: { size: file.size } };
	const requests: { url: string; options: RequestInit }[] = [];
	vi.stubGlobal('fetch', async (url: string, options: RequestInit) => {
		requests.push({ url, options });
		if (url.endsWith('/upload/init')) {
			return new Response(JSON.stringify({ upload_id: 'session', chunk_size: limit }));
		}
		if (url.includes('/chunk/')) return new Response('{"status":true}');
		return new Response(JSON.stringify(uploaded));
	});
	expect(await uploadFile('test-token', file, { upload_mode: 'raw' }, false)).toEqual(uploaded);
	expect(requests.map((r) => r.url)).toEqual([
		'https://chat.test/api/v1/files/upload/init',
		'https://chat.test/api/v1/files/upload/session/chunk/0',
		'https://chat.test/api/v1/files/upload/session/chunk/1',
		'https://chat.test/api/v1/files/upload/session/complete'
	]);
	expect(JSON.parse(requests[0].options.body as string).process).toBe(false);
	for (const request of requests) {
		expect(request.options.headers).toHaveProperty('authorization', 'Bearer test-token');
	}
	expect((requests[1].options.body as FormData).get('file')).toHaveProperty('size', limit);
	expect(await ((requests[2].options.body as FormData).get('file') as File).text()).toBe('abc');
});

test('HTML proxy errors identify the HTTP error instead of failing JSON parsing', async () => {
	vi.spyOn(console, 'error').mockImplementation(() => {});
	vi.stubGlobal('fetch', async () => new Response('<h1>Payload Too Large</h1>', { status: 413 }));
	await expect(
		uploadFile('test-token', new File(['data'], 'data.csv'), null, false)
	).rejects.toContain('413');
});
