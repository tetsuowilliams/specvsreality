/**
 * Maps {@link GanttChartResponse} into [svelte-gantt](https://github.com/ANovokmet/svelte-gantt) options.
 *
 * **Rows & tasks (per-resource history)**  
 * Each API `history[]` entry becomes a **task** on the row for that requirement or artifact
 * (`TaskModel.resourceId` = `RowModel.id`). `from` / `to` are Unix ms (`Date` / ISO from the API).
 *
 * **`timeRanges` (chart-wide bands)**  
 * In svelte-gantt, each time range is drawn **across every row** (see README “Time ranges”).
 * It is the right shape for things like “Lunch” or maintenance windows, **not** for
 * per-artifact history. We still expose {@link mapGanttApiToTimeRanges} so you can pass
 * `timeRanges: [...]` when you want those global markers; the chart uses `[]` by default
 * so history is not duplicated as full-height stripes on unrelated rows.
 *
 * Docs mirror: https://anovokmet.github.io/svelte-gantt/docs/options/gantt (when available);
 * source of truth: package README + `types/gantt.d.ts`.
 */
import type {
	GanttChartResponse,
	GanttHistorySegment,
	RequirementVersionTreeResponse
} from '$lib/api/repoCatalog';
import { artifactSegmentTooltip, requirementSegmentTooltips } from '$lib/gantt/ganttTaskTooltips';

/** Mirrors svelte-gantt `RowModel`. */
export type GanttRowModel = {
	id: PropertyKey;
	label?: string;
	draggable?: boolean;
	resizable?: boolean;
};

/** Mirrors svelte-gantt `TaskModel`. */
export type GanttTaskModel = {
	id: PropertyKey;
	resourceId: PropertyKey;
	from: number;
	to: number;
	label?: string;
	/** Hover tooltip (wired via {@link GanttChart} taskElementHook). */
	tooltip?: string;
	classes?: string;
	draggable?: boolean;
	resizable?: boolean;
};

/** Mirrors svelte-gantt `TimeRangeModel` (`timeRanges` option). */
export type GanttTimeRangeModel = {
	id: PropertyKey;
	from: number;
	to: number;
	label?: string;
	classes?: string | string[];
	resizable?: boolean;
};

export type GanttTimelineBounds = { from: number; to: number };

export const REQUIREMENT_ROW_ID = 'requirement' as const;

export function artifactRowId(artifactIndex: number): string {
	return `artifact:${artifactIndex}`;
}

export type MappedGanttRowsTasks = {
	rows: GanttRowModel[];
	tasks: GanttTaskModel[];
	bounds: GanttTimelineBounds;
};

export type SvelteGanttChartOptions = {
	rows: GanttRowModel[];
	tasks: GanttTaskModel[];
	/** Chart-wide vertical bands only; default `[]` in {@link buildSvelteGanttChartOptions}. */
	timeRanges: GanttTimeRangeModel[];
	from: number;
	to: number;
	preset: ColumnPreset;
	timelineMinWidth: number;
	magnetUnit: 'hour' | 'day';
	magnetOffset: number;
};

function parseMs(iso: string): number {
	const t = Date.parse(iso);
	return Number.isFinite(t) ? t : NaN;
}

function collectGlobalBounds(chart: GanttChartResponse): GanttTimelineBounds {
	let min = Infinity;
	let max = -Infinity;
	const bump = (iso: string) => {
		const t = parseMs(iso);
		if (!Number.isFinite(t)) return;
		min = Math.min(min, t);
		max = Math.max(max, t);
	};
	for (const h of chart.requirement.history) {
		bump(h.start);
		bump(h.end);
	}
	for (const a of chart.artifacts) {
		for (const h of a.history) {
			bump(h.start);
			bump(h.end);
		}
	}
	if (!Number.isFinite(min) || !Number.isFinite(max) || min === max) {
		const now = Date.now();
		return { from: now - 86400000, to: now + 86400000 };
	}
	const span = max - min;
	const pad = Math.max(span * 0.02, 3600000);
	return { from: min - pad, to: max + pad };
}

