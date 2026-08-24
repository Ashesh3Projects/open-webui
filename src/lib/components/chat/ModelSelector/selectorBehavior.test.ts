import { describe, expect, test } from 'vitest';

import { shouldAutoFocusModelSearch } from './selectorBehavior';

describe('shouldAutoFocusModelSearch', () => {
	test('does not focus for pointer opens but preserves keyboard navigation', () => {
		expect(shouldAutoFocusModelSearch('pointer')).toBe(false);
		expect(shouldAutoFocusModelSearch('keyboard')).toBe(true);
	});
});
