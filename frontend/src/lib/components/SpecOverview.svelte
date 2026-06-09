<script lang="ts">
	import type { SpecViewOverviewResponse } from '$lib/api/repoCatalog';
	import MetricCard from '$lib/components/MetricCard.svelte';
	import { DASHBOARD_METRICS, statusHelp } from '$lib/dashboard/metrics';
	import { attentionItems, type SpecItemAttention } from '$lib/spec/specItemStats';
	import { itemTypeColor } from '$lib/spec/itemTypeColors';

	let {
		view,
		onItemClick
	}: {
		view: SpecViewOverviewResponse;
		onItemClick: (itemId: number) => void;
	} = $props();

	const attention = $derived(attentionItems(view.items));
	const mandatoryGaps = $derived(attention.filter((row) => row.kind === 'mandatory_gap'));
	const lowConfidence = $derived(attention.filter((row) => row.kind === 'low_confidence'));
	const unevaluated = $derived(attention.filter((row) => row.kind === 'unevaluated'));

	function formatConfidence(confidence: number | null): string {
		if (confidence === null || confidence === undefined) return '—';
		return `${Math.round(confidence * 100)}%`;
	}

	function shortSha(sha: string): string {
		return sha.slice(0, 7);
	}

	function kindLabel(kind: SpecItemAttention['kind']): string {
		if (kind === 'mandatory_gap') return 'Not implemented';
		if (kind === 'low_confidence') return 'Low confidence';
		return 'Not evaluated';
	}
</script>

