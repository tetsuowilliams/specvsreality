<script lang="ts">
	import { page } from '$app/stores';
	import HealthIcon from '$lib/components/HealthIcon.svelte';
	import { fetchRepoSidebar, type RepoSidebarResponse } from '$lib/api/repoDashboard';

	let { repoId }: { repoId: string } = $props();

	let sidebar = $state<RepoSidebarResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let expanded = $state<Record<number, boolean>>({});

	async function load() {
		loading = true;
		error = null;
		try {
			sidebar = await fetchRepoSidebar(repoId);
			expanded = Object.fromEntries(sidebar.specs.map((spec) => [spec.id, true]));
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load specs';
			sidebar = null;
		} finally {
			loading = false;
		}
	}

	function toggleSpec(specId: number) {
		expanded[specId] = !expanded[specId];
	}

	function shortSha(sha: string): string {
		return sha.slice(0, 7);
	}

	function formatDate(value: string): string {
		return new Intl.DateTimeFormat(undefined, {
			month: 'short',
			day: 'numeric',
			year: 'numeric'
		}).format(new Date(value));
	}

	function statusTitle(status: string): string {
		if (status === 'good') return 'Implemented — all tracked items satisfied at this commit';
		if (status === 'at_risk') return 'At risk — mandatory gaps or low coverage at this commit';
		return 'Unknown — not evaluated at this commit';
	}

	function isVersionActive(specId: number, commitSha: string): boolean {
		const onSpec = $page.url.pathname.startsWith(`/repos/${repoId}/spec/${specId}`);
		return onSpec && $page.url.searchParams.get('commit_sha') === commitSha;
	}

	$effect(() => {
		void load();
	});
</script>

<aside class="spec-sidebar" aria-label="Specs">
	<div class="sidebar-header">
		<span class="title">Specs</span>
		<p class="hint">Commit health for each spec version</p>
	</div>

	{#if loading}
		<p class="muted">Loading…</p>
	{:else if error}
		<p class="error">{error}</p>
	{:else if !sidebar || sidebar.specs.length === 0}
		<p class="muted">No specs tracked yet.</p>
	{:else}
		<ul class="spec-list">
			{#each sidebar.specs as spec (spec.id)}
				{@const specActive = $page.url.pathname.startsWith(`/repos/${repoId}/spec/${spec.id}`)}
				<li class="spec-group">
					<div class="spec-row" class:active={specActive}>
						<button
							type="button"
							class="expand"
							aria-label={expanded[spec.id] ? 'Collapse' : 'Expand'}
							onclick={() => toggleSpec(spec.id)}
						>
							{expanded[spec.id] ? '▾' : '▸'}
						</button>
						<a class="spec-link" href="/repos/{repoId}/spec/{spec.id}">
							<span class="spec-title">{spec.title}</span>
							{#if spec.title !== spec.paper_id}
								<span class="paper-id">{spec.paper_id}</span>
							{/if}
						</a>
					</div>
					{#if expanded[spec.id] && spec.versions.length > 0}
						<ul class="version-list">
							{#each spec.versions as version (version.commit_sha)}
								<li>
									<a
										class="version-link"
										class:active={isVersionActive(spec.id, version.commit_sha)}
										href="/repos/{repoId}/spec/{spec.id}?commit_sha={version.commit_sha}"
										title={statusTitle(version.status)}
									>
										<HealthIcon status={version.status} />
										<span class="version-meta">
											<span class="commit-line">
												<code class="sha">{shortSha(version.commit_sha)}</code>
												<span class="date">{formatDate(version.committed_at)}</span>
											</span>
											<span class="message">{version.commit_message}</span>
										</span>
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

<style>
	.spec-sidebar {
		width: 16.5rem;
		flex-shrink: 0;
		background: #fff;
		border-right: 1px solid #e2e8f0;
		display: flex;
		flex-direction: column;
		min-height: 0;
		overflow: auto;
	}

	.sidebar-header {
		padding: 0.75rem 0.75rem 0.45rem;
	}

	.title {
		font-size: 0.72rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: #94a3b8;
	}

	.hint {
		margin: 0.2rem 0 0;
		font-size: 0.68rem;
		color: #94a3b8;
		line-height: 1.3;
	}

	.spec-list {
		list-style: none;
		margin: 0;
		padding: 0 0.35rem 0.75rem;
		display: grid;
		gap: 0.2rem;
	}

	.spec-row {
		display: flex;
		align-items: flex-start;
		gap: 0.15rem;
		border-radius: 0.4rem;
	}

	.spec-row.active {
		background: #eff6ff;
	}

	.expand {
		border: none;
		background: transparent;
		color: #64748b;
		cursor: pointer;
		width: 1.25rem;
		font-size: 0.7rem;
		padding: 0.35rem 0 0;
		flex-shrink: 0;
	}

	.spec-link {
		flex: 1;
		display: grid;
		gap: 0.1rem;
		padding: 0.35rem 0.4rem 0.35rem 0;
		text-decoration: none;
		color: #0f172a;
		min-width: 0;
	}

	.spec-title {
		font-size: 0.82rem;
		font-weight: 600;
		line-height: 1.3;
		overflow: hidden;
		text-overflow: ellipsis;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
	}

	.paper-id {
		font-size: 0.68rem;
		font-family: ui-monospace, monospace;
		color: #94a3b8;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.version-list {
		list-style: none;
		margin: 0;
		padding: 0.1rem 0 0.2rem 1.2rem;
		display: grid;
		gap: 0.1rem;
	}

	.version-link {
		display: flex;
		align-items: flex-start;
		gap: 0.4rem;
		padding: 0.3rem 0.4rem;
		border-radius: 0.35rem;
		text-decoration: none;
		color: #475569;
	}

	.version-link:hover {
		background: #f8fafc;
	}

	.version-link.active {
		background: #eff6ff;
		color: #1d4ed8;
	}

	.version-meta {
		display: grid;
		gap: 0.05rem;
		min-width: 0;
	}

	.commit-line {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		flex-wrap: wrap;
	}

	.sha {
		font-family: ui-monospace, monospace;
		font-size: 0.72rem;
		font-weight: 600;
		color: inherit;
	}

	.date {
		font-size: 0.68rem;
		color: #94a3b8;
		white-space: nowrap;
	}

	.version-link.active .date {
		color: #60a5fa;
	}

	.message {
		font-size: 0.68rem;
		color: #64748b;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.version-link.active .message {
		color: #3b82f6;
	}

	.muted {
		margin: 0;
		padding: 0.5rem 0.75rem;
		font-size: 0.8rem;
		color: #64748b;
	}

	.error {
		margin: 0;
		padding: 0.5rem 0.75rem;
		font-size: 0.8rem;
		color: #b91c1c;
	}
</style>
