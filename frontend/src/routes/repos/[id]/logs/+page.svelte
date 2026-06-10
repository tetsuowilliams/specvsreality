<script lang="ts">
	import { page } from '$app/stores';
	import { fetchCommitLogs, fetchLogsSidebar, type RepoCommitLogsResponse } from '$lib/api/repoLogs';

	let { data }: { data: { id: string } } = $props();

	let logs = $state<RepoCommitLogsResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	const commitSha = $derived($page.url.searchParams.get('commit_sha'));

	async function load() {
		loading = true;
		error = null;
		try {
			let selectedSha = commitSha;
			if (!selectedSha) {
				const sidebar = await fetchLogsSidebar(data.id);
				selectedSha = sidebar.commits[0]?.commit_sha ?? null;
				if (selectedSha && selectedSha !== commitSha) {
					const url = new URL($page.url);
					url.searchParams.set('commit_sha', selectedSha);
					window.history.replaceState({}, '', url);
				}
			}
			if (!selectedSha) {
				logs = null;
				return;
			}
			logs = await fetchCommitLogs(data.id, selectedSha);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load commit logs';
			logs = null;
		} finally {
			loading = false;
		}
	}

	function formatAction(action: string): string {
		if (action === 'spec_extract') return 'Spec extraction';
		if (action === 'spec_rescan') return 'Spec rescan';
		return action;
	}

	function formatDate(value: string): string {
		return new Intl.DateTimeFormat(undefined, {
			month: 'short',
			day: 'numeric',
			year: 'numeric',
			hour: 'numeric',
			minute: '2-digit'
		}).format(new Date(value));
	}

	$effect(() => {
		void load();
	});
</script>

<section class="logs-page">
	{#if loading}
		<p class="muted">Loading logs…</p>
	{:else if error}
		<p class="error">{error}</p>
	{:else if !logs}
		<p class="muted">No commit logs for this repository yet.</p>
	{:else}
		<header class="logs-header">
			<h1>Commit logs</h1>
			<p class="commit-summary">
				<code>{logs.commit_sha.slice(0, 7)}</code>
				<span>{logs.commit_message}</span>
			</p>
		</header>

		{#if logs.logs.length === 0}
			<p class="muted">No log entries for this commit.</p>
		{:else}
			<ul class="log-list">
				{#each logs.logs as entry (entry.created_at + entry.spec_folder + entry.message)}
					<li class="log-card">
						<div class="log-top">
							<span class="action">{formatAction(entry.action)}</span>
							<code class="folder">{entry.spec_folder}</code>
							<time datetime={entry.created_at}>{formatDate(entry.created_at)}</time>
						</div>
						<p class="message">{entry.message}</p>
						<p class="reasoning">{entry.reasoning}</p>
					</li>
				{/each}
			</ul>
		{/if}
	{/if}
</section>

<style>
	.logs-page {
		max-width: 52rem;
	}

	.logs-header h1 {
		margin: 0 0 0.35rem;
		font-size: 1.1rem;
		font-weight: 600;
		color: #0f172a;
	}

	.commit-summary {
		margin: 0 0 1rem;
		display: flex;
		gap: 0.5rem;
		align-items: baseline;
		flex-wrap: wrap;
		font-size: 0.82rem;
		color: #475569;
	}

	.muted {
		font-size: 0.82rem;
		color: #94a3b8;
	}

	.error {
		font-size: 0.82rem;
		color: #b91c1c;
	}

	.log-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 0.65rem;
	}

	.log-card {
		border: 1px solid #e2e8f0;
		border-radius: 0.55rem;
		padding: 0.75rem 0.85rem;
		background: #fff;
	}

	.log-top {
		display: flex;
		gap: 0.5rem;
		align-items: center;
		flex-wrap: wrap;
		margin-bottom: 0.35rem;
	}

	.action {
		font-size: 0.72rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: #1d4ed8;
	}

	.folder {
		font-size: 0.72rem;
		color: #475569;
	}

	time {
		margin-left: auto;
		font-size: 0.68rem;
		color: #94a3b8;
	}

	.message {
		margin: 0 0 0.25rem;
		font-size: 0.84rem;
		font-weight: 500;
		color: #0f172a;
	}

	.reasoning {
		margin: 0;
		font-size: 0.8rem;
		line-height: 1.45;
		color: #475569;
	}
</style>
