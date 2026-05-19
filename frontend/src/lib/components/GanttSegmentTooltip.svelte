<script lang="ts">
	import type { GanttSegmentTooltip } from '$lib/gantt/ganttSegmentTooltip';

	let {
		tooltip,
		x,
		y
	}: {
		tooltip: GanttSegmentTooltip;
		x: number;
		y: number;
	} = $props();

	const OFFSET_X = 14;
	const OFFSET_Y = 16;
	const MARGIN = 12;

	let el: HTMLDivElement | undefined = $state();
	let left = $state(0);
	let top = $state(0);

	$effect(() => {
		if (!el) return;
		const rect = el.getBoundingClientRect();
		let nextLeft = x + OFFSET_X;
		let nextTop = y + OFFSET_Y;
		if (nextLeft + rect.width > window.innerWidth - MARGIN) {
			nextLeft = x - rect.width - OFFSET_X;
		}
		if (nextTop + rect.height > window.innerHeight - MARGIN) {
			nextTop = y - rect.height - OFFSET_Y;
		}
		left = Math.max(MARGIN, nextLeft);
		top = Math.max(MARGIN, nextTop);
	});

	function shortSha(sha: string): string {
		return sha.length > 12 ? `${sha.slice(0, 7)}…${sha.slice(-4)}` : sha;
	}

	const statusTone = $derived.by(() => {
		const s = tooltip.status.toLowerCase();
		if (s === 'implemented' || s === 'active') return 'ok';
		if (s === 'not_implemented' || s === 'inactive') return 'warn';
		if (s === 'deleted') return 'bad';
		return 'neutral';
	});
</script>

<div
	class="gantt-tooltip"
	class:kind-req={tooltip.kind === 'requirement'}
	class:kind-art={tooltip.kind === 'artifact'}
	data-status={statusTone}
	style="left: {left}px; top: {top}px"
	bind:this={el}
	role="tooltip"
>
	<header class="head">
		<span class="kind">{tooltip.kind === 'requirement' ? 'Requirement' : 'Artifact'}</span>
		<span class="status">{tooltip.statusLabel}</span>
	</header>
	<h4 class="title" title={tooltip.title}>{tooltip.title}</h4>
	<dl class="facts">
		<div class="fact">
			<dt>From</dt>
			<dd>{tooltip.start}</dd>
		</div>
		<div class="fact">
			<dt>Until</dt>
			<dd>{tooltip.end}</dd>
		</div>
		{#if tooltip.commit}
			<div class="fact">
				<dt>Commit</dt>
				<dd><code title={tooltip.commit}>{shortSha(tooltip.commit)}</code></dd>
			</div>
		{/if}
		{#if tooltip.blobSha}
			<div class="fact">
				<dt>Blob</dt>
				<dd><code title={tooltip.blobSha}>{shortSha(tooltip.blobSha)}</code></dd>
			</div>
		{/if}
	</dl>
	{#if tooltip.requirementText}
		<section class="body-block" aria-label="Requirement text">
			<p class="body-label">Requirement text</p>
			<pre class="body-text">{tooltip.requirementText}</pre>
		</section>
	{/if}
</div>

<style>
	.gantt-tooltip {
		position: fixed;
		z-index: 10000;
		width: min(22rem, calc(100vw - 1.5rem));
		max-width: 22rem;
		padding: 0.65rem 0.75rem 0.7rem;
		border-radius: 0.55rem;
		border: 1px solid #e2e8f0;
		background: #fff;
		box-shadow:
			0 4px 6px -1px rgba(15, 23, 42, 0.08),
			0 12px 24px -6px rgba(15, 23, 42, 0.12);
		pointer-events: none;
		font-size: 0.75rem;
		line-height: 1.4;
		color: #334155;
	}
	.head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.5rem;
		margin-bottom: 0.35rem;
	}
	.kind {
		font-size: 0.625rem;
		font-weight: 600;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: #64748b;
	}
	.kind-req .kind {
		color: #0369a1;
	}
	.kind-art .kind {
		color: #7c3aed;
	}
	.status {
		font-size: 0.625rem;
		font-weight: 600;
		padding: 0.12rem 0.45rem;
		border-radius: 999px;
		white-space: nowrap;
	}
	.gantt-tooltip[data-status='ok'] .status {
		background: #dcfce7;
		color: #14532d;
	}
	.gantt-tooltip[data-status='warn'] .status {
		background: #fef3c7;
		color: #78350f;
	}
	.gantt-tooltip[data-status='bad'] .status {
		background: #fee2e2;
		color: #7f1d1d;
	}
	.gantt-tooltip[data-status='neutral'] .status {
		background: #f1f5f9;
		color: #475569;
	}
	.title {
		margin: 0 0 0.5rem 0;
		font-size: 0.8125rem;
		font-weight: 600;
		color: #0f172a;
		line-height: 1.35;
		word-break: break-word;
	}
	.facts {
		margin: 0;
		display: grid;
		gap: 0.28rem;
	}
	.fact {
		display: grid;
		grid-template-columns: 3.25rem 1fr;
		gap: 0.35rem;
		align-items: baseline;
	}
	dt {
		margin: 0;
		font-size: 0.625rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: #94a3b8;
	}
	dd {
		margin: 0;
		color: #1e293b;
	}
	code {
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
		font-size: 0.7rem;
		background: #f8fafc;
		padding: 0.08rem 0.3rem;
		border-radius: 0.2rem;
		border: 1px solid #e2e8f0;
	}
	.body-block {
		margin-top: 0.55rem;
		padding-top: 0.5rem;
		border-top: 1px solid #f1f5f9;
		min-width: 0;
	}
	.body-label {
		margin: 0 0 0.3rem 0;
		font-size: 0.625rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: #94a3b8;
	}
	.body-text {
		margin: 0;
		max-height: 9rem;
		overflow: auto;
		padding: 0.4rem 0.45rem;
		border-radius: 0.35rem;
		background: #f8fafc;
		border: 1px solid #e2e8f0;
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
		font-size: 0.6875rem;
		line-height: 1.45;
		white-space: pre-wrap;
		word-break: break-word;
		color: #0f172a;
	}
</style>
