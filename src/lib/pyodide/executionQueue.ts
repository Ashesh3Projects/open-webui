// Self-contained so the opaque iframe can embed the same queue implementation.
export function createPythonMessageQueue() {
	let pending = Promise.resolve();
	return function enqueue<T>(job: () => Promise<T>): Promise<T> {
		const result = pending.then(job);
		pending = result.then(
			() => undefined,
			() => undefined
		);
		return result;
	};
}
