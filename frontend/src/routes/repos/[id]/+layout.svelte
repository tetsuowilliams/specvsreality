<script lang="ts">
	import SpecSidebar from '$lib/components/SpecSidebar.svelte';
	import { getRepo, type Repo } from '$lib/api/repos';
	import { setRepoContext } from '$lib/repoContext';

	let { data, children }: { data: { id: string }; children: import('svelte').Snippet } = $props();

	let repo = $state<Repo | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	setRepoContext({
		getRepo: () => repo,
		getRepoId: () => data.id
	});

	async function loadRepo() {
		loading = true;
		error = null;
		try {
			repo = await getRepo(data.id);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load repository';
			repo = null;
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		void loadRepo();
	});
</script>

{#if loading}
	<div class="workspace-state">Loading repository…</div>
{:else if error}
	<div class="workspace-state error">{error}</div>
{:else}
	<div class="repo-workspace">
		<SpecSidebar repoId={data.id} />
		<section class="repo-main">
			{@render children()}
		</section>
	</div>
{/if}

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

	.workspace-state {
		padding: 2rem 1.15rem;
		color: #64748b;
	}

	.workspace-state.error {
		color: #b91c1c;
	}
</style>
