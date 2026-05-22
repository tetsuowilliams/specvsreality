<script lang="ts">
	import type { GanttChartResponse, RequirementVersionTreeResponse } from '$lib/api/repoCatalog';
	import { buildSvelteGanttChartOptions, type GanttTaskModel } from '$lib/gantt/mapGanttApiToSvelteGantt';
	import moment from 'moment';
	import { MomentSvelteGanttDateAdapter, SvelteGantt, SvelteGanttTable } from 'svelte-gantt/svelte';

	let {
		chart,
		versionTree = null
	}: {
		chart: GanttChartResponse;
		versionTree?: RequirementVersionTreeResponse | null;
	} = $props();

	const dateAdapter = new MomentSvelteGanttDateAdapter(moment);

	const opts = $derived(buildSvelteGanttChartOptions(chart, { versionTree }));

	const tooltipByTaskId = $derived(
		new Map(
			opts.tasks
				.filter((t) => t.tooltip != null && t.tooltip.trim().length > 0)
				.map((t) => [String(t.id), t.tooltip!.trim()] as const)
		)
	);

	let floatingTip = $state<string | null>(null);
	let floatingX = $state(0);
	let floatingY = $state(0);

	function showFloatingTip(text: string, event: MouseEvent) {
		floatingTip = text;
		floatingX = event.clientX;
		floatingY = event.clientY;
	}

	function hideFloatingTip() {
		floatingTip = null;
	}

	function taskElementHook(node: HTMLElement, model: GanttTaskModel) {
		const tip = tooltipByTaskId.get(String(model.id)) ?? model.tooltip?.trim();
		if (!tip) return {};

		const onEnter = (event: MouseEvent) => showFloatingTip(tip, event);
		const onMove = (event: MouseEvent) => {
			if (floatingTip != null) {
				floatingX = event.clientX;
				floatingY = event.clientY;
			}
		};
		const onLeave = () => hideFloatingTip();

		node.addEventListener('mouseenter', onEnter);
		node.addEventListener('mousemove', onMove);
		node.addEventListener('mouseleave', onLeave);

		return {
			destroy() {
				node.removeEventListener('mouseenter', onEnter);
				node.removeEventListener('mousemove', onMove);
				node.removeEventListener('mouseleave', onLeave);
				hideFloatingTip();
			}
		};
	}

	/**
	 * svelte-gantt only stretches when `fitWidth` and timeline clientWidth > `minWidth`.
	 * `timelineMinWidth` from the mapper can be huge; cap so the default view fits the pane.
	 * Ctrl+scroll switches to the second zoom level with the full min width for detail + scroll.
	 */
	const FIT_TIMELINE_MIN_CAP = 640;
	const timelineMinForFit = $derived(Math.min(opts.timelineMinWidth, FIT_TIMELINE_MIN_CAP));

	const tableW = 232;

	const ganttKey = $derived(
		`${opts.from}|${opts.to}|${opts.tasks.map((t) => t.id).join('|')}|${opts.timeRanges.map((r) => r.id).join('|')}`
	);
</script>