/** Maps API segment status to gantt bar classes (aligned with implementationStatus themes). */
export function statusTaskClasses(status: string): string {
	const s = status.toLowerCase();
	if (s === 'implemented' || s === 'active' || s === 'updated') return 'gantt-status-ok';
	if (s === 'not_implemented' || s === 'inactive') return 'gantt-status-warn';
	if (s === 'deleted') return 'gantt-status-bad';
	return 'gantt-status-neutral';
}

function segmentLabel(seg: GanttHistorySegment): string {
	const short = (iso: string) => {
		const d = new Date(iso);
		return Number.isFinite(d.getTime()) ? d.toLocaleDateString() : iso;
	};
	const commit = seg.commit ? ` · ${seg.commit.slice(0, 7)}` : '';
	return `${seg.status} (${short(seg.start)} → ${short(seg.end)})${commit}`;
}

function mapRequirementSegments(
	block: GanttChartResponse['requirement'],
	tooltips: (string | null)[] | null
): GanttTaskModel[] {
	return block.history.map((seg, i) => {
		const from = parseMs(seg.start);
		const to = parseMs(seg.end);
		const safeTo = Number.isFinite(to) && Number.isFinite(from) && to <= from ? from + 60000 : to;
		const tooltip = tooltips?.[i] ?? undefined;
		return {
			id: `req:${block.paper_id}:${i}:${from}:${safeTo}`,
			resourceId: REQUIREMENT_ROW_ID,
			from: Number.isFinite(from) ? from : Date.now(),
			to: Number.isFinite(safeTo) ? safeTo : Date.now() + 60000,
			...(tooltip ? { tooltip } : {}),
			classes: statusTaskClasses(seg.status),
			draggable: false,
			resizable: false
		};
	});
}

function mapArtifactSegments(
	block: GanttChartResponse['artifacts'][number],
	artifactIndex: number,
	versionTree: RequirementVersionTreeResponse | null
): GanttTaskModel[] {
	const rid = artifactRowId(artifactIndex);
	return block.history.map((seg, i) => {
		const from = parseMs(seg.start);
		const to = parseMs(seg.end);
		const safeTo = Number.isFinite(to) && Number.isFinite(from) && to <= from ? from + 60000 : to;
		const tooltip =
			versionTree != null
				? (artifactSegmentTooltip(block.filepath, seg, versionTree) ?? undefined)
				: undefined;
		return {
			id: `art:${artifactIndex}:${i}:${from}:${safeTo}`,
			resourceId: rid,
			from: Number.isFinite(from) ? from : Date.now(),
			to: Number.isFinite(safeTo) ? safeTo : Date.now() + 60000,
			...(tooltip ? { tooltip } : {}),
			classes: statusTaskClasses(seg.status),
			draggable: false,
			resizable: false
		};
	});
}

export function mapGanttApiToRowsAndTasks(
	chart: GanttChartResponse,
	versionTree?: RequirementVersionTreeResponse | null
): MappedGanttRowsTasks {
	const bounds = collectGlobalBounds(chart);
	const rvTooltips =
		versionTree != null ? requirementSegmentTooltips(chart, versionTree) : null;

	const rows: GanttRowModel[] = [
		{
			id: REQUIREMENT_ROW_ID,
			label: `Requirement (${chart.requirement.paper_id})`,
			draggable: false,
			resizable: false
		}
	];
	const tasks: GanttTaskModel[] = [...mapRequirementSegments(chart.requirement, rvTooltips)];

	for (let i = 0; i < chart.artifacts.length; i++) {
		const a = chart.artifacts[i]!;
		rows.push({
			id: artifactRowId(i),
			label: a.filepath,
			draggable: false,
			resizable: false
		});
		tasks.push(...mapArtifactSegments(a, i, versionTree ?? null));
	}

	return { rows, tasks, bounds };
}

