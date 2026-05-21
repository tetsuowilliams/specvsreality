import { describe, expect, it } from 'vitest';
import {
	REQUIREMENT_ROW_ID,
	artifactRowId,
	buildSvelteGanttChartOptions,
	columnPresetForBounds,
	mapGanttApiToRowsAndTasks,
	mapGanttApiToTimeRanges,
	statusTaskClasses
} from './mapGanttApiToSvelteGantt';
import type { GanttChartResponse } from '$lib/api/repoCatalog';

const t0 = '2024-01-01T00:00:00.000Z';
const t1 = '2024-01-02T00:00:00.000Z';
const t2 = '2024-01-03T00:00:00.000Z';

function sampleChart(): GanttChartResponse {
	return {
		meta: { requirement_implemented: true },
		requirement: {
			paper_id: 'REQ-1',
			history: [
				{ start: t0, end: t1, status: 'implemented', commit: 'abc1234' },
				{ start: t1, end: t2, status: 'not_implemented', commit: null }
			]
		},
		artifacts: [
			{
				filepath: 'src/foo.ts',
				history: [{ start: t0, end: t2, status: 'active', commit: 'def5678' }]
			}
		]
	};
}

describe('mapGanttApiToRowsAndTasks', () => {
	it('maps requirement row and artifact rows with stable ids', () => {
		const { rows, tasks, bounds } = mapGanttApiToRowsAndTasks(sampleChart());
		expect(rows.map((r) => r.id)).toEqual([REQUIREMENT_ROW_ID, artifactRowId(0)]);
		expect(rows[0]?.label).toContain('REQ-1');
		expect(rows[1]?.label).toBe('src/foo.ts');
		expect(bounds.from).toBeLessThan(bounds.to);
		expect(tasks).toHaveLength(3);
		expect(tasks.every((t) => t.draggable === false && t.resizable === false)).toBe(true);
	});

	it('assigns tasks to the correct resourceId', () => {
		const { tasks } = mapGanttApiToRowsAndTasks(sampleChart());
		const reqTasks = tasks.filter((t) => t.resourceId === REQUIREMENT_ROW_ID);
		const artTasks = tasks.filter((t) => t.resourceId === artifactRowId(0));
		expect(reqTasks).toHaveLength(2);
		expect(artTasks).toHaveLength(1);
		expect(reqTasks[0]?.label).toBeUndefined();
		expect(reqTasks[0]?.classes).toBe('gantt-status-ok');
		expect(reqTasks[1]?.classes).toBe('gantt-status-warn');
	});

	it('extends zero-length segments by at least one minute', () => {
		const same = '2024-06-01T12:00:00.000Z';
		const chart: GanttChartResponse = {
			meta: { requirement_implemented: false },
			requirement: {
				paper_id: 'R',
				history: [{ start: same, end: same, status: 'deleted', commit: null }]
			},
			artifacts: []
		};
		const { tasks } = mapGanttApiToRowsAndTasks(chart);
		expect(tasks[0]!.to).toBeGreaterThan(tasks[0]!.from);
	});
});

describe('mapGanttApiToTimeRanges', () => {
	it('produces svelte-gantt time range objects (from/to ms, id, label, resizable)', () => {
		const tr = mapGanttApiToTimeRanges(sampleChart());
		expect(tr).toHaveLength(3);
		expect(tr[0]).toMatchObject({
			resizable: false
		});
		expect(typeof tr[0]!.from).toBe('number');
		expect(typeof tr[0]!.to).toBe('number');
		expect(tr[0]!.to).toBeGreaterThan(tr[0]!.from);
		expect(Array.isArray(tr[0]!.classes)).toBe(true);
	});
});

describe('buildSvelteGanttChartOptions', () => {
	it('defaults timeRanges to empty', () => {
		const o = buildSvelteGanttChartOptions(sampleChart());
		expect(o.timeRanges).toEqual([]);
		expect(o.tasks.length).toBe(3);
	});

	it('can include segment-derived time ranges when opted in', () => {
		const o = buildSvelteGanttChartOptions(sampleChart(), { includeSegmentTimeRanges: true });
		expect(o.timeRanges).toHaveLength(3);
	});
});

describe('statusTaskClasses', () => {
	it('maps implementation and live artifact lifecycle statuses to green', () => {
		expect(statusTaskClasses('implemented')).toBe('gantt-status-ok');
		expect(statusTaskClasses('active')).toBe('gantt-status-ok');
		expect(statusTaskClasses('updated')).toBe('gantt-status-ok');
	});

	it('maps negative implementation statuses to warn or bad', () => {
		expect(statusTaskClasses('not_implemented')).toBe('gantt-status-warn');
		expect(statusTaskClasses('deleted')).toBe('gantt-status-bad');
		expect(statusTaskClasses('open')).toBe('gantt-status-neutral');
	});
});

describe('columnPresetForBounds', () => {
	it('uses hour columns for short spans', () => {
		const day = 86400000;
		const p = columnPresetForBounds({ from: 0, to: 2 * day });
		expect(p.columnUnit).toBe('hour');
		expect(p.headers).toHaveLength(1);
	});

	it('uses week columns for long spans', () => {
		const day = 86400000;
		const p = columnPresetForBounds({ from: 0, to: 200 * day });
		expect(p.columnUnit).toBe('week');
	});

	it('uses a single header row for medium spans (no day-number strip)', () => {
		const day = 86400000;
		const p = columnPresetForBounds({ from: 0, to: 30 * day });
		expect(p.headers).toHaveLength(1);
		expect(p.headers[0]?.unit).toBe('month');
	});
});
