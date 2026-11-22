export const getChatFileUploadOptions = (
	process: boolean,
	contentType: string,
	python: {
		available: boolean;
		engine?: string;
		modelMetadata: {
			capabilities?: { builtin_tools?: boolean };
			builtinTools?: { code_interpreter?: boolean };
		}[];
	}
): { process: boolean; context?: 'raw'; enablePython: boolean } => {
	if (
		process &&
		python.available &&
		python.engine === 'pyodide' &&
		python.modelMetadata.every(
			(meta) =>
				(meta.capabilities?.builtin_tools ?? true) && (meta.builtinTools?.code_interpreter ?? true)
		) &&
		!contentType.startsWith('audio/') &&
		!contentType.startsWith('video/')
	) {
		return { process: false, context: 'raw', enablePython: true };
	}
	return { process, enablePython: false };
};
