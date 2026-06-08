<script lang="ts">
	import { page } from '$app/stores';
	import { getAppContext } from '$lib/appContext';

	const app = getAppContext();
	const repos = $derived(app.getRepos());
</script>

<aside class="repo-rail" aria-label="Workspace navigation">
	<nav class="global-nav">
		<a
			href="/metrics"
			class="global-link"
			class:active={$page.url.pathname === '/metrics'}
		>
			Metrics
		</a>
	</nav>
	<div class="rail-header">
		<span class="title">Repositories</span>
		<button type="button" class="icon-btn" onclick={() => app.openAddRepo()} title="Add repository">
			+
		</button>
	</div>
	<nav class="repo-list">
		{#if repos.length === 0}
			<p class="empty">No repositories yet.</p>
		{:else}
			{#each repos as repo (repo.id)}
				<a
					href="/repos/{repo.id}"
					class="repo-link"
					class:active={$page.params.id === String(repo.id)}
				>
					<span class="repo-name">{repo.name}</span>
					<span class="repo-url">{repo.url}</span>
				</a>
			{/each}
		{/if}
	</nav>
</aside>

<style>
	.repo-rail {
		width: 13.5rem;
		flex-shrink: 0;
		background: #f8fafc;
		border-right: 1px solid #e2e8f0;
		display: flex;
		flex-direction: column;
		min-height: 0;
	}

	.global-nav {
		padding: 0.65rem 0.45rem 0.25rem;
	}

	.global-link {
		display: block;
		padding: 0.45rem 0.5rem;
		border-radius: 0.45rem;
		text-decoration: none;
		color: #334155;
		font-size: 0.82rem;
		font-weight: 600;
		border: 1px solid transparent;
	}

	.global-link:hover {
		background: #eef2f7;
	}

	.global-link.active {
		background: #fff;
		border-color: #dbeafe;
		color: #1d4ed8;
		box-shadow: 0 1px 2px rgba(37, 99, 235, 0.08);
	}

	.rail-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.75rem 0.75rem 0.5rem;
	}

	.title {
		font-size: 0.72rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: #94a3b8;
	}

	.icon-btn {
		width: 1.5rem;
		height: 1.5rem;
		border: 1px solid #cbd5e1;
		border-radius: 0.35rem;
		background: #fff;
		color: #475569;
		cursor: pointer;
		font-size: 0.95rem;
		line-height: 1;
	}

	.repo-list {
		display: flex;
		flex-direction: column;
		gap: 0.15rem;
		padding: 0 0.45rem 0.75rem;
		overflow: auto;
	}

	.repo-link {
		display: grid;
		gap: 0.1rem;
		padding: 0.45rem 0.5rem;
		border-radius: 0.45rem;
		text-decoration: none;
		color: inherit;
		border: 1px solid transparent;
	}

	.repo-link:hover {
		background: #eef2f7;
	}

	.repo-link.active {
		background: #fff;
		border-color: #dbeafe;
		box-shadow: 0 1px 2px rgba(37, 99, 235, 0.08);
	}

	.repo-name {
		font-size: 0.82rem;
		font-weight: 600;
		color: #0f172a;
	}

	.repo-url {
		font-size: 0.68rem;
		color: #64748b;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.empty {
		margin: 0;
		padding: 0.5rem;
		font-size: 0.8rem;
		color: #64748b;
	}
</style>
