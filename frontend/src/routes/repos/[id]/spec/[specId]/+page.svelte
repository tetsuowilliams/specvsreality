<script lang="ts">
	import SpecRequirementsList from '$lib/components/SpecRequirementsList.svelte';
	import { fetchSpecDetail, type SpecDetailResponse } from '$lib/api/repoCatalog';

	let { data }: { data: { id: string; specId: string } } = $props();

	let detail = $state<SpecDetailResponse | null>(null);
	let loading = $state(true);
	let err = $state<string | null>(null);

	async function load() {
		loading = true;
		err = null;
		try {
			detail = await fetchSpecDetail(data.id, data.specId);
		} catch (e) {
			err = e instanceof Error ? e.message : 'Failed to load spec';
			detail = null;
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		void load();
	});
</script>

{#if loading}
	<p>Loading spec…</p>
{:else if err}
	<p class="error">{err}</p>
{:else if detail}
	<section class="spec-detail">
		<header class="spec-header">
			<div>
				<h2>Spec</h2>
				<p class="paper"><span class="label">Paper id</span> <strong>{detail.paper_id}</strong></p>
			</div>
		</header>
		<SpecRequirementsList
			repoId={data.id}
			specId={data.specId}
			requirements={detail.requirements ?? []}
		/>
		<h3>Versions</h3>
		{#if detail.versions.length === 0}
			<p class="muted">No spec versions yet.</p>
		{:else}
			<div class="versions">
				{#each detail.versions as v, i}
					<details class="version" open={i === 0}>
						<summary>Version #{v.id}</summary>
						<div class="md-block">
							<h4>spec.md</h4>
							<pre>{v.spec_md}</pre>
							<h4>tasks.md</h4>
							<pre>{v.tasks_md ?? ''}</pre>
							<h4>plan.md</h4>
							<pre>{v.plan_md ?? ''}</pre>
						</div>
					</details>
				{/each}
			</div>
		{/if}
	</section>
{/if}

<style>
	.spec-header {
		margin-bottom: 0.25rem;
	}
	.spec-detail h2 {
		margin: 0 0 0.35rem 0;
		font-size: 1.35rem;
		font-weight: 700;
		letter-spacing: -0.02em;
		color: #0f172a;
	}
	.spec-detail h3 {
		margin: 1.25rem 0 0.5rem 0;
		font-size: 0.95rem;
		font-weight: 600;
		color: #334155;
	}
	.paper {
		margin: 0;
		font-size: 0.88rem;
	}
	.label {
		color: #64748b;
		margin-right: 0.35rem;
	}
	.versions {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}
	.version {
		border: 1px solid #e2e8f0;
		border-radius: 0.5rem;
		padding: 0.35rem 0.5rem;
		background: #fafafa;
	}
	.version summary {
		cursor: pointer;
		font-weight: 600;
		color: #0f172a;
	}
	.md-block {
		margin-top: 0.5rem;
	}
	.md-block h4 {
		margin: 0.5rem 0 0.2rem 0;
		font-size: 0.82rem;
		color: #475569;
	}
	pre {
		margin: 0 0 0.35rem 0;
		padding: 0.5rem;
		background: #fff;
		border: 1px solid #e5e7eb;
		border-radius: 0.35rem;
		font-size: 0.78rem;
		overflow: auto;
		max-height: 14rem;
		white-space: pre-wrap;
		word-break: break-word;
	}
	.error {
		color: #9a1c1c;
	}
	.muted {
		color: #64748b;
	}
</style>
