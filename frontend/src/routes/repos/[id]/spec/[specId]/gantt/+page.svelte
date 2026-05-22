<script lang="ts">
	import { page } from '$app/stores';
	import GanttChart from '$lib/components/GanttChart.svelte';
	import RequirementVersionTree from '$lib/components/RequirementVersionTree.svelte';
	import {
		fetchGanttChart,
		fetchRequirementVersionTree,
		type GanttChartResponse,
		type RequirementVersionTreeResponse
	} from '$lib/api/repoCatalog';

	let chart = $state<GanttChartResponse | null>(null);
	let versionTree = $state<RequirementVersionTreeResponse | null>(null);
	let loading = $state(true);
	let err = $state<string | null>(null);

	async function load(
		repoId: string,
		specId: string,
		requirementId: string | null
	) {
		loading = true;
		err = null;
		try {
			const rid = requirementId && requirementId.length > 0 ? requirementId : null;
			const [c, tree] = await Promise.all([
				fetchGanttChart(repoId, specId, { requirementId: rid }),
				fetchRequirementVersionTree(repoId, specId, { requirementId: rid })
			]);
			chart = c;
			versionTree = tree;
		} catch (e) {
			err = e instanceof Error ? e.message : 'Failed to load requirement view';
			chart = null;
			versionTree = null;
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		const repoId = $page.params.id;
		const specId = $page.params.specId;
		const requirementId = $page.url.searchParams.get('requirement_id');
		if (!repoId || !specId) return;
		void load(repoId, specId, requirementId);
	});
</script>

{#if loading}
	<p>Loading requirement…</p>
{:else if err}
	<p class="error">{err}</p>
{:else if chart && versionTree}
	<section class="gantt-page">
		<h2>Requirement · {chart.requirement.paper_id}</h2>
		<p class="sub">
			Spec <code>{$page.params.specId}</code> — version history and implementing artifacts, then timeline.
		</p>
		<RequirementVersionTree tree={versionTree} />
		<h3 class="gantt-heading">Timeline</h3>
		<GanttChart {chart} {versionTree} />
	</section>
{/if}

<style>
	.gantt-page {
		max-width: 100%;
		min-width: 0;
	}
	.gantt-page h2 {
		margin: 0 0 0.35rem 0;
		font-size: 1.2rem;
	}
	.gantt-heading {
		margin: 0 0 0.75rem 0;
		font-size: 0.95rem;
		color: #334155;
	}
	.sub {
		margin: 0 0 1rem 0;
		font-size: 0.88rem;
		color: #64748b;
	}
	code {
		background: #f1f5f9;
		padding: 0.1rem 0.35rem;
		border-radius: 0.25rem;
	}
	.error {
		color: #9a1c1c;
		white-space: pre-wrap;
	}
</style>