<div class="gantt">
	<div class="meta">
		<span class="pill" data-on={chart.meta.requirement_implemented}>
			{chart.meta.requirement_implemented ? 'Implemented (latest)' : 'Not implemented (latest)'}
		</span>
	</div>
	<div class="gantt-host">
		<div class="gantt-host-inner">
			{#key ganttKey}
				<SvelteGantt
					classes="specvsreality-gantt"
					{taskElementHook}
					rows={opts.rows}
					tasks={opts.tasks}
					timeRanges={opts.timeRanges}
					from={opts.from}
					to={opts.to}
					{dateAdapter}
					ganttTableModules={[SvelteGanttTable]}
					tableWidth={tableW}
					tableHeaders={[{ title: 'Track', property: 'label', width: tableW }]}
					columnUnit={opts.preset.columnUnit}
					columnOffset={opts.preset.columnOffset}
					headers={opts.preset.headers}
					zoomLevels={[
						{
							headers: opts.preset.headers,
							minWidth: timelineMinForFit,
							fitWidth: true
						},
						{
							headers: [{ unit: 'hour', format: 'ddd D MMM YYYY HH:mm' }],
							minWidth: Math.max(2400, opts.timelineMinWidth),
							fitWidth: false
						}
					]}
					magnetUnit={opts.magnetUnit}
					magnetOffset={opts.magnetOffset}
					rowHeight={64}
					rowPadding={3}
					minWidth={timelineMinForFit}
					fitWidth={true}
					layout="overlap"
					reflectOnParentRows={false}
					reflectOnChildRows={false}
					useCanvasColumns={false}
				/>
			{/key}
		</div>
	</div>
	{#if floatingTip}
		<div
			class="gantt-floating-tip"
			style:left="{floatingX + 14}px"
			style:top="{floatingY + 14}px"
			role="tooltip"
		>
			{floatingTip}
		</div>
	{/if}
</div>

<style>
	.gantt {
		display: flex;
		flex-direction: column;
		gap: 0.45rem;
		font-size: 0.8125rem;
		width: 100%;
		max-width: 100%;
		min-width: 0;
		font-family:
			ui-sans-serif,
			system-ui,
			'Segoe UI',
			Roboto,
			'Helvetica Neue',
			Arial,
			sans-serif;
		-webkit-font-smoothing: antialiased;
		-moz-osx-font-smoothing: grayscale;
		letter-spacing: 0.01em;
	}
	.meta {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.4rem 0.65rem;
	}
	.pill {
		display: inline-block;
		padding: 0.16rem 0.5rem;
		border-radius: 999px;
		font-size: 0.6875rem;
		font-weight: 600;
		letter-spacing: 0.02em;
		text-transform: uppercase;
		background: #e2e8f0;
		color: #475569;
	}
	.pill[data-on='true'] {
		background: #dcfce7;
		color: #14532d;
	}
	.gantt-host {
		width: 100%;
		max-width: 100%;
		min-height: 20rem;
		min-width: 0;
		overflow: auto;
		border: 1px solid #e2e8f0;
		border-radius: 0.5rem;
		background: #fff;
		box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
	}
	.gantt-host-inner {
		padding: 0.5rem 0.6rem;
		min-width: 0;
		box-sizing: border-box;
	}
	:global(.specvsreality-gantt.sg-gantt) {
		--specvsreality-gantt-track: #eef2f6;
		font-size: 0.6875rem;
		color: #334155;
		border-radius: 0.35rem;
		overflow: hidden;
	}

	/* Row band behind tasks; rowPadding adds vertical gap between row edges and the task box */
	:global(.specvsreality-gantt .sg-row) {
		background: var(--specvsreality-gantt-track);
		box-sizing: border-box;
		border-bottom: 1px solid #e2e8f0;
	}

	:global(.specvsreality-gantt .sg-table-row) {
		background: #fafbfc;
		border-bottom: 1px solid #e8ecf0;
	}
	:global(.specvsreality-gantt .sg-table-header-cell) {
		font-size: 0.625rem;
		font-weight: 600;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: #64748b;
		padding: 0.35rem 0.5rem;
	}
	:global(.specvsreality-gantt .sg-table-body-cell) {
		font-size: 0.6875rem;
		font-weight: 500;
		color: #1e293b;
		padding: 0.35rem 0.5rem;
		line-height: 1.35;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	:global(.specvsreality-gantt .sg-table-row) {
		font-size: 0.6875rem !important;
	}
	:global(.specvsreality-gantt .column-header-cell) {
		font-size: 0.625rem;
		font-weight: 500;
		color: #64748b;
	}
	:global(.specvsreality-gantt .sg-task-content) {
		display: none;
	}
	/*
	 * 3px track-colored border on all sides: gaps between segments, modest inset from row edges
	 * (with rowPadding, task height = rowHeight − 2×rowPadding; border-box keeps border inside that box).
	 */
	:global(.specvsreality-gantt .sg-task) {
		box-sizing: border-box;
		border: 3px solid var(--specvsreality-gantt-track);
		border-radius: 0.45rem;
		box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
	}
	.gantt-floating-tip {
		position: fixed;
		z-index: 10000;
		max-width: min(22rem, calc(100vw - 2rem));
		max-height: 14rem;
		overflow: auto;
		padding: 0.5rem 0.65rem;
		background: #1e293b;
		color: #f8fafc;
		font-size: 0.78rem;
		font-weight: 400;
		line-height: 1.45;
		border-radius: 0.4rem;
		box-shadow: 0 8px 20px rgba(15, 23, 42, 0.22);
		white-space: pre-wrap;
		word-break: break-word;
		pointer-events: none;
	}
	:global(.specvsreality-gantt .gantt-status-ok) {
		background: linear-gradient(180deg, #d1fae5 0%, #a7f3d0 100%) !important;
		color: transparent;
	}
	:global(.specvsreality-gantt .gantt-status-warn) {
		background: linear-gradient(180deg, #fecaca 0%, #fca5a5 100%) !important;
		color: transparent;
	}
	:global(.specvsreality-gantt .gantt-status-bad) {
		background: linear-gradient(180deg, #f87171 0%, #ef4444 100%) !important;
		color: #450a0a;
	}
	:global(.specvsreality-gantt .gantt-status-neutral) {
		background: linear-gradient(180deg, #94a3b8 0%, #64748b 100%) !important;
		color: #f8fafc;
	}
</style>
