import { describe, expect, it } from 'vitest';

import { APP_NAME, formatNotificationTitle } from './constants';

describe('application branding', () => {
	it('uses ChatGPT as the frontend fallback name', () => {
		expect(APP_NAME).toBe('ChatGPT');
	});

	it('uses the active instance name in browser notification titles', () => {
		expect(formatNotificationTitle('Task complete', 'My Workspace')).toBe(
			'Task complete / My Workspace'
		);
	});
});
