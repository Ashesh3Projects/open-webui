import { afterEach, expect, test, vi } from 'vitest';

vi.mock('$lib/constants', () => ({ WEBUI_API_BASE_URL: 'https://chat.test/api/v1' }));
vi.mock('$lib/utils', () => ({ splitStream: vi.fn() }));

import { uploadFile } from './index';

afterEach(() => vi.unstubAllGlobals());

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
