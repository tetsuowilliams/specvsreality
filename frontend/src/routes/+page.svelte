<script lang="ts">
	import { goto } from '$app/navigation';
	import { getAppContext } from '$lib/appContext';

	const app = getAppContext();

	$effect(() => {
		const repos = app.getRepos();
		if (repos.length > 0) {
			void goto(`/repos/${repos[0].id}`);
		}
	});
</script>

<section class="welcome">
	<h1>Spec vs Reality</h1>
	<p>Track specifications against implementation across your repositories.</p>
	{#if app.getRepos().length === 0}
		<button type="button" class="primary" onclick={() => app.openAddRepo()}>
			Add your first repository
		</button>
	{:else}
		<p class="muted">Loading workspace…</p>
	{/if}
</section>

<style>
	.welcome {
		max-width: 36rem;
		margin: 4rem auto;
		padding: 2rem;
		text-align: center;
	}

	h1 {
		margin: 0 0 0.5rem;
		font-size: 1.6rem;
		letter-spacing: -0.02em;
	}

	p {
		margin: 0 0 1rem;
		color: #64748b;
	}

	.primary {
		border: none;
		background: #2563eb;
		color: #fff;
		border-radius: 0.5rem;
		padding: 0.6rem 1rem;
		font-size: 0.9rem;
		font-weight: 500;
		cursor: pointer;
	}

	.muted {
		font-size: 0.88rem;
	}
</style>
