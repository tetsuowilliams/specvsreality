<script lang="ts">
	import type { GanttChartResponse } from '$lib/api/repoCatalog';
	import GanttSegmentTooltip from '$lib/components/GanttSegmentTooltip.svelte';
	import { buildSvelteGanttChartOptions, type GanttTaskModel } from '$lib/gantt/mapGanttApiToSvelteGantt';
	import type { GanttSegmentTooltip as GanttSegmentTooltipData } from '$lib/gantt/ganttSegmentTooltip';
	import moment from 'moment';
	import { MomentSvelteGanttDateAdapter, SvelteGantt, SvelteGanttTable } from 'svelte-gantt/svelte';

	let { chart }: { chart: GanttChartResponse } = $props();

	const dateAdapter = new MomentSvelteGanttDateAdapter(moment);

	const opts = $derived(buildSvelteGanttChartOptions(chart));

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

	let activeTooltip: GanttSegmentTooltipData | null = $state(null);
	let tooltipX = $state(0);
	let tooltipY = $state(0);

	function showTooltip(tip: GanttSegmentTooltipData, event: PointerEvent) {
		activeTooltip = tip;
		tooltipX = event.clientX;
		tooltipY = event.clientY;
	}

	function moveTooltip(event: PointerEvent) {
		tooltipX = event.clientX;
		tooltipY = event.clientY;
	}

	function hideTooltip() {
		activeTooltip = null;
	}

	/** svelte-gantt passes the task {@link TaskModel}, not a {@link SvelteTask} wrapper. */
	function taskElementHook(node: HTMLElement, taskModel: GanttTaskModel) {
		const tip = taskModel?.tooltip;
		if (!tip) return {};

		const onEnter = (event: PointerEvent) => showTooltip(tip, event);
		const onMove = (event: PointerEvent) => {
			if (activeTooltip === tip) moveTooltip(event);
		};
		const onLeave = () => {
			if (activeTooltip === tip) hideTooltip();
		};

		node.addEventListener('pointerenter', onEnter);
		node.addEventListener('pointermove', onMove);
		node.addEventListener('pointerleave', onLeave);

		return {
			destroy() {
				node.removeEventListener('pointerenter', onEnter);
				node.removeEventListener('pointermove', onMove);
				node.removeEventListener('pointerleave', onLeave);
				if (activeTooltip === tip) hideTooltip();
			}
		};
	}
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
					{taskElementHook}
				/>
			{/key}
		</div>
	</div>
</div>

{#if activeTooltip}
	<GanttSegmentTooltip tooltip={activeTooltip} x={tooltipX} y={tooltipY} />
{/if}

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
		cursor: pointer;
	}
	:global(.specvsreality-gantt .sg-task:hover) {
		filter: brightness(0.97);
		box-shadow: 0 2px 6px rgba(15, 23, 42, 0.1);
	}
	:global(.specvsreality-gantt .gantt-status-ok) {
		background: linear-gradient(180deg, #d1fae5 0%, #a7f3d0 100%) !important;
		color: transparent;
	}
	:global(.specvsreality-gantt .gantt-status-warn) {
		background: linear-gradient(180deg, #fbbf24 0%, #f59e0b 100%) !important;
		color: #422006;
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
