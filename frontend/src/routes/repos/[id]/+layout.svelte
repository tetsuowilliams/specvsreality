<script lang="ts">
	import SpecSidebar from '$lib/components/SpecSidebar.svelte';
	import { getAppContext } from '$lib/appContext';
	import { getRepo, type Repo } from '$lib/api/repos';
	import { setRepoContext } from '$lib/repoContext';

	const app = getAppContext();

	let { data, children }: { data: { id: string }; children: import('svelte').Snippet } = $props();

	let repo = $state<Repo | null>(null);
	let repoLoading = $state(true);
	let repoError = $state<string | null>(null);

	setRepoContext({
		getRepo: () => repo,
		getRepoId: () => data.id
	});

	async function loadRepo() {
		repoLoading = true;
		repoError = null;
		try {
			repo = await getRepo(data.id);
			await app.refreshRepos();
		} catch (e) {
			repoError = e instanceof Error ? e.message : 'Failed to load repository';
			repo = null;
		} finally {
			repoLoading = false;
		}
	}

	$effect(() => {
		void loadRepo();
	});
</script>

<div class="repo-workspace">
	<SpecSidebar repoId={data.id} />
	<section class="repo-main">
		{#if repoLoading}
			<p class="repo-loading-hint" aria-live="polite">Loading repository…</p>
		{:else if repoError}
			<p class="repo-error">{repoError}</p>
		{:else if repo?.clone_error}
			<div class="repo-clone-error-banner" role="alert">
				<strong>Repository initialization failed</strong>
				<pre class="repo-clone-error-detail">{repo.clone_error}</pre>
			</div>
		{:else if repo && !repo.cursor_position}
			<p class="repo-loading-hint" aria-live="polite">Initializing repository…</p>
		{/if}
		{@render children()}
	</section>
</div>

<style>
	.repo-workspace {
		display: flex;
		min-height: calc(100vh - 3.25rem);
	}

	.repo-main {
		flex: 1;
		min-width: 0;
		padding: 1rem 1.15rem 1.5rem;
		overflow: auto;
	}

	.repo-loading-hint {
		margin: 0 0 0.5rem;
		font-size: 0.8rem;
		color: #94a3b8;
	}

	.repo-error {
		margin: 0 0 0.5rem;
		font-size: 0.8rem;
		color: #b91c1c;
	}

	.repo-clone-error-banner {
		margin: 0 0 0.75rem;
		padding: 0.75rem 0.85rem;
		border: 1px solid #fecaca;
		border-radius: 0.5rem;
		background: #fef2f2;
		color: #7f1d1d;
	}

	.repo-clone-error-banner strong {
		display: block;
		margin-bottom: 0.35rem;
		font-size: 0.82rem;
	}

	.repo-clone-error-detail {
		margin: 0;
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
		font-size: 0.75rem;
		line-height: 1.45;
		white-space: pre-wrap;
		word-break: break-word;
	}
</style>
