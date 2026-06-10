<script lang="ts">
	import { page } from '$app/stores';
	import { fetchLogsSidebar, type RepoLogsSidebarResponse } from '$lib/api/repoLogs';

	let { repoId }: { repoId: string } = $props();

	let sidebar = $state<RepoLogsSidebarResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	async function load() {
		loading = true;
		error = null;
		try {
			sidebar = await fetchLogsSidebar(repoId);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load logs';
			sidebar = null;
		} finally {
			loading = false;
		}
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

	function isCommitActive(commitSha: string): boolean {
		return $page.url.searchParams.get('commit_sha') === commitSha;
	}

	$effect(() => {
		void load();
	});
</script>

<aside class="log-sidebar" aria-label="Commit logs">
	<div class="sidebar-header">
		<span class="title">Commits</span>
		<p class="hint">Decision log entries per commit</p>
	</div>

	{#if loading}
		<p class="muted">Loading…</p>
	{:else if error}
		<p class="error">{error}</p>
	{:else if !sidebar || sidebar.commits.length === 0}
		<p class="muted">No commit logs yet.</p>
	{:else}
		<ul class="commit-list">
			{#each sidebar.commits as commit (commit.commit_sha)}
				<li>
					<a
						class="commit-link"
						class:active={isCommitActive(commit.commit_sha)}
						href="/repos/{repoId}/logs?commit_sha={commit.commit_sha}"
					>
						<span class="commit-meta">
							<span class="commit-line">
								<code class="sha">{shortSha(commit.commit_sha)}</code>
								<span class="date">{formatDate(commit.committed_at)}</span>
								<span class="count">{commit.log_count} log{commit.log_count === 1 ? '' : 's'}</span>
							</span>
							<span class="message">{commit.commit_message}</span>
						</span>
					</a>
				</li>
			{/each}
		</ul>
	{/if}
</aside>

<style>
	.log-sidebar {
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

	.muted {
		padding: 0 0.75rem;
		font-size: 0.78rem;
		color: #94a3b8;
	}

	.error {
		padding: 0 0.75rem;
		font-size: 0.78rem;
		color: #b91c1c;
	}

	.commit-list {
		list-style: none;
		margin: 0;
		padding: 0 0.35rem 0.75rem;
		display: grid;
		gap: 0.2rem;
	}

	.commit-link {
		display: block;
		text-decoration: none;
		color: inherit;
		padding: 0.45rem 0.5rem;
		border-radius: 0.4rem;
	}

	.commit-link:hover {
		background: #f8fafc;
	}

	.commit-link.active {
		background: #eff6ff;
	}

	.commit-meta {
		display: grid;
		gap: 0.2rem;
	}

	.commit-line {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		flex-wrap: wrap;
	}

	.sha {
		font-size: 0.7rem;
		color: #475569;
	}

	.date,
	.count {
		font-size: 0.68rem;
		color: #94a3b8;
	}

	.message {
		font-size: 0.76rem;
		color: #334155;
		line-height: 1.35;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
</style>
