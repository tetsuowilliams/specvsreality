<script lang="ts">
	import { page } from '$app/stores';
	import { getRepo, type Repo } from '$lib/api/repos';
	import { fetchRepoCatalog, type RepoCatalogResponse } from '$lib/api/repoCatalog';
	import { setRepoContext } from '$lib/repoContext';

	let { data, children }: { data: { id: string }; children: import('svelte').Snippet } = $props();

	let repo = $state<Repo | null>(null);
	let catalog = $state<RepoCatalogResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let catalogError = $state<string | null>(null);

	setRepoContext({
		getRepo: () => repo,
		getRepoId: () => data.id
	});

	async function loadWorkspace() {
		loading = true;
		error = null;
		catalogError = null;
		repo = null;
		catalog = null;
		try {
			repo = await getRepo(data.id);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load repository';
			loading = false;
			return;
		}
		try {
			catalog = await fetchRepoCatalog(data.id);
		} catch (e) {
			catalogError = e instanceof Error ? e.message : 'Failed to load catalog';
			catalog = null;
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		void loadWorkspace();
	});
</script>

<section class="repo-layout">
	<p class="back-link"><a href="/">Back to repos</a></p>
	{#if loading}
		<p>Loading repository…</p>
	{:else if error}
		<p class="error">{error}</p>
	{:else if repo}
		<header class="repo-header">
			<div>
				<h1>{repo.name}</h1>
				<p class="url">{repo.url}</p>
			</div>
			<p class="overview-link">
				<a href="/repos/{data.id}/dashboard">Clone / scan overview</a>
			</p>
		</header>

		<div class="workspace">
			<aside class="sidebar" aria-label="Specs and requirements">
				<h2 class="sidebar-title">Catalog</h2>
				{#if catalogError}
					<p class="error">{catalogError}</p>
				{:else if catalog && catalog.specs.length === 0}
					<p class="muted">No specs for this repo yet.</p>
				{:else if catalog}
					<ul class="tree">
						{#each catalog.specs as spec}
							<li class="tree-spec">
								<a
									class="tree-link"
									class:active={$page.url.pathname === `/repos/${data.id}/spec/${spec.id}`}
									href="/repos/{data.id}/spec/{spec.id}"
								>
									Spec · {spec.paper_id}
								</a>
								{#if spec.requirements.length > 0}
									<ul class="tree-reqs">
										{#each spec.requirements as req}
											<li>
												<a
													class="tree-link sub"
													class:active={$page.url.pathname ===
														`/repos/${data.id}/spec/${spec.id}/gantt` &&
														$page.url.searchParams.get('requirement_id') ===
															String(req.id)}
													href="/repos/{data.id}/spec/{spec.id}/gantt?requirement_id={req.id}"
												>
													Req · {req.paper_id}
												</a>
											</li>
										{/each}
									</ul>
								{/if}
							</li>
						{/each}
					</ul>
				{/if}
			</aside>
			<section class="main-panel">
				{@render children()}
			</section>
		</div>
	{/if}
</section>

<style>
	.repo-layout {
		max-width: 96rem;
		margin: 1.5rem auto;
		padding: 0 1.25rem;
		font-family: system-ui, -apple-system, 'Segoe UI', sans-serif;
	}
	.back-link {
		margin: 0 0 0.75rem 0;
		font-size: 0.9rem;
	}
	.back-link a {
		color: #2563eb;
		text-decoration: none;
	}
	.back-link a:hover {
		text-decoration: underline;
	}
	.repo-header {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-start;
		justify-content: space-between;
		gap: 0.75rem;
		margin-bottom: 1rem;
	}
	.repo-header h1 {
		margin: 0;
		letter-spacing: -0.02em;
	}
	.url {
		color: #4b5563;
		margin: 0.3rem 0 0 0;
		font-size: 0.92rem;
	}
	.overview-link {
		margin: 0;
		font-size: 0.88rem;
	}
	.overview-link a {
		color: #2563eb;
		text-decoration: none;
	}
	.overview-link a:hover {
		text-decoration: underline;
	}
	.workspace {
		display: grid;
		grid-template-columns: minmax(14rem, 18rem) 1fr;
		gap: 1rem;
		align-items: start;
	}
	.sidebar {
		border: 1px solid #e2e8f0;
		border-radius: 0.75rem;
		padding: 0.85rem 0.75rem;
		background: #f8fafc;
		min-height: 16rem;
	}
	.sidebar-title {
		margin: 0 0 0.5rem 0;
		font-size: 0.95rem;
		color: #334155;
	}
	.tree {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
	}
	.tree-spec {
		margin: 0;
	}
	.tree-reqs {
		list-style: none;
		padding: 0 0 0 0.65rem;
		margin: 0.25rem 0 0 0;
		border-left: 2px solid #cbd5e1;
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
	}
	.tree-link {
		display: block;
		padding: 0.25rem 0.35rem;
		border-radius: 0.35rem;
		color: #0f172a;
		text-decoration: none;
		font-size: 0.86rem;
		word-break: break-word;
	}
	.tree-link.sub {
		font-size: 0.82rem;
		color: #334155;
	}
	.tree-link:hover {
		background: #e2e8f0;
	}
	.tree-link.active {
		background: #dbeafe;
		font-weight: 600;
	}
	.main-panel {
		border: 1px solid #e2e8f0;
		border-radius: 0.75rem;
		padding: 1.1rem;
		min-height: 20rem;
		background: #fff;
		box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
	}
	.error {
		color: #9a1c1c;
	}
	.muted {
		color: #64748b;
		font-size: 0.88rem;
		margin: 0;
	}
</style>
