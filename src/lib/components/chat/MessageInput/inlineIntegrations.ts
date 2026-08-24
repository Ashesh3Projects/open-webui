export type ToggleFilter = {
	id: string;
	name?: string;
	title?: string;
	has_user_valves?: boolean;
	[key: string]: unknown;
};

export type ValveOption = {
	value: string;
	label: string;
};

export type ReasoningEffortValve = {
	key: string;
	defaultValue: string;
	options: ValveOption[];
};

const REASONING_FILTER_IDS = new Set(['reason_filter', 'reasoning_effort']);

const EFFORT_LABELS: Record<string, string> = {
	'not set': 'Model default',
	none: 'None',
	low: 'Low',
	medium: 'Medium',
	high: 'High',
	xhigh: 'Extra High',
	max: 'Max',
	ultra: 'Ultra'
};

const normalize = (value: unknown) => `${value ?? ''}`.trim().toLowerCase();

export const findReasoningEffortFilter = (filters: ToggleFilter[] = []) =>
	filters.find((filter) => {
		const id = normalize(filter?.id);
		const name = normalize(filter?.name ?? filter?.title);
		return (
			REASONING_FILTER_IDS.has(id) ||
			(filter?.has_user_valves === true && name === 'reasoning effort')
		);
	});

export const getReasoningEffortValve = (spec: any): ReasoningEffortValve | null => {
	const properties = spec?.properties ?? {};
	const key = Object.keys(properties).find((property) => {
		const propertySpec = properties[property] ?? {};
		return (
			normalize(property) === 'reasoning_effort' ||
			normalize(propertySpec?.title) === 'reasoning effort'
		);
	});

	if (!key) return null;

	const propertySpec = properties[key] ?? {};
	if (propertySpec?.input?.type !== 'select' || !Array.isArray(propertySpec?.input?.options)) {
		return null;
	}

	const options = propertySpec.input.options.map((option: any) => {
		const value = `${typeof option === 'object' ? option?.value : option}`;
		return {
			value,
			label: EFFORT_LABELS[normalize(value)] ?? `${option?.label ?? value}`
		};
	});

	return {
		key,
		defaultValue: `${propertySpec?.default ?? options[0]?.value ?? ''}`,
		options
	};
};

export const setFilterEnabled = (selectedIds: string[] = [], id: string, enabled: boolean) => {
	const withoutDuplicates = selectedIds.filter(
		(selectedId, index) => selectedId !== id || selectedIds.indexOf(selectedId) === index
	);

	if (enabled) {
		return withoutDuplicates.includes(id) ? withoutDuplicates : [...withoutDuplicates, id];
	}

	return withoutDuplicates.filter((selectedId) => selectedId !== id);
};

export const canApplyReasoningEffortUpdate = (
	updatedValves: unknown,
	originatingFilterId: string,
	activeFilterId: string | undefined
) =>
	updatedValves !== null && updatedValves !== undefined && activeFilterId === originatingFilterId;

export const canCacheReasoningEffortLoad = (loadedValves: unknown, spec: unknown) =>
	loadedValves !== null && loadedValves !== undefined && getReasoningEffortValve(spec) !== null;
