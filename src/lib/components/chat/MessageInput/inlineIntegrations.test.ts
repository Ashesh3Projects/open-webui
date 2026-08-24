import { describe, expect, test } from 'vitest';

import {
	canApplyReasoningEffortUpdate,
	canCacheReasoningEffortLoad,
	findReasoningEffortFilter,
	getReasoningEffortValve,
	getIntegrationPresentation,
	shouldShowIntegrationsMenu,
	setFilterEnabled
} from './inlineIntegrations';

describe('findReasoningEffortFilter', () => {
	test('extracts the reasoning filter without hiding other toggle filters', () => {
		const filters = [
			{ id: 'citation_filter', name: 'Citations' },
			{ id: 'reason_filter', name: 'Reasoning Effort', has_user_valves: true }
		];

		expect(findReasoningEffortFilter(filters)).toEqual(filters[1]);
		expect(filters).toHaveLength(2);
	});

	test('recognizes a renamed function by its user-facing title when it exposes user valves', () => {
		expect(
			findReasoningEffortFilter([
				{ id: 'custom_reasoning', name: 'Reasoning Effort', has_user_valves: true }
			])?.id
		).toBe('custom_reasoning');
	});

	test('does not pin an unrelated filter that only reuses the same display name', () => {
		expect(
			findReasoningEffortFilter([{ id: 'custom_reasoning', name: 'Reasoning Effort' }])
		).toBeUndefined();
	});
});

describe('getReasoningEffortValve', () => {
	test('uses the REASONING_EFFORT select schema and preserves option order', () => {
		const spec = {
			properties: {
				REASONING_EFFORT: {
					title: 'Reasoning Effort',
					default: 'not set',
					input: {
						type: 'select',
						options: [
							{ value: 'not set', label: "Model default (don't send)" },
							{ value: 'low', label: 'low' },
							{ value: 'xhigh', label: 'xhigh' }
						]
					}
				}
			}
		};

		expect(getReasoningEffortValve(spec)).toEqual({
			key: 'REASONING_EFFORT',
			defaultValue: 'not set',
			options: [
				{ value: 'not set', label: 'Model default' },
				{ value: 'low', label: 'Low' },
				{ value: 'xhigh', label: 'Extra High' }
			]
		});
	});

	test('returns null for an unrelated valve schema', () => {
		expect(
			getReasoningEffortValve({
				properties: {
					API_KEY: { title: 'API Key', type: 'string' }
				}
			})
		).toBeNull();
	});
});

describe('setFilterEnabled', () => {
	test('adds a filter only once and removes every stale duplicate', () => {
		expect(setFilterEnabled(['other'], 'reason_filter', true)).toEqual(['other', 'reason_filter']);
		expect(
			setFilterEnabled(['reason_filter', 'other', 'reason_filter'], 'reason_filter', true)
		).toEqual(['reason_filter', 'other']);
		expect(
			setFilterEnabled(['reason_filter', 'other', 'reason_filter'], 'reason_filter', false)
		).toEqual(['other']);
	});
});

describe('canApplyReasoningEffortUpdate', () => {
	test('requires a persisted response for the filter that is still active', () => {
		expect(canApplyReasoningEffortUpdate(null, 'reason_filter', 'reason_filter')).toBe(false);
		expect(
			canApplyReasoningEffortUpdate({ REASONING_EFFORT: 'high' }, 'reason_filter', 'another_filter')
		).toBe(false);
		expect(
			canApplyReasoningEffortUpdate({ REASONING_EFFORT: 'high' }, 'reason_filter', 'reason_filter')
		).toBe(true);
	});
});

describe('canCacheReasoningEffortLoad', () => {
	test('only caches a load when the API returned a usable reasoning select schema', () => {
		expect(canCacheReasoningEffortLoad(null, null)).toBe(false);
		expect(canCacheReasoningEffortLoad({}, null)).toBe(false);
		expect(
			canCacheReasoningEffortLoad(
				{},
				{
					properties: {
						REASONING_EFFORT: {
							input: { type: 'select', options: [{ value: 'high', label: 'high' }] }
						}
					}
				}
			)
		).toBe(true);
	});
});

describe('getIntegrationPresentation', () => {
	test('uses the legacy integrations menu on mobile and inline controls on wider screens', () => {
		expect(getIntegrationPresentation(true)).toEqual({
			showInlineControls: false,
			showCoreControlsInMenu: true
		});
		expect(getIntegrationPresentation(false)).toEqual({
			showInlineControls: true,
			showCoreControlsInMenu: false
		});
	});
});

describe('shouldShowIntegrationsMenu', () => {
	test('keeps the legacy button available on mobile when only core integrations exist', () => {
		expect(
			shouldShowIntegrationsMenu({
				showCoreControlsInMenu: true,
				showWebSearchButton: false,
				showImageGenerationButton: true,
				showCodeInterpreterButton: false,
				showToolsButton: false,
				showSkillsButton: false,
				filterCount: 0
			})
		).toBe(true);
	});

	test('does not show an empty integrations button', () => {
		expect(
			shouldShowIntegrationsMenu({
				showCoreControlsInMenu: true,
				showWebSearchButton: false,
				showImageGenerationButton: false,
				showCodeInterpreterButton: false,
				showToolsButton: false,
				showSkillsButton: false,
				filterCount: 0
			})
		).toBe(false);
	});
});
