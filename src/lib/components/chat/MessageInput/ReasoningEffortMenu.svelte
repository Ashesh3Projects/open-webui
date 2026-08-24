<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		getUserValvesById,
		getUserValvesSpecById,
		updateUserValvesById
	} from '$lib/apis/functions';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';

	import {
		canApplyReasoningEffortUpdate,
		canCacheReasoningEffortLoad,
		getReasoningEffortValve,
		setFilterEnabled
	} from './inlineIntegrations';

	const i18n: any = getContext('i18n');

	export let filter: any;
	export let selectedFilterIds: string[] = [];
	export let canConfigure = true;

	let show = false;
	let loading = false;
	let saving = false;
	let loadedFilterId: string | null = null;
	let valve: ReturnType<typeof getReasoningEffortValve> = null;
	let valves: Record<string, any> = {};

	$: enabled = selectedFilterIds.includes(filter?.id);
	$: selectedValue = valve ? `${valves?.[valve.key] ?? valve.defaultValue}` : '';
	$: selectedLabel = valve?.options.find((option) => option.value === selectedValue)?.label ?? '';
	$: if (filter?.id !== loadedFilterId) {
		valve = null;
		valves = {};
	}

	const setEnabled = (state: boolean, filterId = filter?.id) => {
		if (!filterId) return;
		selectedFilterIds = setFilterEnabled(selectedFilterIds, filterId, state);
	};

	const load = async () => {
		if (!filter?.id || loadedFilterId === filter.id || loading) return;

		loading = true;
		const filterId = filter.id;
		try {
			const [nextValves, spec] = await Promise.all([
				getUserValvesById(localStorage.token, filterId),
				getUserValvesSpecById(localStorage.token, filterId)
			]);

			if (filter?.id !== filterId) return;
			if (!canCacheReasoningEffortLoad(nextValves, spec)) {
				throw new Error($i18n.t('Failed to load reasoning effort options'));
			}

			valves = nextValves ?? {};
			valve = getReasoningEffortValve(spec);
			loadedFilterId = filterId;
		} catch (error) {
			toast.error(`${error ?? $i18n.t('Error fetching valves')}`);
		} finally {
			loading = false;
		}
	};

	const selectEffort = async (value: string) => {
		if (!filter?.id || !valve || saving) return;

		const filterId = filter.id;
		const previousValves = valves;
		valves = { ...valves, [valve.key]: value };
		saving = true;
		try {
			const updated = await updateUserValvesById(localStorage.token, filterId, valves);
			if (!canApplyReasoningEffortUpdate(updated, filterId, filter?.id)) {
				throw new Error($i18n.t('Failed to update reasoning effort'));
			}

			valves = updated;
			setEnabled(true, filterId);
		} catch (error) {
			valves = previousValves;
			toast.error(`${error}`);
		} finally {
			saving = false;
		}
	};
</script>

<Dropdown
	bind:show
	side="top"
	align="start"
	onOpenChange={(state) => {
		if (state) load();
	}}
>
	<Tooltip
		content={selectedLabel
			? `${$i18n.t('Reasoning Effort')}: ${selectedLabel}`
			: $i18n.t('Reasoning Effort')}
		placement="top"
	>
		<button
			type="button"
			aria-label={$i18n.t('Reasoning Effort')}
			aria-pressed={enabled}
			class="group flex h-[1.875rem] shrink-0 items-center gap-1 rounded-full border px-2 text-xs transition-colors duration-200 focus:outline-hidden {enabled
				? 'border-sky-200/50 bg-sky-50 text-sky-600 hover:bg-sky-100 dark:border-sky-500/20 dark:bg-sky-400/10 dark:text-sky-300 dark:hover:bg-sky-600/10'
				: 'border-transparent bg-transparent text-gray-600 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800'}"
		>
			<Sparkles className="size-4" strokeWidth="1.75" />
			<span class="hidden max-w-24 truncate sm:block">
				{selectedLabel || $i18n.t('Reasoning')}
			</span>
			<ChevronRight className="size-3 rotate-[-90deg] opacity-60" strokeWidth="1.75" />
		</button>
	</Tooltip>

	<div slot="content">
		<DropdownMenu className="min-w-48 p-1!">
			<div class="px-2 pb-1 pt-1.5 text-[11px] font-medium text-gray-500 dark:text-gray-400">
				{$i18n.t('Reasoning Effort')}
			</div>

			{#if loading}
				<div class="px-2 py-2 text-xs text-gray-500">{$i18n.t('Loading...')}</div>
			{:else if valve && canConfigure}
				{#each valve.options as option (option.value)}
					<button
						type="button"
						disabled={saving}
						class="justify-between disabled:cursor-wait disabled:opacity-60"
						on:click={() => selectEffort(option.value)}
					>
						<span>{option.label}</span>
						{#if option.value === selectedValue}
							<Check className="size-3.5" strokeWidth="2" />
						{/if}
					</button>
				{/each}
			{:else if canConfigure}
				<div class="px-2 py-2 text-xs text-gray-500">
					{$i18n.t('No reasoning effort options')}
				</div>
			{/if}

			{#if !loading}
				{#if valve && canConfigure}<hr />{/if}
				<button
					type="button"
					class="justify-between text-gray-600 dark:text-gray-300"
					on:click={() => setEnabled(!enabled)}
				>
					<span>{enabled ? $i18n.t('Disable') : $i18n.t('Enable')}</span>
					{#if enabled}<Check className="size-3.5" strokeWidth="2" />{/if}
				</button>
			{/if}
		</DropdownMenu>
	</div>
</Dropdown>
