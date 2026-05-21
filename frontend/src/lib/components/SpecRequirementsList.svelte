<script lang="ts">
	import type { SpecRequirementStatusItem } from '$lib/api/repoCatalog';
	import {
		IMPLEMENTATION_STATUS_THEMES,
		countByStatus,
		resolveImplementationStatus,
		type ImplementationDisplayStatus
	} from '$lib/gantt/implementationStatus';

	let {
		repoId,
		specId,
		requirements
	}: {
		repoId: string;
		specId: string;
		requirements: SpecRequirementStatusItem[];
	} = $props();

	const counts = $derived(countByStatus(requirements));
	const total = $derived(requirements.length);

	const kpiOrder: ImplementationDisplayStatus[] = [
		'implemented',
		'not_implemented',
		'unevaluated',
		'no_version'
	];

	function ganttHref(reqId: number): string {
		return `/repos/${repoId}/spec/${specId}/gantt?requirement_id=${reqId}`;
	}
</script>

<section class="dashboard" aria-label="Requirements implementation status">
	<header class="dashboard-header">
		<div>
			<h3 class="dashboard-title">Implementation overview</h3>
			<p class="dashboard-sub">
				Latest evaluation per requirement · {total} total
			</p>
		</div>
	</header>

	{#if requirements.length === 0}
		<div class="empty-card">
			<p>No requirements for this spec yet. Run a scan to populate the catalog.</p>
		</div>
	{:else}
		<div class="kpi-grid" role="group" aria-label="Status summary">
			{#each kpiOrder as status}
				{@const theme = IMPLEMENTATION_STATUS_THEMES[status]}
				<div
					class="kpi-card"
					style:--kpi-accent={theme.accent}
					style:--kpi-muted={theme.accentMuted}
				>
					<span class="kpi-value">{counts[status]}</span>
					<span class="kpi-label">{theme.label}</span>
				</div>
			{/each}
		</div>

		<div class="table-card">
			<div class="table-head">
				<span>Requirement</span>
				<span>Status</span>
				<span class="col-action">Action</span>
			</div>
			<ul class="table-body">
				{#each requirements as req}
					{@const status = resolveImplementationStatus(req.implemented, req.has_version)}
					{@const theme = IMPLEMENTATION_STATUS_THEMES[status]}
					<li
						class="table-row"
						data-status={status}
						style:--row-bg={theme.rowBg}
						style:--row-border={theme.rowBorder}
						style:--row-accent={theme.accent}
						style:--pill-bg={theme.pillBg}
						style:--pill-fg={theme.pillFg}
					>
						<div class="cell-req">
							<span class="req-paper">{req.paper_id}</span>
						</div>
						<div class="cell-status">
							<span class="status-pill">
								<span class="status-pill-dot" aria-hidden="true"></span>
								{theme.label}
							</span>
						</div>
						<div class="cell-action">
							{#if req.has_version}
								<a class="action-link" href={ganttHref(req.id)}>View timeline</a>
							{:else}
								<span class="action-muted">—</span>
							{/if}
						</div>
					</li>
				{/each}
			</ul>
		</div>
	{/if}
</section>

<style>
	.dashboard {
		margin: 0 0 1.5rem 0;
		padding: 0;
	}

	.dashboard-header {
		margin-bottom: 1rem;
	}

	.dashboard-title {
		margin: 0;
		font-size: 1.05rem;
		font-weight: 700;
		letter-spacing: -0.02em;
		color: #0f172a;
	}

	.dashboard-sub {
		margin: 0.2rem 0 0 0;
		font-size: 0.8rem;
		color: #64748b;
	}

	.empty-card {
		padding: 1.25rem 1rem;
		border: 1px dashed #cbd5e1;
		border-radius: 0.65rem;
		background: #f8fafc;
		color: #64748b;
		font-size: 0.88rem;
	}

	.empty-card p {
		margin: 0;
	}

	.kpi-grid {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: 0.65rem;
		margin-bottom: 1rem;
	}

	@media (max-width: 720px) {
		.kpi-grid {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}

	.kpi-card {
		padding: 0.85rem 1rem;
		border-radius: 0.65rem;
		border: 1px solid #e2e8f0;
		background: var(--kpi-muted);
		box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
		display: flex;
		flex-direction: column;
		gap: 0.15rem;
	}

	.kpi-value {
		font-size: 1.65rem;
		font-weight: 700;
		line-height: 1.1;
		color: var(--kpi-accent);
		font-variant-numeric: tabular-nums;
		letter-spacing: -0.03em;
	}

	.kpi-label {
		font-size: 0.7rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: #475569;
	}

	.table-card {
		border: 1px solid #e2e8f0;
		border-radius: 0.75rem;
		overflow: hidden;
		background: #fff;
		box-shadow:
			0 1px 3px rgba(15, 23, 42, 0.06),
			0 4px 12px rgba(15, 23, 42, 0.04);
	}

	.table-head,
	.table-row {
		display: grid;
		grid-template-columns: 1fr minmax(9rem, 11rem) 7.5rem;
		align-items: center;
		gap: 0.75rem;
		padding: 0.65rem 1rem;
	}

	.table-head {
		font-size: 0.68rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: #64748b;
		background: #f8fafc;
		border-bottom: 1px solid #e2e8f0;
	}

	.table-body {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.table-row {
		border-bottom: 1px solid #f1f5f9;
		background: var(--row-bg);
		border-left: 4px solid var(--row-accent);
		transition: background 0.12s ease;
	}

	.table-row:last-child {
		border-bottom: none;
	}

	.table-row:hover {
		filter: brightness(0.98);
	}

	.req-paper {
		font-weight: 600;
		font-size: 0.9rem;
		color: #0f172a;
		font-variant-numeric: tabular-nums;
	}

	.status-pill {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.28rem 0.55rem 0.28rem 0.4rem;
		border-radius: 999px;
		font-size: 0.72rem;
		font-weight: 700;
		letter-spacing: 0.02em;
		background: var(--pill-bg);
		color: var(--pill-fg);
		border: 1px solid var(--row-border);
		white-space: nowrap;
	}

	.status-pill-dot {
		width: 0.45rem;
		height: 0.45rem;
		border-radius: 50%;
		background: var(--row-accent);
		flex-shrink: 0;
		box-shadow: 0 0 0 2px color-mix(in srgb, var(--row-accent) 25%, transparent);
	}

	.action-link {
		font-size: 0.8rem;
		font-weight: 600;
		color: #2563eb;
		text-decoration: none;
	}

	.action-link:hover {
		text-decoration: underline;
		color: #1d4ed8;
	}

	.action-muted {
		color: #cbd5e1;
		font-size: 0.85rem;
	}

	.col-action,
	.cell-action {
		text-align: right;
	}

	@media (max-width: 540px) {
		.table-head {
			display: none;
		}
		.table-row {
			grid-template-columns: 1fr;
			gap: 0.35rem;
		}
		.cell-action {
			text-align: left;
		}
	}
</style>