export function mapGanttApiToTimeRanges(chart: GanttChartResponse): GanttTimeRangeModel[] {
	const out: GanttTimeRangeModel[] = [];
	const pushSeg = (id: string, prefix: string, seg: GanttHistorySegment) => {
		const from = parseMs(seg.start);
		const to = parseMs(seg.end);
		const safeTo = Number.isFinite(to) && Number.isFinite(from) && to <= from ? from + 60000 : to;
		out.push({
			id,
			from: Number.isFinite(from) ? from : Date.now(),
			to: Number.isFinite(safeTo) ? safeTo : Date.now() + 60000,
			label: `${prefix}: ${segmentLabel(seg)}`,
			classes: ['specvsreality-api-time-range', statusTaskClasses(seg.status)],
			resizable: false
		});
	};
	chart.requirement.history.forEach((seg, i) => {
		pushSeg(`tr-req-${chart.requirement.paper_id}-${i}`, `Requirement (${chart.requirement.paper_id})`, seg);
	});
	for (let i = 0; i < chart.artifacts.length; i++) {
		const a = chart.artifacts[i]!;
		a.history.forEach((seg, j) => {
			pushSeg(`tr-art-${i}-${j}`, a.filepath, seg);
		});
	}
	return out;
}

export type ColumnPreset = {
	columnUnit: string;
	columnOffset: number;
	headers: { unit: string; format: string; offset?: number }[];
};

export function columnPresetForBounds(bounds: GanttTimelineBounds): ColumnPreset {
	const span = bounds.to - bounds.from;
	const day = 86400000;
	if (span <= 3 * day) {
		return {
			columnUnit: 'hour',
			columnOffset: 6,
			headers: [{ unit: 'hour', format: 'ddd D MMM HH:mm' }]
		};
	}
	if (span <= 120 * day) {
		return {
			columnUnit: 'day',
			columnOffset: 1,
			headers: [{ unit: 'month', format: 'MMM YYYY' }]
		};
	}
	return {
		columnUnit: 'week',
		columnOffset: 1,
		headers: [
			{ unit: 'month', format: 'MMM YYYY' },
			{ unit: 'week', format: '[W]W' }
		]
	};
}

export function timelineMinWidthForBounds(bounds: GanttTimelineBounds): number {
	const span = Math.max(1, bounds.to - bounds.from);
	const hour = 3600000;
	const day = 86400000;
	if (span <= 3 * day) {
		const hours = span / hour;
		return Math.max(1200, Math.min(120000, Math.ceil(hours * 48)));
	}
	const spanDays = span / day;
	return Math.max(1600, Math.min(200000, Math.ceil(spanDays * 8)));
}

function magnetForPreset(p: ColumnPreset): { magnetUnit: 'hour' | 'day'; magnetOffset: number } {
	if (p.columnUnit === 'hour') return { magnetUnit: 'hour', magnetOffset: 1 };
	if (p.columnUnit === 'day') return { magnetUnit: 'day', magnetOffset: 1 };
	return { magnetUnit: 'day', magnetOffset: 1 };
}

export type BuildGanttOptionsParams = {
	/**
	 * When true, sets `timeRanges` from {@link mapGanttApiToTimeRanges}. In svelte-gantt each range
	 * spans **all** rows (see README); use only if you want that global overlay in addition to tasks.
	 */
	includeSegmentTimeRanges?: boolean;
	/** Joins evaluation summary / implements evidence onto segment tooltips. */
	versionTree?: RequirementVersionTreeResponse | null;
};

/**
 * Single-chart options bundle (one `SvelteGantt`): `rows`, `tasks`, timeline `from`/`to`,
 * column preset, width hint, magnet, and `timeRanges` (empty unless `includeSegmentTimeRanges`).
 */
export function buildSvelteGanttChartOptions(
	chart: GanttChartResponse,
	params: BuildGanttOptionsParams = {}
): SvelteGanttChartOptions {
	const { rows, tasks, bounds } = mapGanttApiToRowsAndTasks(chart, params.versionTree);
	const preset = columnPresetForBounds(bounds);
	const { magnetUnit, magnetOffset } = magnetForPreset(preset);
	return {
		rows,
		tasks,
		timeRanges: params.includeSegmentTimeRanges ? mapGanttApiToTimeRanges(chart) : [],
		from: bounds.from,
		to: bounds.to,
		preset,
		timelineMinWidth: timelineMinWidthForBounds(bounds),
		magnetUnit,
		magnetOffset
	};
}
