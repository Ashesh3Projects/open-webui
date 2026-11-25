import { uploadFile } from '$lib/apis/files';
import type { GeneratedPythonFile } from './generatedFiles';

export async function publishGeneratedFiles(
	token: string,
	outputs: GeneratedPythonFile[],
	timeoutMs = 120000
) {
	const files: { id: string }[] = [];
	const file_errors: string[] = [];
	const controller = new AbortController();
	const deadline = setTimeout(() => controller.abort(), timeoutMs);
	const mimeTypes: Record<string, string> = {
		pdf: 'application/pdf',
		txt: 'text/plain',
		csv: 'text/csv',
		json: 'application/json',
		png: 'image/png',
		jpg: 'image/jpeg',
		jpeg: 'image/jpeg',
		svg: 'image/svg+xml',
		docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
		xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
		pptx: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
		zip: 'application/zip',
		html: 'text/html'
	};
	try {
		for (const output of outputs) {
			try {
				if (controller.signal.aborted) throw new Error('Output publication timed out');
				if (!output.path.startsWith('/mnt/uploads/') || output.path.split('/').includes('..')) {
					throw new Error('Invalid output path');
				}
				const name = output.path.split('/').pop();
				if (!name) throw new Error('Missing output filename');
				const type =
					mimeTypes[name.split('.').pop()?.toLowerCase() ?? ''] || 'application/octet-stream';
				const file = new File([output.data], name, { type });
				const stored = await uploadFile(
					token,
					file,
					{ upload_mode: 'raw', generated_by: 'code_interpreter' },
					false,
					false,
					undefined,
					controller.signal
				);
				if (!stored?.id) throw new Error('The output was not saved');
				files.push({ id: stored.id });
			} catch (error) {
				file_errors.push(
					`${output.name}: ${controller.signal.aborted ? 'Output publication timed out' : error instanceof Error ? error.message : String(error)}`
				);
			}
		}
	} finally {
		clearTimeout(deadline);
	}
	return { files, file_errors };
}
