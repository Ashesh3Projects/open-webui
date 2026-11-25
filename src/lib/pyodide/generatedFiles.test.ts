import { expect, test, vi } from 'vitest';
import { createGeneratedFileTracker } from './generatedFiles';

const fakeFS = () => {
	const files = new Map<string, { bytes: Uint8Array; mtime: number; mode: number }>();
	const fs = {
		readdir: (path: string) => [
			'.',
			'..',
			...new Set(
				[...files.keys()]
					.filter((p) => p.startsWith(path + '/'))
					.map((p) => p.slice(path.length + 1).split('/')[0])
			)
		],
		lstat: (path: string) =>
			files.has(path)
				? { ...files.get(path)!, size: files.get(path)!.bytes.length }
				: { size: 0, mtime: 0, mode: 0o40000 },
		isDir: (mode: number) => mode === 0o40000,
		isFile: (mode: number) => mode === 0o100000,
		readFile: vi.fn((path: string) => files.get(path)!.bytes)
	};
	const write = (path: string, value: string, mtime = 1, mode = 0o100000) =>
		files.set(path, { bytes: new TextEncoder().encode(value), mtime, mode });
	return { fs, write };
};

test('captures new and overwritten outputs without reading unchanged uploaded inputs', () => {
	const { fs, write } = fakeFS();
	write('/mnt/uploads/input.csv', 'large input');
	write('/mnt/uploads/old.txt', 'old', 1);
	const tracker = createGeneratedFileTracker(fs);
	const before = tracker.snapshot();
	write('/mnt/uploads/reports/playbook.pdf', '%PDF-output', 2);
	write('/mnt/uploads/old.txt', 'new', 2);
	write('/mnt/uploads/link', 'outside', 2, 0o120000);
	write('/mnt/uploads/__pycache__/module.pyc', 'cache', 2);
	write('/mnt/uploads/.temporary', 'hidden', 2);
	const outputs = tracker.collect(before);
	expect(outputs.map((f) => f.path)).toEqual([
		'/mnt/uploads/old.txt',
		'/mnt/uploads/reports/playbook.pdf'
	]);
	expect(new TextDecoder().decode(outputs[1].data)).toBe('%PDF-output');
	expect(fs.readFile).not.toHaveBeenCalledWith('/mnt/uploads/input.csv');
	expect(fs.readFile).not.toHaveBeenCalledWith('/mnt/uploads/link');
});

test('the tracker is self-contained when embedded into the opaque Python iframe', () => {
	const { fs, write } = fakeFS();
	const factory = new Function(`return (${createGeneratedFileTracker.toString()})`)();
	const tracker = factory(fs);
	const before = tracker.snapshot();
	write('/mnt/uploads/result.csv', 'a,b\n1,2\n');
	expect(tracker.collect(before)[0].name).toBe('result.csv');
});
