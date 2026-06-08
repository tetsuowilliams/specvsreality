<script lang="ts">
	import {
		fetchMetricsDashboard,
		type MetricsDashboardResponse
	} from '$lib/api/metricsDashboard';
	import HelpTip from '$lib/components/HelpTip.svelte';
	import MetricCard from '$lib/components/MetricCard.svelte';
	import { AGENT_LABELS, METRICS_DASHBOARD } from '$lib/dashboard/metrics';

	let dashboard = $state<MetricsDashboardResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let selectedRepoId = $state<number | null>(null);

	async function load() {
		loading = true;
		error = null;
		try {
			dashboard = await fetchMetricsDashboard(selectedRepoId ?? undefined);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load metrics';
			dashboard = null;
		} finally {
			loading = false;
		}
	}

	function formatUsd(value: string | number): string {
		const amount = typeof value === 'string' ? Number(value) : value;
		if (!Number.isFinite(amount)) return '—';
		if (amount === 0) return '$0.00';
		if (amount < 0.01) return `$${amount.toFixed(4)}`;
		return new Intl.NumberFormat(undefined, {
			style: 'currency',
			currency: 'USD',
			minimumFractionDigits: 2,
			maximumFractionDigits: 4
		}).format(amount);
	}

	function formatTokens(value: number): string {
		if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
		if (value >= 1_000) return `${(value / 1_000).toFixed(1)}k`;
		return String(value);
	}

	function formatDate(value: string): string {
		return new Intl.DateTimeFormat(undefined, {
			month: 'short',
			day: 'numeric',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		}).format(new Date(value));
	}

	function shortSha(sha: string): string {
		return sha.slice(0, 7);
	}

	function agentLabel(agent: string): string {
		return AGENT_LABELS[agent] ?? agent;
	}

	function agentClass(agent: string): string {
		if (agent === 'spec_extraction') return 'agent-spec';
		if (agent === 'artifact_candidate') return 'agent-candidate';
		if (agent === 'implements') return 'agent-implements';
		return 'agent-default';
	}

	function selectRepo(repoId: number) {
		selectedRepoId = selectedRepoId === repoId ? null : repoId;
	}

	function clearFilter() {
		selectedRepoId = null;
	}

	const avgCostPerRun = $derived.by(() => {
		if (!dashboard || dashboard.summary.total_runs === 0) return '—';
		const total = Number(dashboard.summary.total_cost_usd);
		return formatUsd(total / dashboard.summary.total_runs);
	});

	const maxAgentCost = $derived.by(() => {
		if (!dashboard || dashboard.by_agent.length === 0) return 0;
		return Math.max(...dashboard.by_agent.map((row) => Number(row.total_cost_usd)));
	});

	$effect(() => {
		selectedRepoId;
		void load();
	});
</script>

