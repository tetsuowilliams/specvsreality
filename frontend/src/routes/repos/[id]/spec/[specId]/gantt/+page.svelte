<script lang="ts">
	import { page } from '$app/stores';
	import GanttChart from '$lib/components/GanttChart.svelte';
	import {
		fetchGanttChart,
		fetchRequirementLatestVersion,
		type GanttChartResponse,
		type RequirementLatestVersionResponse
	} from '$lib/api/repoCatalog';

	let chart = $state<GanttChartResponse | null>(null);
	let latestVersion = $state<RequirementLatestVersionResponse | null>(null);
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
			const [c, lv] = await Promise.all([
				fetchGanttChart(repoId, specId, { requirementId: rid }),
				fetchRequirementLatestVersion(repoId, specId, { requirementId: rid }).catch(() => null)
			]);
			chart = c;
			latestVersion = lv;
		} catch (e) {
			err = e instanceof Error ? e.message : 'Failed to load Gantt chart';
			chart = null;
			latestVersion = null;
		} finally {
			loading = false;
		}
	}

	// Use $page.params + searchParams together so we never pair a new requirement_id
	// with a stale spec id from $props() (that can lag the URL for one tick).
	$effect(() => {
		const repoId = $page.params.id;
		const specId = $page.params.specId;
		const requirementId = $page.url.searchParams.get('requirement_id');
		if (!repoId || !specId) return;
		void load(repoId, specId, requirementId);
	});
</script>

{#if loading}
	<p>Loading Gantt chart…</p>
{:else if err}
	<p class="error">{err}</p>
{:else if chart}
	<section class="gantt-page">
		<h2>Gantt</h2>
		<p class="sub">
			Spec <code>{$page.params.specId}</code> — requirement <code>{chart.requirement.paper_id}</code> and
			implementing artifacts.
		</p>
		{#if latestVersion}
			<section class="latest-req" aria-label="Latest requirement text">
				<h3 class="latest-req-title">Requirement (latest version)</h3>
				<pre class="latest-req-body">{latestVersion.requirement_text}</pre>
				<p class="latest-req-meta">
					Commit <code class="mono">{latestVersion.commit_id.slice(0, 7)}</code>
					· {new Date(latestVersion.commit_datetime).toLocaleString()}
				</p>
			</section>
		{/if}
		<GanttChart {chart} />
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
	.latest-req {
		margin: 0 0 1.1rem 0;
		padding: 0.75rem 0.85rem;
		border: 1px solid #e2e8f0;
		border-radius: 0.5rem;
		background: #fafbfc;
		min-width: 0;
	}
	.latest-req-title {
		margin: 0 0 0.5rem 0;
		font-size: 0.82rem;
		font-weight: 600;
		color: #475569;
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}
	.latest-req-body {
		margin: 0;
		padding: 0;
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
		font-size: 0.8rem;
		line-height: 1.45;
		white-space: pre-wrap;
		word-break: break-word;
		color: #0f172a;
		background: transparent;
		border: none;
		max-height: 18rem;
		overflow: auto;
	}
	.latest-req-meta {
		margin: 0.55rem 0 0 0;
		font-size: 0.75rem;
		color: #64748b;
	}
	.mono {
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
		font-size: 0.72em;
	}
</style>
