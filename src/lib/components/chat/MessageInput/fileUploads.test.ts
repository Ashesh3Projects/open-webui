import { describe, expect, test } from 'vitest';
import { getChatFileUploadOptions } from './fileUploads';

const python = { available: true, engine: 'pyodide', modelMetadata: [{}] };

describe('chat document uploads', () => {
	test('makes CSV attachments raw and enables Python even when full context was the default', () => {
		expect(getChatFileUploadOptions(true, 'text/csv', python)).toEqual({
			process: false,
			context: 'raw',
			enablePython: true
		});
	});

	test.each(['audio/mpeg', 'video/mp4'])('preserves media processing for %s', (contentType) => {
		expect(getChatFileUploadOptions(true, contentType, python)).toEqual({
			process: true,
			enablePython: false
		});
	});

	test('does not enable Python when the user or selected model cannot use it', () => {
		expect(getChatFileUploadOptions(true, 'text/csv', { ...python, available: false })).toEqual({
			process: true,
			enablePython: false
		});
	});

	test('preserves explicit unprocessed image uploads', () => {
		expect(getChatFileUploadOptions(false, 'image/png', python)).toEqual({
			process: false,
			enablePython: false
		});
	});

	test.each([
		{ ...python, engine: 'jupyter' },
		{ ...python, modelMetadata: [{ builtinTools: { code_interpreter: false } }] },
		{ ...python, modelMetadata: [{ capabilities: { builtin_tools: false } }] }
	])('keeps processing when browser execution is unavailable: %j', (options) => {
		expect(getChatFileUploadOptions(true, 'text/csv', options)).toEqual({
			process: true,
			enablePython: false
		});
	});
});
