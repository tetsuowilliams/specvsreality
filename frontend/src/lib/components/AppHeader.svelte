<script lang="ts">
	import { page } from '$app/stores';
	import { getAppContext } from '$lib/appContext';
	import { windToHead } from '$lib/api/repos';

	const app = getAppContext();

	let syncing = $state(false);
	let syncMessage = $state<string | null>(null);

	const currentRepo = $derived.by(() => {
		const repoId = $page.params.id;
		if (!repoId) return null;
		return app.getRepos().find((repo) => String(repo.id) === repoId) ?? null;
	});

	const canSync = $derived(
		currentRepo != null && Boolean(currentRepo.cursor_position) && !currentRepo.clone_error
	);

	async function syncRepo() {
		if (!currentRepo || syncing || !canSync) return;
		syncing = true;
		syncMessage = null;
		try {
			await windToHead(currentRepo.id);
			syncMessage = 'Queued';
			await app.refreshRepos();
		} catch (e) {
			syncMessage = e instanceof Error ? e.message : 'Failed to queue sync';
		} finally {
			syncing = false;
		}
	}
</script>

<header class="app-header">
	<div class="brand">
		<a href="/" class="logo">Spec vs Reality</a>
		{#if currentRepo}
			<span class="divider">/</span>
			<span class="repo-name">{currentRepo.name}</span>
		{/if}
	</div>
	<div class="actions">
		{#if currentRepo}
			<button
				type="button"
				class="sync-btn"
				disabled={syncing || !canSync}
				title={canSync
					? 'Pull latest changes and analyze new commits'
					: 'Available after the repository finishes initializing'}
				onclick={syncRepo}
			>
				{syncing ? 'Syncing…' : 'Sync'}
			</button>
			{#if syncMessage}
				<span class="sync-message" class:error={syncMessage !== 'Queued'}>{syncMessage}</span>
			{/if}
		{/if}
		<button type="button" class="add-btn" onclick={() => app.openAddRepo()}>+ Add repo</button>
	</div>
</header>

<style>
	.app-header {
		height: 3.25rem;
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 1rem;
		background: #fff;
		border-bottom: 1px solid #e2e8f0;
		position: sticky;
		top: 0;
		z-index: 40;
	}

	.brand {
		display: flex;
		align-items: center;
		gap: 0.45rem;
		min-width: 0;
	}

	.logo {
		font-size: 0.95rem;
		font-weight: 700;
		color: #0f172a;
		text-decoration: none;
		letter-spacing: -0.02em;
		white-space: nowrap;
	}

	.divider {
		color: #cbd5e1;
	}

	.repo-name {
		font-size: 0.88rem;
		font-weight: 500;
		color: #475569;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.actions {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.sync-btn,
	.add-btn {
		border: 1px solid #cbd5e1;
		background: #fff;
		color: #334155;
		border-radius: 0.45rem;
		padding: 0.35rem 0.7rem;
		font-size: 0.8rem;
		font-weight: 500;
		cursor: pointer;
	}

	.sync-btn:disabled {
		opacity: 0.55;
		cursor: not-allowed;
	}

	.sync-btn:hover:not(:disabled),
	.add-btn:hover {
		background: #f8fafc;
		border-color: #94a3b8;
	}

	.sync-message {
		font-size: 0.75rem;
		color: #16a34a;
	}

	.sync-message.error {
		color: #b91c1c;
		max-width: 12rem;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
</style>