{#if loading}
	<div class="state">Loading metrics…</div>
{:else if error}
	<div class="state error">{error}</div>
{:else if dashboard}
	<div class="dashboard">
		<header class="dash-header">
			<div>
				<h1>LLM Usage &amp; Cost</h1>
				<p class="subtitle">Token consumption and estimated spend across all agent runs.</p>
			</div>
			{#if selectedRepoId != null}
				<button type="button" class="clear-filter" onclick={clearFilter}>
					Clear repo filter
				</button>
			{/if}
		</header>

		{#if dashboard.summary.total_runs === 0}
			<section class="panel empty-panel">
				<h2>No agent runs yet</h2>
				<p>
					Metrics appear after the worker scans a repository and runs spec extraction, candidate
					discovery, or implements evaluation agents.
				</p>
			</section>
		{:else}
			<section class="summary-grid">
				<MetricCard
					metric={METRICS_DASHBOARD.total_spend}
					value={formatUsd(dashboard.summary.total_cost_usd)}
				/>
				<MetricCard
					metric={METRICS_DASHBOARD.total_tokens}
					value={formatTokens(dashboard.summary.total_tokens)}
				/>
				<MetricCard metric={METRICS_DASHBOARD.agent_runs} value={dashboard.summary.total_runs} />
				<MetricCard metric={METRICS_DASHBOARD.avg_cost_per_run} value={avgCostPerRun} />
			</section>

			<div class="two-col">
				<section class="panel">
					<div class="panel-header">
						<h2><HelpTip {...METRICS_DASHBOARD.cost_by_agent} inline /></h2>
					</div>
					<ul class="bar-chart">
						{#each dashboard.by_agent as row (row.agent)}
							{@const pct =
								maxAgentCost > 0 ? (Number(row.total_cost_usd) / maxAgentCost) * 100 : 0}
							<li>
								<div class="bar-row">
									<span class="bar-label">{agentLabel(row.agent)}</span>
									<div class="bar-track">
										<div
											class="bar-fill {agentClass(row.agent)}"
											style:width="{pct}%"
										></div>
									</div>
									<span class="bar-value">{formatUsd(row.total_cost_usd)}</span>
								</div>
								<p class="bar-meta">
									{row.run_count} runs · {formatTokens(row.total_tokens)} tokens
								</p>
							</li>
						{/each}
					</ul>
				</section>

				<section class="panel">
					<div class="panel-header">
						<h2><HelpTip {...METRICS_DASHBOARD.per_repo} inline /></h2>
					</div>
					{#if dashboard.by_repo.length === 0}
						<p class="empty">No repository totals yet.</p>
					{:else}
						<div class="table-wrap">
							<table>
								<thead>
									<tr>
										<th>Repository</th>
										<th>Runs</th>
										<th>Tokens</th>
										<th>Cost</th>
									</tr>
								</thead>
								<tbody>
									{#each dashboard.by_repo as row (row.repo_id)}
										<tr
											class="clickable"
											class:selected={selectedRepoId === row.repo_id}
											onclick={() => selectRepo(row.repo_id)}
										>
											<td>
												<a
													href="/repos/{row.repo_id}"
													class="repo-link"
													onclick={(e) => e.stopPropagation()}
												>
													{row.repo_name}
												</a>
											</td>
											<td>{row.run_count}</td>
											<td class="mono">{formatTokens(row.total_tokens)}</td>
											<td class="mono cost">{formatUsd(row.total_cost_usd)}</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					{/if}
				</section>
			</div>

			<section class="panel">
				<div class="panel-header">
					<h2><HelpTip {...METRICS_DASHBOARD.recent_runs} inline /></h2>
					{#if selectedRepoId != null}
						<p class="panel-desc">Filtered to one repository</p>
					{/if}
				</div>
				{#if dashboard.recent_runs.length === 0}
					<p class="empty">No runs match the current filter.</p>
				{:else}
					<div class="table-wrap">
						<table class="runs-table">
							<thead>
								<tr>
									<th>When</th>
									<th>Repository</th>
									<th>Commit</th>
									<th>Agent</th>
									<th>Model</th>
									<th>In</th>
									<th>Out</th>
									<th>Cost</th>
								</tr>
							</thead>
							<tbody>
								{#each dashboard.recent_runs as row (row.id)}
									<tr>
										<td class="time">{formatDate(row.ran_at)}</td>
										<td>{row.repo_name}</td>
										<td class="mono"><code>{shortSha(row.commit_sha)}</code></td>
										<td>
											<span class="pill {agentClass(row.agent)}">{agentLabel(row.agent)}</span>
										</td>
										<td class="model">{row.model}</td>
										<td class="mono">{formatTokens(row.input_tokens)}</td>
										<td class="mono">{formatTokens(row.output_tokens)}</td>
										<td class="mono cost">{formatUsd(row.cost_usd)}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{/if}
			</section>
		{/if}
	</div>
{/if}

<style>
	.dashboard {
		padding: 1.25rem 1.5rem 2rem;
		max-width: 72rem;
	}

	.dash-header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 1rem;
		margin-bottom: 1rem;
	}

	h1 {
		margin: 0;
		font-size: 1.45rem;
		letter-spacing: -0.02em;
		color: #0f172a;
	}

	.subtitle {
		margin: 0.35rem 0 0;
		color: #64748b;
		font-size: 0.9rem;
	}

	.clear-filter {
		border: 1px solid #cbd5e1;
		background: #fff;
		color: #475569;
		border-radius: 0.45rem;
		padding: 0.4rem 0.65rem;
		font-size: 0.78rem;
		cursor: pointer;
		white-space: nowrap;
	}

	.summary-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
		gap: 0.65rem;
		margin-bottom: 1rem;
	}

	.two-col {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr));
		gap: 0.85rem;
		margin-bottom: 0.85rem;
	}

	.panel {
		background: #fff;
		border: 1px solid #e2e8f0;
		border-radius: 0.75rem;
		padding: 0.9rem 1rem 1rem;
	}

	.empty-panel {
		text-align: center;
		padding: 2.5rem 1.5rem;
	}

	.empty-panel h2 {
		margin: 0 0 0.5rem;
		font-size: 1.05rem;
	}

	.empty-panel p {
		margin: 0;
		color: #64748b;
		max-width: 32rem;
		margin-inline: auto;
	}

	.panel-header {
		margin-bottom: 0.75rem;
	}

	.panel-header h2 {
		margin: 0;
		font-size: 0.95rem;
		color: #0f172a;
	}

	.panel-desc {
		margin: 0.25rem 0 0;
		font-size: 0.78rem;
		color: #94a3b8;
	}

	.bar-chart {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 0.85rem;
	}

	.bar-row {
		display: grid;
		grid-template-columns: 7.5rem 1fr auto;
		gap: 0.5rem;
		align-items: center;
	}

	.bar-label {
		font-size: 0.78rem;
		font-weight: 600;
		color: #334155;
	}

	.bar-track {
		height: 0.55rem;
		background: #f1f5f9;
		border-radius: 999px;
		overflow: hidden;
	}

	.bar-fill {
		height: 100%;
		border-radius: 999px;
		min-width: 2px;
	}

	.bar-fill.agent-spec {
		background: linear-gradient(90deg, #3b82f6, #60a5fa);
	}

	.bar-fill.agent-candidate {
		background: linear-gradient(90deg, #8b5cf6, #a78bfa);
	}

	.bar-fill.agent-implements {
		background: linear-gradient(90deg, #0d9488, #2dd4bf);
	}

	.bar-fill.agent-default {
		background: #94a3b8;
	}

	.bar-value {
		font-size: 0.78rem;
		font-family: ui-monospace, monospace;
		color: #0f172a;
	}

	.bar-meta {
		margin: 0.2rem 0 0 8rem;
		font-size: 0.72rem;
		color: #94a3b8;
	}

	.table-wrap {
		overflow-x: auto;
	}

	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.8rem;
	}

	th,
	td {
		padding: 0.45rem 0.5rem;
		text-align: left;
		border-bottom: 1px solid #f1f5f9;
	}

	th {
		font-size: 0.7rem;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: #94a3b8;
		font-weight: 600;
	}

	tbody tr.clickable {
		cursor: pointer;
	}

	tbody tr.clickable:hover {
		background: #f8fafc;
	}

	tbody tr.selected {
		background: #eff6ff;
	}

	.runs-table tbody tr {
		cursor: default;
	}

	.repo-link {
		color: #2563eb;
		text-decoration: none;
		font-weight: 600;
	}

	.repo-link:hover {
		text-decoration: underline;
	}

	.mono {
		font-family: ui-monospace, monospace;
		font-size: 0.76rem;
	}

	.cost {
		font-weight: 600;
		color: #0f172a;
	}

	.time {
		white-space: nowrap;
		color: #64748b;
	}

	.model {
		color: #64748b;
		max-width: 10rem;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.pill {
		display: inline-block;
		padding: 0.15rem 0.45rem;
		border-radius: 999px;
		font-size: 0.68rem;
		font-weight: 600;
		white-space: nowrap;
	}

	.pill.agent-spec {
		background: #dbeafe;
		color: #1d4ed8;
	}

	.pill.agent-candidate {
		background: #ede9fe;
		color: #6d28d9;
	}

	.pill.agent-implements {
		background: #ccfbf1;
		color: #0f766e;
	}

	.pill.agent-default {
		background: #f1f5f9;
		color: #475569;
	}

	.empty {
		margin: 0;
		color: #64748b;
		font-size: 0.85rem;
	}

	.state {
		padding: 2rem;
		text-align: center;
		color: #64748b;
	}

	.state.error {
		color: #b91c1c;
	}
</style>
