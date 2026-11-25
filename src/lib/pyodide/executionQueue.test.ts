import { expect, test } from 'vitest';
import { createPythonMessageQueue } from './executionQueue';

test('keeps overlapping Python jobs and filesystem operations in their own execution', async () => {
	const enqueue = createPythonMessageQueue();
	const files: string[] = [];
	let release!: () => void;
	const gate = new Promise<void>((resolve) => (release = resolve));
	const first = enqueue(async () => {
		const before = [...files];
		await gate;
		files.push('chat-a.pdf');
		return files.filter((name) => !before.includes(name));
	});
	const second = enqueue(async () => {
		const before = [...files];
		files.push('chat-b.pdf');
		return files.filter((name) => !before.includes(name));
	});
	await Promise.resolve();
	expect(files).toEqual([]);
	release();
	expect(await first).toEqual(['chat-a.pdf']);
	expect(await second).toEqual(['chat-b.pdf']);
});

test('a failed job does not prevent later jobs and the queue can be embedded in the iframe', async () => {
	const make = new Function(`return (${createPythonMessageQueue.toString()})`)();
	const enqueue = make();
	await expect(
		enqueue(async () => {
			throw new Error('failed');
		})
	).rejects.toThrow('failed');
	expect(await enqueue(async () => 'next')).toBe('next');
});
