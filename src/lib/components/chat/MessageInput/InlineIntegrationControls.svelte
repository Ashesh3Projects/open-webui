<script lang="ts">
	import { getContext } from 'svelte';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import Photo from '$lib/components/icons/Photo.svelte';
	import Terminal from '$lib/components/icons/Terminal.svelte';

	import ReasoningEffortMenu from './ReasoningEffortMenu.svelte';

	const i18n: any = getContext('i18n');

	export let reasoningFilter: any = null;
	export let selectedFilterIds: string[] = [];
	export let canConfigureReasoning = true;

	export let showWebSearchButton = false;
	export let webSearchEnabled = false;
	export let showImageGenerationButton = false;
	export let imageGenerationEnabled = false;
	export let showCodeInterpreterButton = false;
	export let codeInterpreterEnabled = false;

	export let onWebSearchToggle: Function = () => {};

	const activeClass =
		'border-sky-200/50 bg-sky-50 text-sky-600 hover:bg-sky-100 dark:border-sky-500/20 dark:bg-sky-400/10 dark:text-sky-300 dark:hover:bg-sky-600/10';
	const inactiveClass =
		'border-transparent bg-transparent text-gray-600 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800';
</script>

<div class="flex shrink-0 items-center gap-0.5">
	{#if reasoningFilter}
		<ReasoningEffortMenu
			filter={reasoningFilter}
			bind:selectedFilterIds
			canConfigure={canConfigureReasoning}
		/>
	{/if}

	{#if showWebSearchButton}
		<Tooltip content={$i18n.t('Web Search')} placement="top">
			<button
				type="button"
				aria-label={webSearchEnabled ? $i18n.t('Disable Web Search') : $i18n.t('Enable Web Search')}
				aria-pressed={webSearchEnabled}
				class="flex size-[1.875rem] shrink-0 items-center justify-center rounded-full border transition-colors duration-200 focus:outline-hidden {webSearchEnabled
					? activeClass
					: inactiveClass}"
				on:click={() => {
					webSearchEnabled = !webSearchEnabled;
					onWebSearchToggle(webSearchEnabled);
				}}
			>
				<GlobeAlt className="size-4" strokeWidth="1.75" />
			</button>
		</Tooltip>
	{/if}

	{#if showImageGenerationButton}
		<Tooltip content={$i18n.t('Image')} placement="top">
			<button
				type="button"
				aria-label={imageGenerationEnabled
					? $i18n.t('Disable Image Generation')
					: $i18n.t('Enable Image Generation')}
				aria-pressed={imageGenerationEnabled}
				class="flex size-[1.875rem] shrink-0 items-center justify-center rounded-full border transition-colors duration-200 focus:outline-hidden {imageGenerationEnabled
					? activeClass
					: inactiveClass}"
				on:click={() => (imageGenerationEnabled = !imageGenerationEnabled)}
			>
				<Photo className="size-4" strokeWidth="1.75" />
			</button>
		</Tooltip>
	{/if}

	{#if showCodeInterpreterButton}
		<Tooltip content={$i18n.t('Code Interpreter')} placement="top">
			<button
				type="button"
				aria-label={codeInterpreterEnabled
					? $i18n.t('Disable Code Interpreter')
					: $i18n.t('Enable Code Interpreter')}
				aria-pressed={codeInterpreterEnabled}
				class="flex size-[1.875rem] shrink-0 items-center justify-center rounded-full border transition-colors duration-200 focus:outline-hidden {codeInterpreterEnabled
					? activeClass
					: inactiveClass}"
				on:click={() => (codeInterpreterEnabled = !codeInterpreterEnabled)}
			>
				<Terminal className="size-3.5" strokeWidth="2" />
			</button>
		</Tooltip>
	{/if}
</div>
