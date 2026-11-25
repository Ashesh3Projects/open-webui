export type GeneratedPythonFile = { path: string; name: string; data: ArrayBuffer };

type PythonFS = {
	readdir(path: string): string[];
	lstat(path: string): { mode: number; size: number; mtime: Date | number };
	isDir(mode: number): boolean;
	isFile(mode: number): boolean;
	readFile(path: string): Uint8Array;
};

// Keep this factory self-contained: the opaque iframe embeds its compiled source.
export function createGeneratedFileTracker(fs: PythonFS, root = '/mnt/uploads') {
	function snapshot() {
		const entries = new Map<string, string>();
		function visit(directory: string) {
			let names: string[];
			try {
				names = fs.readdir(directory).sort();
			} catch {
				return;
			}
			for (const name of names) {
				if (name.startsWith('.') || name === '__pycache__') continue;
				const path = `${directory}/${name}`;
				const stat = fs.lstat(path);
				if (fs.isDir(stat.mode)) visit(path);
				else if (fs.isFile(stat.mode)) {
					entries.set(path, `${stat.size}:${Number(stat.mtime)}`);
				}
			}
		}
		visit(root);
		return entries;
	}
	function collect(before: Map<string, string>): GeneratedPythonFile[] {
		const outputs: GeneratedPythonFile[] = [];
		for (const [path, signature] of snapshot()) {
			if (before.get(path) === signature) continue;
			const bytes = fs.readFile(path);
			const data = new ArrayBuffer(bytes.byteLength);
			new Uint8Array(data).set(bytes);
			outputs.push({ path, name: path.split('/').pop()!, data });
		}
		return outputs;
	}
	return { snapshot, collect };
}
