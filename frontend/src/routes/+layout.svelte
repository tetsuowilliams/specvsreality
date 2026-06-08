<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import AppHeader from '$lib/components/AppHeader.svelte';
	import AddRepoModal from '$lib/components/AddRepoModal.svelte';
	import RepoRail from '$lib/components/RepoRail.svelte';
	import { listRepos, type Repo } from '$lib/api/repos';
	import { setAppContext } from '$lib/appContext';

	let { children } = $props();

	let repos = $state<Repo[]>([]);
	let addRepoOpen = $state(false);

	async function refreshRepos() {
		repos = await listRepos();
	}

	setAppContext({
		getRepos: () => repos,
		refreshRepos,
		openAddRepo: () => {
			addRepoOpen = true;
		}
	});

	$effect(() => {
		void refreshRepos();
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<div class="app-shell">
	<AppHeader />
	<div class="app-body">
		<RepoRail />
		<main class="app-main">
			{@render children()}
		</main>
	</div>
</div>

<AddRepoModal
	open={addRepoOpen}
	onClose={() => {
		addRepoOpen = false;
	}}
	onCreated={refreshRepos}
/>

<style>
	.app-shell {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
		font-family: Inter, system-ui, -apple-system, 'Segoe UI', sans-serif;
		background: #f1f5f9;
	}

	.app-body {
		flex: 1;
		display: flex;
		min-height: 0;
	}

	.app-main {
		flex: 1;
		min-width: 0;
		min-height: 0;
		overflow: auto;
	}
</style>
