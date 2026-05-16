<script lang="ts">
	import { getRepoContext } from '$lib/repoContext';

	const { getRepo } = getRepoContext();
	const repo = $derived(getRepo());
</script>

{#if repo}
	<section class="dashboard">
		<h2>Repository</h2>
		<p class="subtitle">Tracked clone metadata (scanning implementation is not wired yet).</p>
		<dl class="meta">
			<dt>Cursor / HEAD</dt>
			<dd><code>{repo.cursor_position || '—'}</code></dd>
			<dt>Clone location</dt>
			<dd><code>{repo.location || '—'}</code></dd>
		</dl>
	</section>
{/if}

<style>
	.dashboard h2 {
		margin: 0;
		font-size: 1.35rem;
		letter-spacing: -0.01em;
	}
	.subtitle {
		color: #4b5563;
		margin: 0.35rem 0 1rem 0;
		font-size: 0.92rem;
	}
	.meta {
		display: grid;
		grid-template-columns: 10rem 1fr;
		gap: 0.5rem 1rem;
		margin: 0;
		font-size: 0.92rem;
	}
	.meta dt {
		margin: 0;
		color: #64748b;
		font-weight: 500;
	}
	.meta dd {
		margin: 0;
		word-break: break-all;
	}
</style>
