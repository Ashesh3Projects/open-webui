import { afterEach, expect, test, vi } from 'vitest';
import { writable } from 'svelte/store';

vi.mock('$lib/constants', () => ({ WEBUI_API_BASE_URL: 'https://chat.test/api/v1' }));
vi.mock('$lib/stores', () => ({ config: writable({ features: { enable_tool_servers: true } }) }));

import { uploadToMachine } from './index';

afterEach(() => {
	vi.unstubAllGlobals();
	vi.restoreAllMocks();
});

const target = {
	baseUrl: 'https://chat.test/api/v1/machines/general',
	key: 'webui-token',
	system: true,
	context: { userId: null, chatId: 'chat-a', modelId: null }
};

test('large filesystem uploads reach the machine in bounded parts with their original bytes and chat', async () => {
	const limit = 64 * 1024 * 1024;
	const file = new File([new Uint8Array(limit), 'end'], 'large.csv', { type: 'text/csv' });
	const calls: { url: string; options: RequestInit }[] = [];
	vi.stubGlobal('fetch', async (url: string, options: RequestInit) => {
		calls.push({ url, options });
		if (url.endsWith('/init'))
			return new Response(JSON.stringify({ upload_id: 'session', chunk_size: limit }));
		if (url.includes('/chunk/')) return new Response('{"status":true}');
		return new Response('{"path":"/home/user/large.csv","size":67108867}');
	});
	expect(await uploadToMachine(target, '/home/user', file)).toEqual({
		path: '/home/user/large.csv',
		size: 67108867
	});
	expect(calls.map((c) => c.url)).toEqual([
		'https://chat.test/api/v1/machines/general/files/upload/init',
		'https://chat.test/api/v1/machines/general/files/upload/session/chunk/0',
		'https://chat.test/api/v1/machines/general/files/upload/session/chunk/1',
		'https://chat.test/api/v1/machines/general/files/upload/session/complete'
	]);
	expect(JSON.parse(calls[0].options.body as string)).toMatchObject({
		filename: 'large.csv',
		directory: '/home/user',
		size: 67108867
	});
	for (const c of calls)
		expect(c.options.headers).toMatchObject({
			Authorization: 'Bearer webui-token',
			'X-Session-Id': 'chat-a'
		});
	expect((calls[1].options.body as FormData).get('file')).toHaveProperty('size', limit);
	expect(await ((calls[2].options.body as FormData).get('file') as File).text()).toBe('end');
});

test('a failed machine chunk cancels the staged upload and never completes it', async () => {
	vi.spyOn(console, 'error').mockImplementation(() => {});
	const calls: { url: string; method: string }[] = [];
	vi.stubGlobal('fetch', async (url: string, options: RequestInit) => {
		calls.push({ url, method: options.method! });
		if (url.endsWith('/init')) return new Response('{"upload_id":"session","chunk_size":67108864}');
		return new Response('upstream unavailable', { status: 502 });
	});
	expect(
		await uploadToMachine(target, '/home/user', new File([new Uint8Array(67108865)], 'large.csv'))
	).toBeNull();
	expect(calls).toEqual([
		{ url: 'https://chat.test/api/v1/machines/general/files/upload/init', method: 'POST' },
		{
			url: 'https://chat.test/api/v1/machines/general/files/upload/session/chunk/0',
			method: 'POST'
		},
		{ url: 'https://chat.test/api/v1/machines/general/files/upload/session', method: 'DELETE' }
	]);
});
