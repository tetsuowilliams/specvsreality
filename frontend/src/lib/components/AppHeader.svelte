<script lang="ts">
	import { page } from '$app/stores';
	import { getAppContext } from '$lib/appContext';

	const app = getAppContext();

	const currentRepo = $derived.by(() => {
		const repoId = $page.params.id;
		if (!repoId) return null;
		return app.getRepos().find((repo) => String(repo.id) === repoId) ?? null;
	});
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

	.add-btn:hover {
		background: #f8fafc;
		border-color: #94a3b8;
	}
</style>
