<script lang="ts">
	import { fetchRepoDashboard, type RepoDashboardResponse } from '$lib/api/repoDashboard';
	import HelpTip from '$lib/components/HelpTip.svelte';
	import MetricCard from '$lib/components/MetricCard.svelte';
	import { DASHBOARD_METRICS, statusHelp } from '$lib/dashboard/metrics';

	let { repoId }: { repoId: string } = $props();

	let dashboard = $state<RepoDashboardResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	async function load() {
		loading = true;
		error = null;
		try {
			dashboard = await fetchRepoDashboard(repoId);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load dashboard';
			dashboard = null;
		} finally {
			loading = false;
		}
	}

	function shortSha(sha: string | null): string {
		return sha ? sha.slice(0, 7) : '—';
	}

	function formatDate(value: string | null): string {
		if (!value) return '—';
		return new Intl.DateTimeFormat(undefined, {
			month: 'short',
			day: 'numeric',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		}).format(new Date(value));
	}

	function statusClass(status: string): string {
		if (status === 'good') return 'good';
		if (status === 'mostly_implemented') return 'amber';
		if (status === 'at_risk') return 'bad';
		return 'neutral';
	}

	$effect(() => {
		void load();
	});
</script>

{#if loading}
	<div class="state">Loading dashboard…</div>
{:else if error}
	<div class="state error">{error}</div>
{:else if dashboard}
	<div class="dashboard">
		<header class="dash-header">
			<div>
				<h1>{dashboard.repo_name}</h1>
				<p class="subtitle">
					{#if dashboard.summary.latest_commit_sha}
						Latest analysed commit
						<code>{shortSha(dashboard.summary.latest_commit_sha)}</code>
						{#if dashboard.summary.latest_commit_message}
							· {dashboard.summary.latest_commit_message}
						{/if}
					{:else}
						No commits analysed yet
					{/if}
				</p>
			</div>
		</header>

		<p class="intro">
			Implementation health at a glance. Counts use each spec item’s <strong>latest evaluation</strong>
			and include <strong>must</strong> and <strong>should</strong> items only unless noted.
		</p>

		<section class="summary-grid">
			<MetricCard metric={DASHBOARD_METRICS.specs_tracked} value={dashboard.summary.specs_tracked} />
			<MetricCard
				metric={DASHBOARD_METRICS.latest_commit}
				value={shortSha(dashboard.summary.latest_commit_sha)}
				mono
			/>
			<MetricCard
				metric={DASHBOARD_METRICS.coverage}
				value={dashboard.summary.coverage_percent != null
					? `${dashboard.summary.coverage_percent}%`
					: '—'}
			/>
			<MetricCard
				metric={DASHBOARD_METRICS.missing}
				value={dashboard.summary.missing_items}
				warn={dashboard.summary.missing_items > 0}
			/>
			<MetricCard
				metric={DASHBOARD_METRICS.low_confidence}
				value={dashboard.summary.low_confidence_items}
				warn={dashboard.summary.low_confidence_items > 0}
			/>
			<MetricCard
				metric={DASHBOARD_METRICS.candidates}
				value={dashboard.summary.candidate_artifacts}
			/>
		</section>

		<section class="panel">
			<div class="panel-header">
				<h2>Specs overview</h2>
				<p class="panel-desc">{DASHBOARD_METRICS.status.short}</p>
			</div>
			{#if dashboard.specs.length === 0}
				<p class="empty">No specs tracked yet.</p>
			{:else}
				<div class="table-wrap">
					<table>
						<thead>
							<tr>
								<th>Spec</th>
								<th>Version</th>
								<th><HelpTip {...DASHBOARD_METRICS.status} inline /></th>
								<th><HelpTip {...DASHBOARD_METRICS.satisfied} inline /></th>
								<th><HelpTip {...DASHBOARD_METRICS.missing} inline /></th>
								<th><HelpTip {...DASHBOARD_METRICS.low_confidence} inline /></th>
								<th><HelpTip {...DASHBOARD_METRICS.candidates} inline /></th>
								<th>Last evaluated</th>
							</tr>
						</thead>
						<tbody>
							{#each dashboard.specs as row (row.spec_id)}
								<tr>
									<td>
										<a href="/repos/{repoId}/spec/{row.spec_id}" class="spec-link">
											{row.paper_id}
										</a>
									</td>
									<td class="mono">{shortSha(row.latest_commit_sha)}</td>
									<td>
										<span
											class="pill {statusClass(row.status)}"
											title={statusHelp(row.status).detail}
										>
											{statusHelp(row.status).label}
										</span>
									</td>
									<td>{row.satisfied}</td>
									<td>{row.missing}</td>
									<td>{row.low_confidence}</td>
									<td>{row.candidate_artifacts}</td>
									<td class="time">
										{#if row.last_evaluated_commit_sha}
											<code>{shortSha(row.last_evaluated_commit_sha)}</code>
											<span>{formatDate(row.last_evaluated_at)}</span>
										{:else}
											—
										{/if}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
		</section>

		<div class="two-col">
			<section class="panel">
				<div class="panel-header">
					<h2>Needs attention</h2>
					<p class="panel-desc">{DASHBOARD_METRICS.needs_attention.detail}</p>
				</div>
				{#if dashboard.needs_attention.length === 0}
					<p class="empty">Nothing urgent right now.</p>
				{:else}
					<ul class="attention-list">
						{#each dashboard.needs_attention as item (item.spec_id + item.detail)}
							<li class="attention-item severity-{item.severity}">
								<a href="/repos/{repoId}/spec/{item.spec_id}">
									<strong>{item.headline}</strong>
									<span>{item.detail}</span>
								</a>
							</li>
						{/each}
					</ul>
				{/if}
			</section>

			<section class="panel">
				<div class="panel-header">
					<h2>Recent changes</h2>
					<p class="panel-desc">{DASHBOARD_METRICS.recent_changes.detail}</p>
				</div>
				{#if dashboard.recent_changes.length === 0}
					<p class="empty">No recent changes detected.</p>
				{:else}
					<ul class="changes-list">
						{#each dashboard.recent_changes as change (change.commit_sha + change.message)}
							<li>
								<a href="/repos/{repoId}/spec/{change.spec_id}">
									<span class="change-msg">{change.message}</span>
									<span class="change-meta">
										<code>{shortSha(change.commit_sha)}</code>
										· {formatDate(change.committed_at)}
									</span>
								</a>
							</li>
						{/each}
					</ul>
				{/if}
			</section>
		</div>

		<section class="panel">
			<div class="panel-header">
				<h2>Artifact activity</h2>
				<p class="panel-desc">{DASHBOARD_METRICS.artifact_activity.detail}</p>
			</div>
			{#if dashboard.artifact_activity.length === 0}
				<p class="empty">No candidate artifacts or evidence links yet.</p>
			{:else}
				<ul class="artifact-list">
					{#each dashboard.artifact_activity as artifact (artifact.filepath + artifact.link_type)}
						<li>
							<code class="filepath">{artifact.filepath}</code>
							<span class="artifact-label">{artifact.label}</span>
						</li>
					{/each}
				</ul>
			{/if}
		</section>
	</div>
{/if}

<style>
	.dashboard {
		display: grid;
		gap: 1rem;
	}

	.dash-header h1 {
		margin: 0;
		font-size: 1.35rem;
		font-weight: 700;
		letter-spacing: -0.02em;
		color: #0f172a;
	}

	.subtitle {
		margin: 0.35rem 0 0;
		font-size: 0.84rem;
		color: #64748b;
	}

	.intro {
		margin: 0;
		font-size: 0.84rem;
		color: #475569;
		line-height: 1.45;
	}

	.summary-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
		gap: 0.65rem;
	}

	.mono,
	code {
		font-family: ui-monospace, monospace;
	}

	.panel {
		background: #fff;
		border: 1px solid #e2e8f0;
		border-radius: 0.75rem;
		padding: 0.85rem 1rem;
	}

	.panel-header h2 {
		margin: 0;
		font-size: 0.92rem;
		font-weight: 600;
		color: #334155;
	}

	.panel-desc {
		margin: 0.3rem 0 0.65rem;
		font-size: 0.78rem;
		color: #64748b;
		line-height: 1.4;
	}

	.table-wrap {
		overflow: auto;
	}

	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.8rem;
	}

	th,
	td {
		padding: 0.5rem 0.45rem;
		text-align: left;
		border-bottom: 1px solid #f1f5f9;
		vertical-align: top;
	}

	th {
		font-size: 0.72rem;
		font-weight: 600;
		color: #64748b;
		text-transform: uppercase;
		letter-spacing: 0.03em;
	}

	.spec-link {
		color: #2563eb;
		text-decoration: none;
		font-weight: 600;
	}

	.spec-link:hover {
		text-decoration: underline;
	}

	.pill {
		display: inline-block;
		padding: 0.12rem 0.45rem;
		border-radius: 999px;
		font-size: 0.68rem;
		font-weight: 600;
		text-transform: capitalize;
	}

	.pill.good {
		background: #dcfce7;
		color: #166534;
	}
	.pill.amber {
		background: #fef3c7;
		color: #92400e;
	}
	.pill.bad {
		background: #fee2e2;
		color: #991b1b;
	}
	.pill.neutral {
		background: #f1f5f9;
		color: #475569;
	}

	.time {
		display: grid;
		gap: 0.1rem;
		color: #64748b;
		font-size: 0.74rem;
	}

	.two-col {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr));
		gap: 1rem;
	}

	.attention-list,
	.changes-list,
	.artifact-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 0.45rem;
	}

	.attention-item a,
	.changes-list a {
		display: grid;
		gap: 0.1rem;
		padding: 0.55rem 0.65rem;
		border-radius: 0.5rem;
		border: 1px solid #f1f5f9;
		text-decoration: none;
		color: inherit;
	}

	.attention-item a:hover,
	.changes-list a:hover {
		background: #f8fafc;
	}

	.attention-item strong {
		font-size: 0.84rem;
		color: #0f172a;
	}

	.attention-item span,
	.change-msg {
		font-size: 0.8rem;
		color: #475569;
	}

	.change-meta {
		font-size: 0.72rem;
		color: #64748b;
	}

	.artifact-list li {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 0.75rem;
		padding: 0.45rem 0;
		border-bottom: 1px solid #f8fafc;
		font-size: 0.8rem;
	}

	.filepath {
		color: #0f172a;
	}

	.artifact-label {
		color: #64748b;
		white-space: nowrap;
	}

	.empty,
	.state {
		color: #64748b;
		font-size: 0.88rem;
		margin: 0;
	}

	.state.error,
	.error {
		color: #b91c1c;
	}
</style>
