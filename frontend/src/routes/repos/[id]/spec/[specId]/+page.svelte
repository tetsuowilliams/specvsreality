<script lang="ts">
	import { page } from '$app/stores';
	import SpecMarkdownView from '$lib/components/SpecMarkdownView.svelte';
	import SpecItemDrawer from '$lib/components/SpecItemDrawer.svelte';
	import SpecOverview from '$lib/components/SpecOverview.svelte';
	import {
		fetchSpecViewMarkdown,
		fetchSpecViewOverview,
		type SpecDocument,
		type SpecTab,
		type SpecViewMarkdown,
		type SpecViewOverviewResponse
	} from '$lib/api/repoCatalog';
	import { itemTypeColor } from '$lib/spec/itemTypeColors';

	let view = $state<SpecViewOverviewResponse | null>(null);
	let markdown = $state<SpecViewMarkdown | null>(null);
	let loading = $state(true);
	let markdownLoading = $state(false);
	let markdownErr = $state<string | null>(null);
	let err = $state<string | null>(null);
	let selectedItemId = $state<number | null>(null);
	let drawerOpen = $state(false);
	let activeTab = $state<SpecTab>('overview');
	let loadGeneration = 0;
	let markdownGeneration = 0;
	const selectedItem = $derived(
		view?.items.find((item) => item.id === selectedItemId) ?? null
	);

	const docTabs = $derived.by(() => {
		if (!view) return [];
		const tabs: { id: SpecDocument; label: string }[] = [{ id: 'spec', label: 'Spec' }];
		if (view.version.has_tasks_md) {
			tabs.push({ id: 'tasks', label: 'Tasks' });
		}
		if (view.version.has_plan_md) {
			tabs.push({ id: 'plan', label: 'Plan' });
		}
		return tabs;
	});

	const activeMarkdown = $derived.by(() => {
		if (!markdown) return '';
		if (activeTab === 'tasks') return markdown.tasks_md ?? '';
		if (activeTab === 'plan') return markdown.plan_md ?? '';
		return markdown.spec_md;
	});

	const legendTypes = $derived(
		view && activeTab !== 'overview'
			? [
					...new Set(
						view.items
							.filter((item) => item.spans[activeTab as SpecDocument] != null)
							.map((item) => item.item_type)
					)
				]
			: []
	);

	function isCommitNotFoundError(error: unknown): boolean {
		return error instanceof Error && error.message.includes('spec version not found for commit');
	}

	async function loadMarkdown(
		repoId: string,
		specId: string,
		commitSha: string | null,
		generation: number
	) {
		const mdGeneration = ++markdownGeneration;
		markdownLoading = true;
		markdownErr = null;
		try {
			let result: SpecViewMarkdown;
			try {
				result = await fetchSpecViewMarkdown(repoId, specId, commitSha ?? undefined);
			} catch (e) {
				if (!commitSha || !isCommitNotFoundError(e)) {
					throw e;
				}
				result = await fetchSpecViewMarkdown(repoId, specId);
			}
			if (generation !== loadGeneration || mdGeneration !== markdownGeneration) return;
			markdown = result;
		} catch (e) {
			if (generation !== loadGeneration || mdGeneration !== markdownGeneration) return;
			markdownErr = e instanceof Error ? e.message : 'Failed to load markdown';
			markdown = null;
		} finally {
			if (generation === loadGeneration && mdGeneration === markdownGeneration) {
				markdownLoading = false;
			}
		}
	}

	async function load(repoId: string, specId: string, commitSha: string | null) {
		const generation = ++loadGeneration;
		loading = true;
		err = null;
		markdown = null;
		markdownErr = null;
		selectedItemId = null;
		drawerOpen = false;
		activeTab = 'overview';
		try {
			let result: SpecViewOverviewResponse;
			try {
				result = await fetchSpecViewOverview(repoId, specId, commitSha ?? undefined);
			} catch (e) {
				if (!commitSha || !isCommitNotFoundError(e)) {
					throw e;
				}
				result = await fetchSpecViewOverview(repoId, specId);
			}
			if (generation !== loadGeneration) return;
			view = result;
			void loadMarkdown(repoId, specId, commitSha, generation);
		} catch (e) {
			if (generation !== loadGeneration) return;
			err = e instanceof Error ? e.message : 'Failed to load spec';
			view = null;
		} finally {
			if (generation === loadGeneration) {
				loading = false;
			}
		}
	}

	function openItem(itemId: number) {
		selectedItemId = itemId;
		drawerOpen = true;
	}

	function closeDrawer() {
		drawerOpen = false;
	}

	function shortSha(sha: string): string {
		return sha.slice(0, 7);
	}

	function selectTab(tab: SpecTab) {
		activeTab = tab;
	}

	$effect(() => {
		const repoId = $page.params.id;
		const specId = $page.params.specId;
		const commitSha = $page.url.searchParams.get('commit_sha');
		if (!repoId || !specId) return;
		void load(repoId, specId, commitSha);
	});

	$effect(() => {
		if (!view) return;
		const itemId = Number($page.url.searchParams.get('item'));
		if (Number.isFinite(itemId) && view.items.some((item) => item.id === itemId)) {
			openItem(itemId);
		}
	});