<div class="overview">
	<div class="overview-header">
		<div>
			<span class="status-pill {view.summary.status}">
				{statusHelp(view.summary.status).label}
			</span>
			<p class="intro">
				Health for the latest spec version. Failed items below show the evaluator’s summary and
				identified gaps.
			</p>
		</div>
	</div>

	<section class="summary-grid">
		<MetricCard
			metric={{
				label: 'Items',
				short: 'Spec items extracted from this version.',
				detail: `${view.summary.total_items} total, ${view.summary.tracked_items} must/should.`
			}}
			value={view.summary.tracked_items}
		/>
		<MetricCard metric={DASHBOARD_METRICS.coverage} value={view.summary.coverage_percent != null
			? `${view.summary.coverage_percent}%`
			: '—'} />
		<MetricCard
			metric={DASHBOARD_METRICS.missing}
			value={view.summary.mandatory_gaps}
			warn={view.summary.mandatory_gaps > 0}
		/>
		<MetricCard
			metric={DASHBOARD_METRICS.low_confidence}
			value={view.summary.low_confidence}
			warn={view.summary.low_confidence > 0}
		/>
		<MetricCard
			metric={{
				label: 'Unevaluated',
				short: 'Must/should items with no evaluation yet.',
				detail: 'These have not been checked against the codebase at any commit.'
			}}
			value={view.summary.unevaluated}
			warn={view.summary.unevaluated > 0}
		/>
	</section>

	{#if mandatoryGaps.length > 0}
		<section class="alert-panel">
			<header>
				<h2>Mandatory gaps</h2>
				<p>Must-have items judged <strong>not implemented</strong> at the latest evaluation.</p>
			</header>
			<div class="item-cards">
				{#each mandatoryGaps as row (row.item.id)}
					{@const latest = row.latest!}
					<article class="item-card failed">
						<button type="button" class="item-card-btn" onclick={() => onItemClick(row.item.id)}>
							<div class="item-head">
								<span class="key">{row.item.local_key}</span>
								<span class="badge failed">{kindLabel(row.kind)}</span>
								<span
									class="badge type"
									style:background={itemTypeColor(row.item.item_type).bg}
									style:color={itemTypeColor(row.item.item_type).text}
								>
									{row.item.item_type.replaceAll('_', ' ')}
								</span>
							</div>
							<p class="item-text">{row.item.text}</p>
							{#if latest.summary}
								<div class="reason">
									<span class="reason-label">Why it failed</span>
									<p>{latest.summary}</p>
								</div>
							{/if}
							{#if latest.gaps.length > 0}
								<div class="gaps">
									<span class="reason-label">Gaps</span>
									<ul>
										{#each latest.gaps as gap}<li>{gap}</li>{/each}
									</ul>
								</div>
							{/if}
							<div class="meta-row">
								<span>Confidence {formatConfidence(latest.confidence)}</span>
								<span>Evaluated at <code>{shortSha(latest.commit_sha)}</code></span>
							</div>
						</button>
					</article>
				{/each}
			</div>
		</section>
	{/if}

	{#if lowConfidence.length > 0}
		<section class="panel">
			<header>
				<h2>Low confidence</h2>
				<p>Implemented or not—the model was unsure. Review these judgements.</p>
			</header>
			<div class="item-cards compact">
				{#each lowConfidence as row (row.item.id)}
					{@const latest = row.latest!}
					<article class="item-card warn">
						<button type="button" class="item-card-btn" onclick={() => onItemClick(row.item.id)}>
							<div class="item-head">
								<span class="key">{row.item.local_key}</span>
								<span class="badge warn">
									{latest.implemented ? 'Implemented' : 'Not implemented'} · {formatConfidence(
										latest.confidence
									)} conf
								</span>
							</div>
							<p class="item-text">{row.item.text}</p>
							{#if latest.summary}
								<p class="summary-line">{latest.summary}</p>
							{/if}
						</button>
					</article>
				{/each}
			</div>
		</section>
	{/if}

	{#if unevaluated.length > 0}
		<section class="panel">
			<header>
				<h2>Not yet evaluated</h2>
				<p>Tracked items waiting for an implementation check.</p>
			</header>
			<ul class="simple-list">
				{#each unevaluated as row (row.item.id)}
					<li>
						<button type="button" class="simple-link" onclick={() => onItemClick(row.item.id)}>
							<span class="key">{row.item.local_key}</span>
							<span class="item-text">{row.item.text}</span>
						</button>
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	{#if attention.length === 0 && view.summary.evaluated > 0}
		<section class="panel success-panel">
			<h2>All clear</h2>
			<p>
				All tracked must/should items are implemented with acceptable confidence at the latest
				evaluation.
			</p>
		</section>
	{/if}

	{#if view.summary.evaluated === 0}
		<section class="panel">
			<p class="empty">No evaluations recorded for this spec version yet.</p>
		</section>
	{/if}
</div>

<style>
	.overview {
		display: grid;
		gap: 1rem;
	}

	.overview-header .intro {
		margin: 0.5rem 0 0;
		font-size: 0.84rem;
		color: #64748b;
		line-height: 1.45;
	}

	.status-pill {
		display: inline-block;
		padding: 0.2rem 0.55rem;
		border-radius: 999px;
		font-size: 0.72rem;
		font-weight: 600;
		text-transform: capitalize;
	}

	.status-pill.good {
		background: #dcfce7;
		color: #166534;
	}
	.status-pill.mostly_implemented {
		background: #fef3c7;
		color: #92400e;
	}
	.status-pill.at_risk {
		background: #fee2e2;
		color: #991b1b;
	}
	.status-pill.unknown {
		background: #f1f5f9;
		color: #475569;
	}

	.summary-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
		gap: 0.65rem;
	}

	.alert-panel {
		background: #fff5f5;
		border: 1px solid #fecaca;
		border-radius: 0.75rem;
		padding: 0.9rem 1rem;
	}

	.panel {
		background: #fff;
		border: 1px solid #e2e8f0;
		border-radius: 0.75rem;
		padding: 0.9rem 1rem;
	}

	.success-panel {
		background: #f0fdf4;
		border-color: #bbf7d0;
	}

	.alert-panel header h2,
	.panel header h2,
	.success-panel h2 {
		margin: 0;
		font-size: 0.95rem;
		font-weight: 600;
		color: #0f172a;
	}

	.alert-panel header p,
	.panel header p {
		margin: 0.25rem 0 0.75rem;
		font-size: 0.8rem;
		color: #64748b;
	}

	.item-cards {
		display: grid;
		gap: 0.65rem;
	}

	.item-cards.compact .item-text {
		margin-bottom: 0;
	}

	.item-card {
		border-radius: 0.6rem;
		overflow: hidden;
	}

	.item-card.failed {
		border: 1px solid #fca5a5;
		background: #fff;
	}

	.item-card.warn {
		border: 1px solid #fde68a;
		background: #fffbeb;
	}

	.item-card-btn {
		width: 100%;
		text-align: left;
		border: none;
		background: transparent;
		padding: 0.75rem 0.85rem;
		cursor: pointer;
	}

	.item-card-btn:hover {
		background: rgba(255, 255, 255, 0.6);
	}

	.item-head {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.35rem;
		margin-bottom: 0.35rem;
	}

	.key {
		font-family: ui-monospace, monospace;
		font-weight: 700;
		font-size: 0.82rem;
		color: #0f172a;
	}

	.badge {
		font-size: 0.66rem;
		padding: 0.08rem 0.4rem;
		border-radius: 999px;
		font-weight: 600;
	}

	.badge.failed {
		background: #fee2e2;
		color: #991b1b;
	}

	.badge.warn {
		background: #fef3c7;
		color: #92400e;
	}

	.badge.type {
		text-transform: lowercase;
	}

	.item-text {
		margin: 0 0 0.5rem;
		font-size: 0.86rem;
		color: #334155;
		line-height: 1.45;
	}

	.reason,
	.gaps {
		margin-top: 0.45rem;
	}

	.reason-label {
		display: block;
		font-size: 0.68rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: #b91c1c;
		margin-bottom: 0.15rem;
	}

	.reason p,
	.summary-line {
		margin: 0;
		font-size: 0.82rem;
		color: #475569;
		line-height: 1.45;
	}

	.gaps ul {
		margin: 0;
		padding-left: 1.1rem;
		font-size: 0.8rem;
		color: #b45309;
	}

	.meta-row {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
		margin-top: 0.55rem;
		font-size: 0.72rem;
		color: #64748b;
	}

	.simple-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 0.35rem;
	}

	.simple-link {
		width: 100%;
		display: grid;
		gap: 0.1rem;
		text-align: left;
		border: 1px solid #f1f5f9;
		border-radius: 0.45rem;
		padding: 0.5rem 0.65rem;
		background: #f8fafc;
		cursor: pointer;
	}

	.simple-link:hover {
		background: #f1f5f9;
	}

	.empty {
		margin: 0;
		color: #64748b;
		font-size: 0.88rem;
	}
</style>