</script>

{#if loading}
	<p>Loading spec…</p>
{:else if err}
	<p class="error">{err}</p>
{:else if view}
	<section class="spec-view">
		<header class="spec-header">
			<div>
				<h2>{view.version.title ?? `Spec · ${view.paper_id}`}</h2>
				<p class="meta">
					<span class="paper-id">{view.paper_id}</span>
					<span class="sep">·</span>
					<code class="commit">{shortSha(view.version.commit_sha)}</code>
					<span class="sep">·</span>
					<span class="commit-msg">{view.version.commit_message}</span>
				</p>
				{#if view.version.summary}
					<p class="summary">{view.version.summary}</p>
				{/if}
			</div>
		</header>

		<nav class="doc-tabs" aria-label="Spec view">
			<button
				type="button"
				class="doc-tab"
				class:active={activeTab === 'overview'}
				aria-current={activeTab === 'overview' ? 'page' : undefined}
				onclick={() => selectTab('overview')}
			>
				Overview
			</button>
			{#each docTabs as tab (tab.id)}
				<button
					type="button"
					class="doc-tab"
					class:active={activeTab === tab.id}
					aria-current={activeTab === tab.id ? 'page' : undefined}
					onclick={() => selectTab(tab.id)}
				>
					{tab.label}
				</button>
			{/each}
		</nav>

		{#if activeTab === 'overview'}
			<SpecOverview {view} onItemClick={openItem} />
		{:else if markdownLoading && !markdown}
			<p class="muted">Loading document…</p>
		{:else if markdownErr}
			<p class="error">{markdownErr}</p>
		{:else if markdown}
			{#if legendTypes.length > 0}
				<div class="legend">
					<span class="legend-label">Highlighted in this tab</span>
					{#each legendTypes as itemType}
						<span
							class="legend-chip"
							style:background={itemTypeColor(itemType).bg}
							style:color={itemTypeColor(itemType).text}
							style:border-color={itemTypeColor(itemType).border}
						>
							{itemType.replaceAll('_', ' ')}
						</span>
					{/each}
				</div>
			{/if}

			<div class="markdown-panel">
				<SpecMarkdownView
					markdown={activeMarkdown}
					document={activeTab as SpecDocument}
					items={view.items}
					onItemClick={openItem}
				/>
			</div>
		{/if}
	</section>

	<SpecItemDrawer item={selectedItem} open={drawerOpen} onClose={closeDrawer} />
{/if}

<style>
	.spec-header {
		margin-bottom: 0.85rem;
		padding-bottom: 0.85rem;
		border-bottom: 1px solid #e2e8f0;
	}

	.spec-header h2 {
		margin: 0 0 0.35rem 0;
		font-size: 1.35rem;
		font-weight: 700;
		letter-spacing: -0.02em;
		color: #0f172a;
	}

	.meta {
		margin: 0;
		font-size: 0.82rem;
		color: #64748b;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.35rem;
	}

	.paper-id {
		font-family: ui-monospace, monospace;
		color: #334155;
	}

	.commit {
		font-family: ui-monospace, monospace;
		font-size: 0.78rem;
		background: #f1f5f9;
		padding: 0.1rem 0.35rem;
		border-radius: 0.3rem;
	}

	.summary {
		margin: 0.5rem 0 0 0;
		font-size: 0.88rem;
		color: #475569;
	}

	.doc-tabs {
		display: flex;
		gap: 0.25rem;
		margin-bottom: 0.85rem;
		border-bottom: 1px solid #e2e8f0;
	}

	.doc-tab {
		appearance: none;
		border: none;
		background: transparent;
		padding: 0.55rem 0.85rem;
		margin-bottom: -1px;
		font-size: 0.88rem;
		font-weight: 500;
		color: #64748b;
		cursor: pointer;
		border-bottom: 2px solid transparent;
		border-radius: 0.35rem 0.35rem 0 0;
		transition:
			color 0.15s ease,
			background 0.15s ease,
			border-color 0.15s ease;
	}

	.doc-tab:hover {
		color: #334155;
		background: #f8fafc;
	}

	.doc-tab.active {
		color: #0f172a;
		font-weight: 600;
		border-bottom-color: #2563eb;
		background: #fff;
	}

	.legend {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.35rem;
		margin-bottom: 0.85rem;
	}

	.legend-label {
		font-size: 0.72rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: #94a3b8;
		margin-right: 0.15rem;
	}

	.legend-chip {
		font-size: 0.68rem;
		padding: 0.12rem 0.45rem;
		border-radius: 999px;
		border: 1px solid transparent;
	}

	.markdown-panel {
		padding: 0.25rem 0.15rem;
	}

	.muted {
		color: #64748b;
	}

	.error {
		color: #9a1c1c;
	}
</style>
